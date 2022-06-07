import asyncio
import datetime
import random
import time

import discord
from babel import Locale
from babel.dates import format_timedelta, format_datetime
from babel.lists import format_list
from discord.ext import commands, menus

from utils import checks
from utils.bot_class import MyBot
from utils.cog_class import Cog
from utils.concurrency import dont_block
from utils.ctx_class import MyContext
from utils.images import get_random_image
from utils.inventory_items import FoieGras
from utils.models import get_from_db, AccessLevel
from utils.translations import TRANSLATORS, get_pct_complete

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def _(message):
    return message


class TranslatorsMenusSource(menus.ListPageSource):
    def __init__(self, ctx: MyContext, translators):
        super().__init__(list(translators.items()), per_page=6)
        self.ctx = ctx
        self.translators_cache = None

    async def format_page(self, menu, entries):
        _ = await self.ctx.get_translate_function()
        language_code = await self.ctx.get_language_code()

        embed = discord.Embed(title=_("The beloved DuckHunt translators"))

        embed.color = discord.Color.green()
        embed.description = _("The bot itself is made by Eyesofcreeper, with contributions from people mentionned in "
                              "`{ctx.prefix}credits`. **You want to help translate this bot ?** "
                              "Contact Eyesofcreeper#0001 on the support server (`{ctx.prefix}invite`). Thanks!")

        offset = menu.current_page * self.per_page
        for i, item in enumerate(entries, start=offset):
            locale, translators = item

            parsed_translators = []

            for user in translators:
                parsed_translators.append(f"{user.name}#{user.discriminator}")

            try:
                locale_data = Locale.parse(locale)
                locale_display_name = locale_data.get_display_name(language_code)
            except ValueError:
                locale_display_name = locale

            embed.add_field(name=f"{locale_display_name}: `{locale}` - {get_pct_complete(locale)}%",
                            value=format_list(parsed_translators, locale=language_code),
                            inline=False)

        return embed


async def show_translators_menu(ctx, translators):
    pages = menus.MenuPages(source=TranslatorsMenusSource(ctx, translators), clear_reactions_after=True)
    await pages.start(ctx)


