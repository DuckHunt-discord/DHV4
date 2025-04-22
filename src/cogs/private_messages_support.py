import asyncio
import datetime
import re
from typing import Dict, List

import babel
import discord
from aiohttp import payload_type
from babel import Locale
from babel.dates import format_datetime, format_timedelta
from discord import RawReactionActionEvent
from discord.ext import commands, menus, tasks
from discord.utils import snowflake_time
from tortoise import timezone

from cogs.tags import TagMenuSource, TagName
from utils import views
from utils.bot_class import MyBot
from utils.checks import NotInChannel, NotInServer
from utils.cog_class import Cog
from utils.concurrency import dont_block
from utils.ctx_class import MyContext
from utils.models import (
    AccessLevel,
    DiscordUser,
    Player,
    SupportTicket,
    Tag,
    get_from_db,
    get_tag,
)
from utils.random_ducks import get_random_duck_file
from utils.translations import get_translate_function
from utils.views import CommandView, View, get_context_from_interaction


def _(message):
    return message


class MirrorMenuPage(menus.MenuPages):
    def __init__(self, source, **kwargs):
        super().__init__(source, **kwargs)
        self.other = None

    def reaction_check(self, payload: discord.RawReactionActionEvent) -> bool:
        # Allow anyone to use the menu.
        # self.ctx: MyContext
        if payload.message_id != self.message.id:
            return False

        # self.bot: MyBot
        if payload.user_id == self.bot.user.id:
            return False

        return payload.emoji in self.buttons

    async def show_page(self, page_number, propagate=True):
        if propagate and self.other:
            try:
                await self.other.show_page(page_number, propagate=False)
            except discord.NotFound:
                # Break the link, one was deleted.
                self.other = None
            except discord.Forbidden:
                # Break the link, can't speak anymore.
                self.other = None

        return await super().show_page(page_number)

    def stop(self, propagate=True):
        if propagate and self.other:
            try:
                self.other.stop(propagate=False)
            except discord.NotFound:
                # Break the link, one was deleted.
                self.other = None
            except discord.Forbidden:
                # Break the link, can't speak anymore.
                self.other = None
        return super().stop()


