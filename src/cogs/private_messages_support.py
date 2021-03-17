import datetime
from typing import Dict, List

import discord
from babel.dates import format_datetime
from discord.ext import commands

from utils.bot_class import MyBot
from utils.checks import NotInServer, BotIgnore, NotInChannel
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db
from utils.translations import get_translate_function


class PrivateMessagesSupport(Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self._forwarding_category = None
        self.webhook_cache: Dict[discord.TextChannel, discord.Webhook] = {}
        self.users_cache: Dict[int, discord.User] = {}
        self.blocked_ids: List[int] = []

    async def is_in_forwarding_channels(self, ctx):
        category = await self.get_forwarding_category()
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != category.guild.id:
            raise NotInServer(must_be_in_guild_id=category.guild.id)
        elif ctx.channel.category != category:
            raise NotInChannel(must_be_in_channel_id=category.id)
        return True

    async def get_user(self, user_id):
        user_id = int(user_id)
        user = self.users_cache.get(user_id, None)
        if user is None:
            user = await self.bot.fetch_user(user_id)
            self.users_cache[user_id] = user

        return user

    async def get_forwarding_category(self) -> discord.CategoryChannel:
        if self._forwarding_category is None:
            self._forwarding_category = self.bot.get_channel(self.config()['forwarding_category'])

        return self._forwarding_category

    async def get_or_create_channel(self, user: discord.User) -> discord.TextChannel:
        forwarding_category = await self.get_forwarding_category()

        channel = discord.utils.get(forwarding_category.text_channels, name=str(user.id))
        if not channel:
            now_str = format_datetime(datetime.datetime.now(), locale='en')
            channel = await forwarding_category.create_text_channel(
                name=str(user.id),
                topic=f"This is the logs of a DM with {user.name}#{user.discriminator}. "
                      f"What's written in there will be sent back to him, except if "
                      f"the message starts with # or is a DuckHunt command.\nChannel opened: {now_str}",
                reason="Received a DM.")

            webhook = await channel.create_webhook(name=f"{user.name}#{user.discriminator}",
                                                   avatar=await user.avatar_url.read(),
                                                   reason="Received a DM.")
            self.webhook_cache[channel] = webhook
        else:
            if self.webhook_cache.get(channel, None) is None:
                webhook = (await channel.webhooks())[0]
                self.webhook_cache[channel] = webhook
        return channel

    async def handle_support_message(self, message: discord.Message):
        user = await self.get_user(message.channel.name)
        db_user = await get_from_db(user, as_user=True)
        language = db_user.language

        _ = get_translate_function(self.bot, language)

        support_embed = discord.Embed(color=discord.Color.blurple(), title="Support response")
        support_embed.set_author(name=f"{message.author.name}#{message.author.discriminator}",
                                 icon_url=str(message.author.avatar_url))
        support_embed.description = message.content

        if len(message.attachments) == 1:
            url = str(message.attachments[0].url)
            if not message.channel.nsfw \
                    and (url.endswith(".webp") or url.endswith(".png") or url.endswith(".jpg")):
                support_embed.set_image(url=url)
            else:
                support_embed.add_field(name="Attached", value=url)

        elif len(message.attachments) > 1:
            for attach in message.attachments:
                support_embed.add_field(name="Attached", value=attach.url)

            support_embed.add_field(name=_("Attachments persistance"),
                                    value=_(
                                        "Images and other attached data to the message will get deleted "
                                        "once your ticket is closed. "
                                        "Make sure to save them beforehand if you wish."))

        try:
            await user.send(embed=support_embed)
        except Exception as e:
            await message.channel.send(f"❌: {e}\nYou can use `dh!private_support close` to close the channel.")

    async def handle_dm_message(self, message: discord.Message):
        await self.bot.wait_until_ready()

        if message.author.id in self.blocked_ids:
            return

        forwarding_channel = await self.get_or_create_channel(message.author)
        forwarding_webhook = self.webhook_cache[forwarding_channel]

        attachments = message.attachments
        files = [await attach.to_file() for attach in attachments]
        embeds = message.embeds

        await forwarding_webhook.send(content=message.content,
                                      embeds=embeds,
                                      files=files,
                                      allowed_mentions=discord.AllowedMentions.none(),
                                      wait=True)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            # Don't listen to bots (ourselves in this case)
            return

        if message.guild:
            if message.channel.category == await self.get_forwarding_category():
                # This is a support message.
                await self.handle_support_message(message)
        else:
            ctx = await self.bot.get_context(message, cls=MyContext)
            if ctx.valid:
                # It's just a command.
                return

            # New DM message.
            await self.handle_dm_message(message)

    @commands.group(aliases=["ps"])
    async def private_support(self, ctx: MyContext):
        """
        The DuckHunt bot DMs are monitored. All of these commands are used to control the created channels, and to
        interact with remote users.
        """
        await self.is_in_forwarding_channels(ctx)

        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @private_support.command()
    async def close(self, ctx: MyContext):
        """
        Close the opened DM channel. Will send a message telling the user that the DM was closed.
        """
        await self.is_in_forwarding_channels(ctx)

        user = await self.get_user(ctx.channel.name)
        db_user = await get_from_db(user, as_user=True)
        language = db_user.language

        _ = get_translate_function(self.bot, language)

        close_embed = discord.Embed(
            color=discord.Color.red(),
            title=_("DM Closed"),
            description=_("Your support ticket was closed. Thanks for using DuckHunt DM support.", ctx=ctx),
        )

        close_embed.add_field(name=_("Support server"), value=_("For all your questions, there is a support server. "
                                                                "Click [here](https://discord.gg/G4skWae) to join."))

        async with ctx.typing():
            await user.send(embed=close_embed)
            await ctx.channel.delete(
                reason=f"{ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) closed the DM.")

    @private_support.command()
    async def block(self, ctx: MyContext):
        """
        Block the user from opening further DMs channels.
        """
        await self.is_in_forwarding_channels(ctx)

        self.blocked_ids.append(int(ctx.channel.name))
        await ctx.send("👌")


setup = PrivateMessagesSupport.setup