class SimpleCommands(Cog):
    display_name = _("Miscellaneous")
    help_priority = 10

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.translators_cache = {}

    @commands.command()
    async def ping(self, ctx: MyContext):
        """
        Check that the bot is online, give the latency between the bot and Discord servers.
        """
        _ = await ctx.get_translate_function()

        t_1 = time.perf_counter()
        await ctx.typing()  # tell Discord that the bot is "typing", which is a very simple request
        t_2 = time.perf_counter()
        time_delta = round((t_2 - t_1) * 1000)  # calculate the time needed to trigger typing
        await ctx.send(_("Pong. — Time taken: {miliseconds}ms",
                         miliseconds=time_delta))  # send a message telling the user the calculated ping time

    @commands.command()
    async def wiki(self, ctx: MyContext):
        """
        Returns the wiki URL
        """
        _ = await ctx.get_translate_function()

        wiki_url = self.config()["wiki_url"]

        await ctx.send(_(wiki_url))

    @commands.command()
    async def invite(self, ctx: MyContext):
        """
        Get the URL to invite the bot
        """

        await ctx.send(
            f"<https://duckhunt.me/invite>")

    @commands.command()
    async def support(self, ctx: MyContext):
        """
        Get a discord invite to the support server.
        """
        await ctx.send(f"<https://duckhunt.me/support>")

    @commands.command(aliases=["giveback", "ft"])
    @checks.channel_enabled()
    async def freetime(self, ctx: MyContext):
        """
        Get the time when you'll get free magazines and your weapon back from the police
        """

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()

        now = int(time.time())
        SECONDS_SPENT_TODAY = now % 86400
        SECONDS_LEFT_TODAY = 86400 - SECONDS_SPENT_TODAY
        time_delta = datetime.timedelta(seconds=SECONDS_LEFT_TODAY)

        formatted_delta = format_timedelta(time_delta, add_direction=True, locale=language_code)
        formatted_precise_delta = format_timedelta(time_delta, add_direction=True, locale=language_code, threshold=24)

        await ctx.send(_("You'll get back your weapon and magazines {formatted_delta} ({formatted_precise_delta})",
                         formatted_delta=formatted_delta,
                         formatted_precise_delta=formatted_precise_delta,
                         ))

    @commands.command()
    @checks.channel_enabled()
    async def prefix(self, ctx: MyContext):
        """
        Get the bot prefixes
        """
        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()

        global_prefixes = self.bot.config['bot']['prefixes']
        local_prefix = (await get_from_db(ctx.guild)).prefix

        global_prefixes_list = format_list(global_prefixes, locale=language_code)

        if local_prefix:
            await ctx.send(_(
                "My prefix here is {local_prefix}. You can also call me with any of the global prefixes : {global_prefixes_list}",
                local_prefix=local_prefix,
                global_prefixes_list=global_prefixes_list))
        else:
            await ctx.send(_("You can call me with any of the global prefixes : {global_prefixes_list}",
                             global_prefixes_list=global_prefixes_list))

    @commands.command(aliases=["helpers", "whomadethis"])
    async def credits(self, ctx: MyContext):
        """
        Thanks to those fine people who (helped) make the bot
        """
        _ = await ctx.get_translate_function()

        my_perms = ctx.channel.permissions_for(ctx.me)

        if my_perms.embed_links:
            embed = discord.Embed()

            embed.color = discord.Color.green()
            embed.description = _("The bot itself is made by Eyesofcreeper, but these fine people down there help with "
                                  "graphics, ideas, images, and more. Make sure to give them a wave if you see them.")

            embed.add_field(name=_("Developer"), value=_("<@138751484517941259> (\"Eyesofcreeper\") made this bot."), inline=False)
            embed.add_field(name=_("Designer"), value=_("<@465207298890006529> (\"Calgeka\") made a lot of the avatars Ducks used."), inline=False)
            embed.add_field(name=_("Designer"), value=_("<@376052158573051906> (\"Globloxmen\") made a lot of ducks you can find all over the game. Join the /r/dailyducks subreddit."), inline=False)
            embed.add_field(name=_("Ideas"), value=_("Bot based on an original idea by MenzAgitat (on IRC, #boulets EpiKnet). Website: https://www.boulets.oqp.me/irc/aide_duck_hunt.html"), inline=False)
            embed.add_field(name=_("Translations"), value=_("The bot is translated in MANY languages! Translators are listed in `{ctx.prefix}translators`."), inline=False)

            f = discord.File("assets/Robot_Ducc_Globloxmen.jpg")
            embed.set_image(url=f"attachment://Robot_Ducc_Globloxmen.jpg")

            await ctx.send(embed=embed, file=f)
        else:
            await ctx.send(content="\n".join([_("**DuckHunt credits**"),
                                              _("The bot itself is made by Eyesofcreeper, but a lot of people "
                                   "helped with graphics, ideas, images, and more."),
                                              _("To see more information about that bot, you'll need to give it the "
                                                "`embed_links` permission. Contact your friendly neighbourhood server "
                                                "admin.")]))

    @commands.command(aliases=["translate"])
    async def translators(self, ctx: MyContext):
        """
        Thanks to those fine people who (helped) translate the bot
        """
        _ = await ctx.get_translate_function()

        if not len(self.translators_cache):
            for locale, translators_ids in TRANSLATORS.items():
                self.translators_cache[locale] = []
                for translator_id in translators_ids:
                    try:
                        self.translators_cache[locale].append(await ctx.bot.fetch_user(translator_id))
                    except discord.NotFound:
                        ctx.logger.warning(f"Translator {translator_id} for language {locale} can't be found on discord.")
                        continue

        await show_translators_menu(ctx, self.translators_cache)

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def pee(self, ctx: MyContext):
        """
        For when you misspell the pan command.
        """
        _ = await ctx.get_translate_function()

        await ctx.reply(_("You don't have to go right now"))

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def reloaf(self, ctx: MyContext):
        """
        For when you misspell the reload command.
        """
        await ctx.reply("🍞")

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def eye(self, ctx: MyContext):
        """
        I only get one eye
        """
        await ctx.reply("👁️")

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def eyes(self, ctx: MyContext):
        """
        Who doesn't need eyes
        """
        await ctx.reply("👀")

    @commands.command(hidden=True, aliases=["girafe", "giraf"])
    @checks.channel_enabled()
    async def giraffe(self, ctx: MyContext):
        """
        I hav long nek
        """
        await ctx.reply("🦒")

    @commands.command(hidden=True,)
    @checks.channel_enabled()
    @checks.is_in_server(195260081036591104)
    async def impossible(self, ctx: MyContext):
        """
        It's impossible.
        """
        await ctx.reply("And yet, it's <@202484200438366208>")

    @commands.command(hidden=True)
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    @dont_block
    async def vote_boss_spawn(self, ctx: MyContext, yes_trigger: int = 5, no_trigger: int = 1, time_to_wait: int = 60):
        """
        Vote for a boss to spawn for a minute.
        This is an unfair vote: while it needs people to vote quickly for a boss,
        if someones vote against, the boss won't spawn.
        """
        ftd = format_timedelta(datetime.timedelta(seconds=time_to_wait), locale='en', threshold=1.1)
        message = await ctx.send('**A vote to spawn a boss is in progress**\n'
                                 f'React with 🦆 to spawn a boss (needs {yes_trigger} votes in {ftd}), or\n'
                                 f'React with ❌ to prevent the boss spawn (needs {no_trigger} votes in {ftd}, '
                                 f'wins in the case of a tie)\n'
                                 f'➡️ If **exactly** {no_trigger} no votes are casted, no-voters will receive 2 boxes '
                                 f'of foie gras each.\n'
                                 f'Yes, this is a social experiment, and it\'s starting **NOW**.')

        await message.add_reaction("🦆")
        await message.add_reaction("❌")

        await asyncio.sleep(int((time_to_wait - 10)/2))
        to_delete = await ctx.reply("⏰ Halfway there...")
        await asyncio.sleep(int((time_to_wait - 10)/2))
        await to_delete.delete()
        to_edit = await ctx.reply("⏰ 10 seconds left...")
        await asyncio.sleep(5)
        await to_edit.edit(content="⏰ 5 seconds left...")
        await asyncio.sleep(5)
        await to_edit.edit(content="⏰ And done...")

        try:
            message = await ctx.channel.fetch_message(message.id)
        except:
            await ctx.reply("❌ Re-fetching the message failed. Cancelling.")

        got_yes = 0
        got_no = 0
        no_react = None

        for reaction in message.reactions:
            if str(reaction.emoji) == "❌":
                got_no = reaction.count
                no_react = reaction
            elif str(reaction.emoji) == "🦆":
                got_yes = reaction.count

        # Remove our own
        got_yes -= 1
        got_no -= 1

        if got_no == no_trigger:
            await message.reply(f"Got exactly {got_no} no votes. Giving them 2 boxes of foie gras each..")
            async for user in no_react.users():
                await FoieGras.give_to(user, uses=2)
            return
        elif got_no > no_trigger:
            await message.reply(f"Got {got_no} no votes. Not spawning a boss.")
            return
        elif got_yes < yes_trigger:
            await message.reply(f"Didn't get enough yes votes ({got_yes} < {yes_trigger}). Not spawning a boss.")
            return
        elif got_yes >= yes_trigger:
            await message.reply(f"🦆 Alright. I'm spawning a boss. Congratulations.")
            boss_cog = self.bot.get_cog('DuckBoss')
            await boss_cog.spawn_boss()

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def cow(self, ctx: MyContext):
        """
        Who doesn't need cows ?
        """
        _ = await ctx.get_translate_function()

        if "🐮" in ctx.author.name:
            await ctx.reply(_("Hi, fellow cow lover"))
        else:
            await ctx.reply("🐄")

    @commands.command(hidden=True, aliases=["foot"])
    @checks.channel_enabled()
    async def feet(self, ctx: MyContext):
        """
        When you don't have eyes
        """
        await ctx.reply(random.choice(["🦶", "👣", "🦶🏻", "🦶🏼", "🦶🏽", "🦶🏾", "🦶🏿"]))

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def huh(self, ctx: MyContext):
        """
        I guess that just says ¯\\_(ツ)_/¯
        """
        await ctx.reply(r"¯\_(ツ)_/¯")

    @commands.command(hidden=True)
    @checks.channel_enabled()
    async def lol(self, ctx: MyContext):
        """
        When you need some good laughs
        """
        await ctx.reply("🤣")

    @commands.command(aliases=["events"])
    @checks.channel_enabled()
    async def event(self, ctx: MyContext):
        """
        See the current global event.

        Events are rolled by the bot at the start of each hour, and last for one full hour.
        Many events exist, and you will want to take advantage of seeing them, as they can bring you luck, money or even
        better : EXPERIENCE !
        """
        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()

        now = time.time()
        seconds_left = (60*60) - now % (60*60)

        td = datetime.timedelta(seconds=seconds_left)

        embed = discord.Embed(title=_("Current event: ") + _(self.bot.current_event.value[0]))
        embed.description = _(self.bot.current_event.value[1])

        formatted_td = format_timedelta(td, threshold=10, granularity='minute', locale=language_code)

        embed.set_footer(text=_("Events last for one hour from the beginning to the end of the hour. Ending in {formatted_td}",
                                formatted_td=formatted_td))

        embed.color = discord.Color.dark_theme()

        await ctx.send(embed=embed)

    @commands.command()
    @checks.channel_enabled()
    async def time(self, ctx: MyContext):
        """
        This returns the current bot time.
        """

        language_code = await ctx.get_language_code()
        now = datetime.datetime.utcnow()
        await ctx.reply(format_datetime(now, format='full', locale=language_code))


setup = SimpleCommands.setup