class CloseReasonSelect(discord.ui.Select):
    reasons = {
        # shown reason : Emoji, stored reason, tag_to_send
        "No help needed": ("❌", "No help needed", None),
        "Support given": ("✅", "Support was provided and the matter resolved", None),
        "DM Commands": ("🤖", "DM Commands", "dm_commands"),
        "Unrelated": ("⁉️", "Not a support DM", "dm_unrelated"),
        "Spam": ("💬", "Spam", None),
        "Scam": ("☢️", "User sent a scam message to the bot", "scams"),
        "Insults": ("🤬", "Insults in DM", None),
        "Unresponsive": ("☠️", "User did not respond", None),
        "Thanks": ("🙃", "Complimented the bot", None),
    }

    def __init__(self, bot):
        self.bot = bot

        options = []

        for reason_label, extra_info in self.reasons.items():
            reason_emoji, stored_reason, tag_to_send = extra_info
            options.append(discord.SelectOption(label=reason_label, emoji=reason_emoji))

        super().__init__(
            custom_id="private_messages_support:close_select_reason",
            placeholder="Quick DM closing",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        ctx = await get_context_from_interaction(self.bot, interaction)
        reason_info = self.reasons[self.values[0]]
        reason_emoji, stored_reason, tag_to_send = reason_info

        close_command = self.bot.get_command("private_support close")
        if tag_to_send:
            await interaction.response.send_message(
                f"Closing with {stored_reason}, but sending the `{tag_to_send}` tag beforehand...",
                ephemeral=True,
            )
            tag_command = self.bot.get_command("private_support tag")
            await ctx.invoke(tag_command, tag_name=tag_to_send)
            await asyncio.sleep(1)
        else:
            await interaction.response.send_message(
                f"Closing with {stored_reason}...", ephemeral=True
            )

        await ctx.invoke(close_command, reason=stored_reason)


class CommonTagSelect(views.AutomaticDeferMixin, discord.ui.Select):
    tags = {
        # tag to send : Emoji, shown name
        "setup": ("⚙️", "How to setup"),
        "quickguide": ("🦆", "How to play"),
        "dm_unrelated": ("⁉️", "Unrelated DMs (close?)"),
        "dm_commands": ("🤖", "DM Commands (close?)"),
        "leveling_up": ("☝️", "Leveling up"),
        "lore_v4": ("📖", "Lore"),
        "commands": ("❕", "Commands list"),
        "wiki": ("🌱", "Wiki"),
    }

    def __init__(self, bot):
        self.bot = bot

        reverse_lookup = {}
        options = []

        for tag_name, extra_info in self.tags.items():
            tag_emoji, tag_shown = extra_info
            options.append(discord.SelectOption(label=tag_shown, emoji=tag_emoji))
            reverse_lookup[tag_shown] = tag_name

        self.reverse_lookup = reverse_lookup

        super().__init__(
            custom_id="private_messages_support:common_tag_select",
            placeholder="Quick tag selector",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        ctx = await get_context_from_interaction(self.bot, interaction)
        tag_name = self.reverse_lookup[self.values[0]]

        tag_command = self.bot.get_command("private_support tag")

        await ctx.invoke(tag_command, tag_name=tag_name)


class CloseReasonSelectView(View):
    def __init__(self, bot):
        super().__init__(bot, timeout=None)

        self.add_item(CloseReasonSelect(bot))
        self.add_item(CommonTagSelect(bot))


def get_close_reason_view(bot, reason_shortcode, reason_stored):
    close_command = bot.get_command("private_support close")
    return CommandView(
        bot,
        close_command,
        persist=f"private_messages_support:close_reason:{reason_shortcode}",
        command_kwargs={"reason": reason_stored},
        label=f"Close the DM ({reason_shortcode})",
        style=discord.ButtonStyle.blurple,
    )


class PrivateMessagesSupport(Cog):
    display_name = _("Support team: private messages")
    help_priority = 15
    help_color = "red"

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.webhook_cache: Dict[discord.TextChannel, discord.Webhook] = {}
        self.users_cache: Dict[int, discord.User] = {}
        self.archived_threads_cache: Dict[int, discord.Thread] = {}  # Cache for archived threads
        self.tags_cache: Dict[int, discord.ForumTag] = {}  # Cache for forum tags
        self.index = 0
        self.background_loop.start()

        self.invites_regex = re.compile(
            r"""
                discord      # Literally just discord
                (?:(?:app)?\s?\.\s?com\s?\/invite|\.\s?gg|\.\s?me)\s?\/ # All the domains
                ((?!.*[Ii10OolL]).[a-zA-Z0-9]{5,12}|[a-zA-Z0-9\-]{2,32}) # Rest of the fucking owl.
                """,
            flags=re.VERBOSE | re.IGNORECASE,
        )
        self.views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info(f"Loading archived support channel threads from the forwarding forum.")

        # Load archived threads into cache
        forum = await self.get_forwarding_forum()
        async for thread in forum.archived_threads():
            try:
                user_id = int(thread.name)
                self.archived_threads_cache[user_id] = thread
            except ValueError:
                continue

        self.bot.logger.info(f"Threads loaded. {len(self.archived_threads_cache)} archived threads in forwarding forum cache.")

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload):
        thread_id = payload.data["id"]
        # guild_id = int(payload.data["guild_id"])
        parent_id = int(payload.data["parent_id"])
        forum = await self.get_forwarding_forum()

        # Check if the channel is a thread and if it's archived
        if parent_id == forum.id:
            self.bot.logger.debug(f"Got raw thread update for a thread of the support forum.")
            after = payload.data.get("thread") or await self.bot.fetch_channel(thread_id)

            # Check if the thread is in the forwarding forum
            # Remove from cache
            user_id = int(after.name)
            if after.archived:
                self.bot.logger.debug(f"[SUPPORT] Archiving thread {after.name} in cache (from event!).")
                # Store the thread in the cache
                self.archived_threads_cache[user_id] = after

    def cog_unload(self):
        self.background_loop.cancel()

    @tasks.loop(hours=1)
    async def background_loop(self):
        """
        Check for age of the last message sent in the thread.
        If it's too old, consider the thread inactive and close the ticket.
        """
        forum = await self.get_forwarding_forum()
        now = timezone.now()
        one_day_ago = now - datetime.timedelta(days=1)
        
        # Check active threads
        for thread in forum.threads:
            last_message_id = thread.last_message_id
            if last_message_id:
                last_message_time = snowflake_time(last_message_id)
            else:
                try:
                    last_message = (await thread.history(limit=1).flatten())[0]
                except IndexError:
                    last_message_time = now
                else:
                    last_message_time = last_message.created_at

            inactive_for = last_message_time - now
            inactive_for_str = format_timedelta(
                inactive_for, granularity="minute", locale="en", threshold=1.1
            )
            self.bot.logger.debug(
                f"[SUPPORT GARBAGE COLLECTOR] "
                f"#{thread.name} has been inactive for {inactive_for_str}."
            )

            if last_message_time <= one_day_ago:
                self.bot.logger.debug(
                    f"[SUPPORT GARBAGE COLLECTOR] "
                    f"Archiving #{thread.name}..."
                )
                # The last message was sent a day ago, or more.
                # It's time to close the thread.
                async with thread.typing():
                    user = await self.get_user(thread.name)
                    db_user = await get_from_db(user, as_user=True)

                    ticket = await db_user.get_or_create_support_ticket()
                    ticket.close(
                        await get_from_db(self.bot.user, as_user=True),
                        "Automatic closing for inactivity.",
                    )

                    await ticket.save()

                    language = db_user.language
                    _ = get_translate_function(self.bot, language)

                    inactivity_embed = discord.Embed(
                        color=discord.Color.orange(),
                        title=_("DM Timed Out"),
                        description=_(
                            "Tickets expire after 24 hours of inactivity.\n"
                            "Got a question? Ask it here or in [the support server](https://duckhunt.me/support).\n"
                            "Thank you for using the DuckHunt ticket system!"
                        ),
                    )

                    inactivity_embed.add_field(
                        name=_("Support server"),
                        value=_(
                            "For all your questions, there is a support server. "
                            "Click [here](https://duckhunt.me/support) to join."
                        ),
                    )

                    try:
                        await user.send(embed=inactivity_embed)
                    except:
                        pass

                    await self.clear_caches(thread)
                    await thread.edit(archived=True)

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

    async def is_in_forwarding_threads(self, ctx):
        forum = await self.get_forwarding_forum()
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != forum.guild.id:
            raise NotInServer(must_be_in_guild_id=forum.guild.id)
        elif not isinstance(ctx.channel, discord.Thread) or ctx.channel.parent_id != forum.id:
            raise NotInChannel(must_be_in_channel_id=forum.id)
        return True

    async def get_user(self, user_id):
        user_id = int(user_id)
        user = self.users_cache.get(user_id, None)
        if user is None:
            user = await self.bot.fetch_user(user_id)
            self.users_cache[user_id] = user

        return user

    async def get_forwarding_forum(self) -> discord.ForumChannel:
        return self.bot.get_channel(self.config()["forwarding_forum"])

    async def get_forum_tag(self, tag_id: int) -> discord.ForumTag:
        # Check cache first
        if tag_id in self.tags_cache:
            return self.tags_cache[tag_id]
            
        forum = await self.get_forwarding_forum()
        for tag in forum.available_tags:
            if tag.id == tag_id:
                # Cache the tag
                self.tags_cache[tag_id] = tag
                return tag
        raise ValueError(f"Tag with ID {tag_id} not found in forum")

    async def get_or_create_thread(self, user: discord.User) -> discord.Thread:
        user_id = int(user.id)
        forum = await self.get_forwarding_forum()
        blocked_tag = await self.get_forum_tag(self.config()["forum_categories"]["blocked"])
        
        # First check active threads in forum
        for thread in forum.threads:
            if thread.name == str(user.id):
                self.bot.logger.debug(f"[SUPPORT] found thread for {user} in the forum object ({thread.archived=}, {thread.locked=}).")

                if blocked_tag in thread.applied_tags:
                    self.bot.logger.info(f"[SUPPORT] Thread for {user} is blocked. Ignoring.")
                    return None

                return thread
                
        # Then check archived threads cache
        if user_id in self.archived_threads_cache:
            thread = self.archived_threads_cache[user_id]
            self.bot.logger.debug(f"[SUPPORT] found thread for {user} in the archived cache ({thread.archived=}, {thread.locked=}).")
            # Check if thread is in blocked category

            if blocked_tag in thread.applied_tags:
                self.bot.logger.info(f"[SUPPORT] Thread for {user} is blocked. Ignoring.")
                return None
                
            # Unarchive the thread and set it back to open
            open_tag = await self.get_forum_tag(self.config()["forum_categories"]["open"])
            self.bot.logger.info(f"[SUPPORT] Thread for {user} is archived, and we got a new message. Re opening!")
            await thread.edit(archived=False, applied_tags=[open_tag])
            
            # Remove from archived cache since it's now active
            del self.archived_threads_cache[user_id]
            
            # Send a new recap embed
            await self.handle_ticket_opening(thread, user)
            return thread
                
        # Create new thread if none exists
        self.bot.logger.info(f"[SUPPORT] creating a DM thread for {user}.")
        
        now_str = format_datetime(datetime.datetime.now(), locale="en")
        open_tag = await self.get_forum_tag(self.config()["forum_categories"]["open"])
        thread, message = await forum.create_thread(
            name=str(user.id),
            content=f"This is the logs of a DM with {user.name}#{user.discriminator}. "
            f"What's written in there will be sent back to them, except if "
            f"the message starts with > or is a DuckHunt command.\nThread opened: {now_str}",
            reason="Received a DM.",
            applied_tags=[open_tag]
        )
        
        self.bot.logger.debug(f"[SUPPORT] thread created for {user}.")
        await self.handle_ticket_opening(thread, user)
        return thread

    async def send_mirrored_message(
        self,
        channel: discord.Thread,
        user: discord.User,
        db_user=None,
        support_view=None,
        **send_kwargs,
    ):
        self.bot.logger.info(
            f"[SUPPORT] Sending mirror message to {user}"
        )

        db_user = db_user or await get_from_db(user, as_user=True)
        language = db_user.language
        _ = get_translate_function(self.bot, language)

        if support_view:
            channel_message = await support_view.send(channel, **send_kwargs)
        else:
            channel_message = await channel.send(**send_kwargs)

        try:
            await user.send(**send_kwargs)
        except discord.Forbidden:
            await channel_message.add_reaction("❌")
            await channel.send(
                content="❌ Couldn't send the above message, `dh!ps close` to close the channel."
            )

    async def handle_ticket_opening(
        self, thread: discord.Thread, user: discord.User
    ):
        db_user: DiscordUser = await get_from_db(user, as_user=True)
        ticket = await db_user.get_or_create_support_ticket()
        await ticket.save()

        await thread.send(
            content=f"Opening a DM thread with {user} ({user.mention}).\n"
            f"Every message in here will get sent back to them if it's not a bot message, "
            f"DuckHunt command, and if it doesn't start with the > character.\n"
            f"You can use many commands in the DM threads, detailed in "
            f"`dh!help private_support`\n"
            f"• `dh!ps close` will close the thread, sending a DM to the user.\n"
            f"• `dh!ps tag tag_name` will send a tag to the user *and* in the thread. "
            f"The two are linked, so changing pages in this thread "
            f"will change the page in the DM too.\n"
            f"• `dh!ps block` will block the user from opening further threads.\n"
            f"• `dh!ps huh` should be used if the message is not a support request, "
            f"and will silently close the thread.\n"
            f"Attachments are supported in messages.\n\n"
            f"Thanks for helping with the bot DM support ! <3"
        )

        players_data = (
            await Player.all()
            .filter(member__user=db_user)
            .order_by("-last_giveback")
            .select_related("channel")
            .limit(5)
        )

        info_embed = discord.Embed(
            color=discord.Color.blurple(), title="Support information"
        )

        info_embed.description = (
            "Information in this box isn't meant to be shared outside of this thread, and is "
            "provided for support purposes only. \n"
            "Nothing was sent to the user about this."
        )

        info_embed.set_author(
            name=f"{user}",
            icon_url=str(user.display_avatar.url),
        )
        info_embed.set_footer(text="Private statistics")

        ticket_count = await db_user.support_ticket_count()
        info_embed.add_field(
            name="User language", value=str(db_user.language), inline=True
        )

        if db_user.access_level_override != AccessLevel.DEFAULT:
            info_embed.add_field(
                name="Access Level",
                value=str(db_user.access_level_override.name),
                inline=True,
            )

        fs_td = format_timedelta(
            db_user.first_seen - timezone.now(),
            granularity="minute",
            add_direction=True,
            format="short",
            locale="en",
        )

        info_embed.add_field(name="First seen", value=str(fs_td), inline=True)
        info_embed.add_field(
            name="Tickets created", value=str(ticket_count), inline=True
        )

        if ticket_count > 1:
            async for ticket in SupportTicket.filter(user=db_user, closed=True).order_by("-opened_at").select_related("closed_by", "last_tag_used").limit(5):
                ftd = format_timedelta(
                    ticket.closed_at - timezone.now(),
                    granularity="minute",
                    add_direction=True,
                    format="short",
                    locale="en",
                )
                if ticket.closed_by:
                    value = f"Closed {ftd} by {ticket.closed_by.name}."
                else:
                    value = f"Closed {ftd} by the bot."

                if ticket.close_reason:
                    value += f"\n{ticket.close_reason}"

                if ticket.last_tag_used_id:
                    tag: Tag = ticket.last_tag_used
                    value += f"\nLast tag sent: {tag.name}"

                info_embed.add_field(name=f"Ticket n°{ticket.pk}", value=value, inline=False)

        for player_data in players_data:
            if player_data.channel.enabled:
                info_embed.add_field(
                    name=f"#{player_data.channel} - {player_data.experience} exp",
                    value=f"[Statistics](https://duckhunt.me/data/channels/{player_data.channel.discord_id}/{user.id})",
                )
            else:
                info_embed.add_field(
                    name=f"#{player_data.channel} [DISABLED]",
                    value=f"[Statistics](https://duckhunt.me/data/channels/{player_data.channel.discord_id}/{user.id}) - {player_data.experience} exp",
                )

        await CloseReasonSelectView(self.bot).send(thread, embed=info_embed)

        _ = get_translate_function(self.bot, db_user.language)

        welcome_embed = discord.Embed(
            color=discord.Color.green(), title="Support ticket opened"
        )
        welcome_embed.description = _(
            "DMing any message to the bot will open a ticket.\n"
            "You have a question? [Ask it](https://dontasktoask.com) to our human volunteers.\n"
            "You opened the ticket by mistake? Type `close` (*once, no prefix needed*) and we, human volunteers will close it."
        )

        welcome_embed.set_footer(
            text=_(
                "Support tickets are automatically archived after 24 hours of inactivity"
            )
        )

        try:
            await user.send(embed=welcome_embed)
        except discord.Forbidden:
            await thread.send(
                content="❌ It seems I can't send messages to the user, you might want to close the DM. "
                "`dh!ps close`."
            )

    async def handle_support_message(self, message: discord.Message):
        user = await self.get_user(message.channel.name)
        db_user = await get_from_db(user, as_user=True)
        language = db_user.language

        self.bot.logger.info(
            f"[SUPPORT] answering {user} with a message from {message.author}"
        )

        _ = get_translate_function(self.bot, language)

        support_embed = discord.Embed(
            color=discord.Color.blurple(), title="Support response"
        )
        support_embed.set_author(
            name=f"{message.author}",
            icon_url=str(message.author.display_avatar.url),
        )
        support_embed.description = message.content

        if len(message.attachments) == 1:
            url = str(message.attachments[0].url)
            if not message.channel.nsfw and (
                url.endswith(".webp") or url.endswith(".png") or url.endswith(".jpg")
            ):
                support_embed.set_image(url=url)
            else:
                support_embed.add_field(name="Attached", value=url)

        elif len(message.attachments) > 1:
            for attach in message.attachments:
                support_embed.add_field(name="Attached", value=attach.url)

            support_embed.add_field(
                name=_("Attachments persistence"),
                value=_(
                    "Images and other attached data to the message will get deleted "
                    "once your ticket is closed. "
                    "Make sure to save them beforehand if you wish."
                ),
            )

        try:
            await user.send(embed=support_embed)
        except Exception as e:
            await message.channel.send(
                f"❌: {e}\nYou can use `dh!private_support close` to close the channel."
            )

    async def handle_auto_responses(self, message: discord.Message):
        forwarding_channel = await self.get_or_create_thread(message.author)

        if forwarding_channel is None:
            # Thread is in blocked category
            return

        content = message.content

        user = message.author
        db_user = await get_from_db(message.author, as_user=True)
        language = db_user.language
        _ = get_translate_function(self.bot, language)

        if self.invites_regex.search(content):
            dm_invite_embed = discord.Embed(
                color=discord.Color.purple(),
                title=_("This is not how you invite DuckHunt."),
            )
            dm_invite_embed.description = _(
                "To invite DuckHunt, you need :\n"
                "- To be a server Administrator.\n"
                "- To click on the [following link](https://duckhunt.me/invite)\n"
                "More info on [this guide](https://duckhunt.me/docs/bot-administration/admin-quickstart). If you need more help, "
                "you can ask here and we'll get back to you."
            )

            dm_invite_embed.set_footer(text=_("This is an automatic message."))

            view = get_close_reason_view(self.bot, "invites", "Sent the bot an invite")

            await self.send_mirrored_message(
                forwarding_channel,
                user,
                db_user=db_user,
                embed=dm_invite_embed,
                support_view=view,
            )

    async def handle_dm_message(self, message: discord.Message):
        self.bot.logger.info(
            f"[SUPPORT] received a message from {message.author}"
        )
        await self.bot.wait_until_ready()

        thread = await self.get_or_create_thread(message.author)
        if thread is None:  # Thread is in blocked category
            return

        self.bot.logger.debug(
            f"[SUPPORT] got {message.author} thread."
        )

        attachments = message.attachments
        files = [await attach.to_file() for attach in attachments]
        embeds = message.embeds

        self.bot.logger.debug(
            f"[SUPPORT] {message.author} message prepared."
        )

        send_kwargs = {
            "content": message.content,
            "embeds": embeds,
            "files": files,
            "allowed_mentions": discord.AllowedMentions.none(),
        }

        if "close" in message.content.lower():
            view = get_close_reason_view(self.bot, "asked", "Asked closed")
            await view.send(thread, **send_kwargs)
        else:
            await thread.send(**send_kwargs)

        self.bot.logger.debug(
            f"[SUPPORT] {message.author} message forwarded."
        )

    async def clear_caches(self, thread: discord.Thread):
        try:
            user_id = int(thread.name)
            # Clear user cache
            self.users_cache.pop(user_id)
            # Clear thread caches
            # self.archived_threads_cache.pop(user_id, None)
        except (KeyError, ValueError):
            # Cog reload, probably.
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            # Don't listen to bots (ourselves in this case)
            return

        if not message.content and not message.attachments:
            # Message has no text and no attachments
            return

        guild = message.guild
        ctx = await self.bot.get_context(message, cls=MyContext)
        if ctx.valid:
            # It's just a command.
            return

        if guild:
            if (
                isinstance(message.channel, discord.Thread)
                and message.channel.parent == await self.get_forwarding_forum()
            ):
                if message.content.startswith(">"):
                    return
                # This is a support message.
                async with message.channel.typing():
                    await self.handle_support_message(message)
        else:
            # New DM message.
            await self.handle_dm_message(message)
            await self.handle_auto_responses(message)

    @commands.group(aliases=["ps"])
    async def private_support(self, ctx: MyContext):
        """
        The DuckHunt bot DMs are monitored. All of these commands are used to control the created channels, and to
        interact with remote users.
        """
        await self.is_in_forwarding_threads(ctx)

        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @private_support.command()
    async def close(self, ctx: MyContext, *, reason: str = None):
        """
        Close the opened DM thread. Will send a message telling the user that the DM was closed.
        """
        await self.is_in_forwarding_threads(ctx)

        user = await self.get_user(ctx.channel.name)
        db_user = await get_from_db(user, as_user=True)

        ticket = await db_user.get_or_create_support_ticket()
        ticket.close(await get_from_db(ctx.author, as_user=True), reason)

        await ticket.save()

        language = db_user.language
        _ = get_translate_function(self.bot, language)

        close_embed = discord.Embed(
            color=discord.Color.red(),
            title=_("DM Closed"),
            description=_(
                "Your support ticket was closed and the history archived. "
                "Thanks for using DuckHunt DM support. "
                "Keep in mind, sending another message here will open a new ticket!\n"
                "In the meantime, here's a nice duck picture for you to look at !",
                ctx=ctx,
            ),
        )

        close_embed.add_field(
            name=_("Support server"),
            value=_(
                "For all your questions, there is a support server. "
                "Click [here](https://duckhunt.me/support) to join."
            ),
        )

        file, debug = await get_random_duck_file(self.bot)
        close_embed.set_image(url="attachment://random_duck.png")

        await ctx.send(content="🚮 Archiving thread...")

        try:
            await user.send(file=file, embed=close_embed)
        except:
            pass

        closed_tag = await self.get_forum_tag(self.config()["forum_categories"]["closed"])
        await ctx.channel.edit(
            archived=True,
            applied_tags=[closed_tag],
            reason=f"{ctx.author} ({ctx.author.id}) closed the DM."
        )
        
        # Update thread caches
        user_id = int(ctx.channel.name)
        self.archived_threads_cache[user_id] = ctx.channel

    @private_support.command(aliases=["not_support", "huh"])
    async def close_silent(self, ctx: MyContext, *, reason: str = None):
        """
        Close the opened DM thread. Will not send a message, since it wasn't a support request.
        """
        await self.is_in_forwarding_threads(ctx)

        if reason is None:
            reason = "Closed silently."

        user = await self.get_user(ctx.channel.name)
        db_user = await get_from_db(user, as_user=True)

        ticket = await db_user.get_or_create_support_ticket()
        ticket.close(await get_from_db(ctx.author, as_user=True), reason)

        await ticket.save()

        async with ctx.typing():
            await ctx.send(content="🚮 Archiving thread..?")

            closed_tag = await self.get_forum_tag(self.config()["forum_categories"]["closed"])
            await ctx.channel.edit(
                archived=True,
                applied_tags=[closed_tag],
                reason=f"{ctx.author} ({ctx.author.id}) closed the DM."
            )
            
            # Update thread caches
            user_id = int(ctx.channel.name)
            self.archived_threads_cache[user_id] = ctx.channel

    @private_support.command()
    @dont_block
    async def block(self, ctx: MyContext):
        """
        Block the user from opening further DMs channels.
        """
        await self.is_in_forwarding_threads(ctx)

        blocked_tag = await self.get_forum_tag(self.config()["forum_categories"]["blocked"])
        await ctx.channel.edit(
            applied_tags=[blocked_tag],
            reason=f"{ctx.author} ({ctx.author.id}) blocked the user.",
            locked=True,
        )

        # Update thread caches
        user_id = int(ctx.channel.name)
        self.archived_threads_cache[user_id] = ctx.channel


        await ctx.send("👌 User blocked and thread marked as blocked.")

    @private_support.command(aliases=["send_tag", "t"])
    @dont_block
    async def tag(self, ctx: MyContext, *, tag_name: TagName):
        """
        Send a tag to the user, as if you used the dh!tag command in his DMs.
        """
        await self.is_in_forwarding_threads(ctx)

        user = await self.get_user(ctx.channel.name)
        tag = await get_tag(tag_name)

        if tag:
            db_user = await get_from_db(user, as_user=True)
            ticket = await db_user.get_or_create_support_ticket()

            ticket.last_tag_used = tag
            await ticket.save()

            support_pages = MirrorMenuPage(
                timeout=86400,
                source=TagMenuSource(ctx, tag),
                clear_reactions_after=True,
            )
            dm_pages = MirrorMenuPage(
                timeout=86400,
                source=TagMenuSource(ctx, tag),
                clear_reactions_after=True,
            )

            dm_pages.other = support_pages
            support_pages.other = dm_pages

            await support_pages.start(ctx)
            try:
                await dm_pages.start(ctx, channel=await user.create_dm())
            except discord.Forbidden as e:
                _ = await ctx.get_translate_function()
                await ctx.reply(_("❌ Can't send a message to this user: {e}.", e=e))
        else:
            _ = await ctx.get_translate_function()
            await ctx.reply(_("❌ There is no tag with that name."))

    @private_support.command(aliases=["sl"])
    async def suggest_language(self, ctx: MyContext, *, language_code):
        """
        Suggest a new language to the user. This will show them a prompt asking them if they want to switch to this new
        language.
        """
        await self.is_in_forwarding_threads(ctx)

        user = await self.get_user(ctx.channel.name)
        db_user = await get_from_db(user, as_user=True)

        if db_user.language.casefold() == language_code.casefold():
            await ctx.reply(f"❌ The user language is already set to {db_user.language}")
            return

        try:
            suggested_locale = Locale.parse(language_code)
        except (babel.UnknownLocaleError, ValueError):
            await ctx.reply(
                "❌ Unknown locale. You need to provide a language code here, like `fr`, `es`, `en`, ..."
            )
            return

        current_locale = Locale.parse(db_user.language)

        _ = get_translate_function(ctx, language_code)

        embed = discord.Embed(
            colour=discord.Colour.blurple(), title=_("Language change offer")
        )

        embed.description = _(
            "DuckHunt support suggests you change your personal language "
            "from {current_language} to {suggested_language}. This will translate "
            "all the messages you get in private message from DuckHunt to {suggested_language}.",
            current_language=current_locale.get_display_name(language_code),
            suggested_language=suggested_locale.get_display_name(language_code),
        )

        embed.set_author(
            name=f"{ctx.author}",
            icon_url=str(ctx.author.display_avatar.url),
        )

        embed.set_footer(
            text=_(
                "Press ✅ to accept the change, or do nothing to reject. "
                "Use the [dh!settings my_lang language_code] command in a game channel to edit later."
            )
        )

        message = await user.send(embed=embed)
        await message.add_reaction("✅")

        # Do it, but don't block it
        asyncio.ensure_future(
            self.language_change_interaction(
                ctx, db_user, user, language_code, suggested_locale
            )
        )
        await ctx.message.add_reaction("<a:typing:1067431760331284551>")

    async def language_change_interaction(
        self, ctx, db_user, user, language_code, suggested_locale
    ):
        def check(payload: RawReactionActionEvent):
            return (
                payload.user_id == user.id
                and str(payload.emoji) == "✅"
                and payload.guild_id is None
            )

        try:
            payload = await self.bot.wait_for(
                "raw_reaction_add", timeout=86400, check=check
            )
        except asyncio.TimeoutError:
            _ = get_translate_function(ctx, db_user.language)
            await user.send(_("Your language preference wasn't changed."))
            await ctx.message.add_reaction("❌")
            await ctx.reply("Language change timed out.")
        else:
            async with user.dm_channel.typing():
                db_user = await get_from_db(user, as_user=True)
                db_user.language = language_code
                await db_user.save()
                _ = get_translate_function(ctx, language_code)

            await user.send(
                _(
                    "Your preferred language is now {new_language}.",
                    new_language=suggested_locale.get_display_name(),
                )
            )

            await ctx.message.add_reaction("✅")
            await ctx.reply("Language change accepted.")


setup = PrivateMessagesSupport.setup
