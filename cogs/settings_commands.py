"""
Commands to change settings in a channel/server

These commands act where they are typed!
"""
from typing import Optional

import babel.lists
import babel.numbers

from babel import Locale

from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

from utils import checks, ducks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.ducks_config import max_ducks_per_day
from utils.interaction import create_and_save_webhook
from utils.models import get_from_db


class SettingsCommands(Cog):
    @commands.group(aliases=["set"])
    async def settings(self, ctx: MyContext):
        """
        Commands to view and edit settings
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @settings.group(aliases=["template", "preset", "presets"])
    async def templates(self, ctx: MyContext):
        """
        Set your server settings to specific, designed modes
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    # Templates #

    @templates.command(aliases=["dhv3", "version3", "old"])
    async def v3(self, ctx: MyContext):
        """
        Restore similar settings to DuckHunt V3, if that's your thing.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        db_channel.use_webhooks = False

        db_channel.allow_global_items = False

        db_channel.mentions_when_killed = False
        db_channel.show_duck_lives = False

        db_channel.kill_on_miss_chance = 5
        db_channel.duck_frighten_chance = 3

        db_channel.spawn_weight_normal_ducks = 100
        db_channel.spawn_weight_super_ducks = 5
        db_channel.spawn_weight_baby_ducks = 3
        db_channel.spawn_weight_prof_ducks = 0
        db_channel.spawn_weight_ghost_ducks = 0
        db_channel.spawn_weight_moad_ducks = 2
        db_channel.spawn_weight_mechanical_ducks = 0
        db_channel.spawn_weight_armored_ducks = 0
        db_channel.spawn_weight_golden_ducks = 0
        db_channel.spawn_weight_plastic_ducks = 0
        db_channel.spawn_weight_kamikaze_ducks = 0

        db_channel.super_ducks_min_life = 3
        db_channel.super_ducks_max_life = 6

        await db_channel.save()

        await ctx.send(_("DHV3-Like settings have been applied to this channel.", ))

    @templates.command()
    async def casual(self, ctx: MyContext):
        """
        Set the bot for a more casual experience.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        db_channel.use_webhooks = True
        db_channel.use_emojis = True

        db_channel.allow_global_items = True

        db_channel.tax_on_user_send = 0
        db_channel.mentions_when_killed = True
        db_channel.show_duck_lives = True

        db_channel.kill_on_miss_chance = 1
        db_channel.duck_frighten_chance = 2

        db_channel.clover_min_experience = 5
        db_channel.clover_max_experience = 15

        db_channel.base_duck_exp = 15
        db_channel.per_life_exp = 8

        db_channel.spawn_weight_normal_ducks = 100
        db_channel.spawn_weight_super_ducks = 15
        db_channel.spawn_weight_baby_ducks = 3
        db_channel.spawn_weight_prof_ducks = 2
        db_channel.spawn_weight_ghost_ducks = 5
        db_channel.spawn_weight_moad_ducks = 10
        db_channel.spawn_weight_mechanical_ducks = 1
        db_channel.spawn_weight_armored_ducks = 2
        db_channel.spawn_weight_golden_ducks = 5
        db_channel.spawn_weight_plastic_ducks = 2
        db_channel.spawn_weight_kamikaze_ducks = 1

        db_channel.ducks_time_to_live = 960
        db_channel.super_ducks_min_life = 3
        db_channel.super_ducks_max_life = 9

        await db_channel.save()

        await ctx.send(_("Casual mode settings have been applied to this channel.", ))

    # Guild settings #

    @settings.command()
    async def prefix(self, ctx: MyContext, new_prefix: Optional[str] = None):
        """
        Change/view the server prefix.

        Note that some prefixes are global and can't be edited.
        """
        db_guild = await get_from_db(ctx.guild)
        _ = await ctx.get_translate_function()

        if new_prefix:
            db_guild.prefix = new_prefix

            await db_guild.save()

        if db_guild.prefix:
            await ctx.send(_("The server prefix is set to `{prefix}`.",
                             prefix=escape_mentions(escape_markdown(db_guild.prefix))
                             ))
        else:
            await ctx.send(_("There is no specific prefix set for this guild."))

    @settings.command()
    async def language(self, ctx: MyContext, language_code: Optional[str] = None):
        """
        Change/view the server language.

        Specify the server language as a 2/5 letters code. For example, if you live in France, you'd use fr or fr_FR.
        In Québec, you could use fr_QC.
        """
        db_guild = await get_from_db(ctx.guild)
        if language_code:
            try:
                locale_data = Locale.parse(language_code)
            except babel.UnknownLocaleError:
                _ = await ctx.get_translate_function()
                # Send it twice, in english and the original language.
                await ctx.send(f"❌ Unknown locale. If you wish to go back to the default, english language, use `{ctx.prefix}{ctx.command.qualified_name} en`")
                await ctx.send(_("❌ Unknown locale. If you wish to go back to the default, english language, use `{ctx.prefix}{ctx.command.qualified_name} en`", ctx=ctx))
                return

            db_guild.language = language_code
            await db_guild.save()

        _ = await ctx.get_translate_function()  # Deferered for the new language
        if db_guild.language:
            locale_data = Locale.parse(db_guild.language)
            await ctx.send(_("This server language is set to `{language}` [{language_name}].",
                             language=escape_mentions(db_guild.language),
                             language_name=locale_data.get_display_name()
                             ))

            # Do not translate
            await ctx.send(f"If you wish to go back to the default, english language, use `{ctx.prefix}{ctx.command.qualified_name} en`")
        else:
            await ctx.send(_("There is no specific language set for this guild."))

    # Channel settings #

    @settings.command()
    async def use_webhooks(self, ctx: MyContext, value: Optional[bool] = None):
        """
        Specify wether the bot should use webhooks to communicate in this channel.

        Webhooks allow for custom avatars and usernames. However, there is a Discord limit of 10 webhooks per channel.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.use_webhooks = value
            await db_channel.save()

        if db_channel.use_webhooks:
            await ctx.send(_("Webhooks are used in this channel."))
        else:
            await ctx.send(_("Webhooks are not used in this channel."))

    @settings.command()
    async def add_webhook(self, ctx: MyContext):
        """
        Add a new webhook to the channel, to get better rate limits handling. Remember the 10 webhooks/channel limit.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if not db_channel.use_webhooks:
            await ctx.send(_("Webhooks are not used in this channel. Please enable them first. You can use `{command}` to do it.",
                             command=f"{ctx.prefix}settings use_webhooks True"))
            return

        webhooks_count = len(db_channel.webhook_urls)

        webhook = await create_and_save_webhook(ctx.bot, ctx.channel, force=True)
        if webhook:
            await ctx.send(_("Your webhook was created. The bot now uses {n} webhook(s) to spawn ducks.", n=webhooks_count + 1))
        else:
            await ctx.send(_("I couldn't create a webhook. Double-check my permissions and try again."))

    @settings.command()
    async def use_emojis(self, ctx: MyContext, value: bool = None):
        """
        Allow ducks to use emojis when they spawn.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.use_emojis = value
            await db_channel.save()

        if db_channel.use_emojis:
            await ctx.send(_("That channel uses emojis to spawn ducks."))
        else:
            await ctx.send(_("That channel uses pure-text ducks. How does it feels to live in the IRC world ?"))

    @settings.command()
    async def enabled(self, ctx: MyContext, value: bool = None):
        """
        Allow ducks to spawn.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.enabled = value
            await db_channel.save()

        if db_channel.enabled:
            await ctx.send(_("Ducks will spawn on {channel.mention}", channel=ctx.channel))
        else:
            await ctx.send(_("Ducks won't spawn on {channel.mention}", channel=ctx.channel))

    @settings.command()
    async def tax_on_user_send(self, ctx: MyContext, value: int = None):
        """
        Change the tax taken from users when they *send* some experience to another player.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.tax_on_user_send = value
            await db_channel.save()

        if db_channel.tax_on_user_send:
            await ctx.send(_("On {channel.mention}, players will pay {tax}% of tax to the bot when they share some experience.",
                             channel=ctx.channel,
                             tax=db_channel.tax_on_user_send))
        else:
            await ctx.send(_("Players won't have to pay any tax when sending experience to others in {channel.mention}", channel=ctx.channel))

    @settings.command()
    async def mentions_when_killed(self, ctx: MyContext, value: bool = None):
        """
        Control if users might be pinged when they get killed. It's recommanded to set this to False on big servers.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.mentions_when_killed = value
            await db_channel.save()

        if db_channel.mentions_when_killed:
            await ctx.send(_("On {channel.mention}, players will be mentionned when they get killed.",
                             channel=ctx.channel))
        else:
            await ctx.send(_("Players won't get mentions when they get killed in {channel.mention}", channel=ctx.channel))

    @settings.command()
    async def show_duck_lives(self, ctx: MyContext, value: bool = None):
        """
        When killing super ducks and the like, show how many lives the ducks have left.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.show_duck_lives = value
            await db_channel.save()

        if db_channel.show_duck_lives:
            await ctx.send(_("On {channel.mention}, players will see the lives count of super ducks.",
                             channel=ctx.channel))
        else:
            await ctx.send(_("Players won't see lives of super ducks on {channel.mention}", channel=ctx.channel))

    @settings.command()
    async def kill_on_miss_chance(self, ctx: MyContext, value: int = None):
        """
        Set how likely it is that a hunter will kill someone when missing a shot.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.kill_on_miss_chance = value
            await db_channel.save()

        if db_channel.kill_on_miss_chance:
            await ctx.send(_("On {channel.mention}, players will kill people {pct}% of the time when missing a shot.",
                             channel=ctx.channel,
                             pct=db_channel.kill_on_miss_chance))
        else:
            await ctx.send(_("Players won't kill people randomly when missing shots on {channel.mention}. "
                             "They can still kill people volontarly.", channel=ctx.channel))

    @settings.command()
    async def duck_frighten_chance(self, ctx: MyContext, value: int = None):
        """
        Set how likely it is that a hunter will frighten a duck when shooting.
        Remember, the silencer sets this to 0% for a hunter.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            db_channel.duck_frighten_chance = value
            await db_channel.save()

        if db_channel.duck_frighten_chance:
            await ctx.send(_("On {channel.mention}, players will frighten ducks {pct}% of the time when shooting.",
                             channel=ctx.channel,
                             pct=db_channel.duck_frighten_chance))
        else:
            await ctx.send(_("Players won't frighten ducks, making the silencer useless on {channel.mention}.", channel=ctx.channel))

    @settings.command()
    async def clover_min_experience(self, ctx: MyContext, value: int = None):
        """
        Set the minimum experience a clover will give. Might be negative for funsies :)
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < db_channel.base_duck_exp:
                await ctx.send(_("⚠️ In some cases, users may get NEGATIVE experience when killing ducks with that low of a experience.",
                                 channel=ctx.channel,
                                 ))
            elif value > db_channel.clover_max_experience:
                await ctx.send(_("❌️ You need to provide a lower value than the one set in `clover_max_experience` !",
                                 channel=ctx.channel,
                                 ))
                return

            db_channel.clover_min_experience = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, when a hunter buy a clover, the minimum experience given per duck kill will be of {value}.",
                         channel=ctx.channel,
                         value=db_channel.clover_min_experience))

    @settings.command()
    async def clover_max_experience(self, ctx: MyContext, value: int = None):
        """
        Set the maximum experience a clover will give. Might be negative for funsies :)
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < db_channel.clover_min_experience:
                await ctx.send(_("❌️ You need to provide a higher value than the one set in `clover_min_experience` !",
                                 channel=ctx.channel,
                                 ))
                return

            db_channel.clover_max_experience = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, when a hunter buy a clover, the maximum experience given per duck kill will be of {value}.",
                         channel=ctx.channel,
                         value=db_channel.clover_max_experience))

    @settings.command()
    async def base_duck_exp(self, ctx: MyContext, value: int = None):
        """
        Set the normal amount of experience a duck will give when killed.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < 0:
                await ctx.send(_("⚠️ Giving negative experience when hunter kills ducks might be a bad idea.",
                                 channel=ctx.channel,
                                 ))
            db_channel.base_duck_exp = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, when a hunter kills a duck, the experience given will be of {value}.",
                         channel=ctx.channel,
                         value=db_channel.base_duck_exp))

    @settings.command()
    async def per_life_exp(self, ctx: MyContext, value: int = None):
        """
        Set the additional amount of experience given for every life of a super duck.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < 0:
                await ctx.send(_("⚠️ Giving negative experience when hunter kills ducks might be a bad idea.",
                                 channel=ctx.channel,
                                 ))
            db_channel.per_life_exp = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, when a hunter kills a duck, the experience given will be of {value}.",
                         channel=ctx.channel,
                         value=db_channel.per_life_exp))

    @settings.command()
    async def ducks_per_day(self, ctx: MyContext, value: int = None):
        """
        Set the amount of ducks that will spawn every day
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        maximum_value = max_ducks_per_day(ctx.guild.member_count)

        if value:
            if value <= 0:
                await ctx.send(_("❌️ To disable a channel, use `{prefix}settings enabled False`.",
                                 prefix=ctx.prefix,
                                 ))
                return
            elif value > maximum_value:
                await ctx.send(_("⚠️️ You cannot set that higher than {maximum_value}. "
                                 "The number of ducks per day is limited to ensure resources are used fairly. "
                                 "If you donated towards bot, contact Eyesofcreeper#0001 to lift the limit. "
                                 "If not, consider donating to support me.",
                                 maximum_value=maximum_value,
                                 ))
                value = maximum_value
            db_channel.ducks_per_day = value
            await db_channel.save()

        # TODO : Replan that channel.

        await ctx.send(_("On {channel.mention}, {value} ducks will spawn every day.",
                         channel=ctx.channel,
                         value=db_channel.ducks_per_day))

    @settings.command()
    async def weights(self, ctx: MyContext, duck_type: str, value: int = None):
        """
        Set a duck probably to spawn to a certain weight. The higher the weight, the more probability for it to spawn.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        allowed_ducks_types = ducks.DUCKS_CATEGORIES

        if duck_type not in allowed_ducks_types:
            await ctx.send(_("❌ I don't know what type of duck you are talking about. Choose one in {allowed_ducks_types}.",
                             channel=ctx.channel,
                             allowed_ducks_types=babel.lists.format_list(allowed_ducks_types, locale=await ctx.get_language_code())
                             ))
            return

        attr = f"spawn_weight_{duck_type}_ducks"
        if value:
            if value < 0:
                await ctx.send(_("❌ You cannot set a negative weight.", ))
                return
            else:
                setattr(db_channel, attr, value)
                await db_channel.save()

        await ctx.send(_("❌ Weight for the {duck_type} is set to {value} in {channel.mention}.",
                         channel=ctx.channel,
                         duck_type=duck_type,
                         value=getattr(db_channel, attr)
                         ))

    @settings.command()
    async def ducks_time_to_live(self, ctx: MyContext, value: int = None):
        """
        Set for how many seconds a duck will stay on the channel before leaving
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < 30:
                await ctx.send(_("❌️ Ducks need to settle for a while in the pond before leaving.",
                                 channel=ctx.channel,
                                 ))
                return
            elif value > 3600:
                await ctx.send(_("❌️ Ducks will get bored long before that.",
                                 channel=ctx.channel,
                                 ))
                return
            db_channel.ducks_time_to_live = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, ducks will stay for {value} seconds.",
                         channel=ctx.channel,
                         value=babel.numbers.format_decimal(db_channel.ducks_time_to_live, locale=await ctx.get_language_code())))

    @settings.command()
    async def super_ducks_min_life(self, ctx: MyContext, value: int = None):
        """
        Set the minimum lives of a super duck
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < 1:
                await ctx.send(_("❌️ Super ducks will live !",
                                 channel=ctx.channel,
                                 ))
                return
            elif value > db_channel.super_ducks_max_life:
                await ctx.send(_("❌️ You need to provide a lower value than the one set in `super_ducks_max_life` !",
                                 channel=ctx.channel,
                                 ))
                return

            db_channel.super_ducks_min_life = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, super ducks will get a minimum of {value} lives.",
                         channel=ctx.channel,
                         value=db_channel.super_ducks_min_life))

    @settings.command()
    async def super_ducks_max_life(self, ctx: MyContext, value: int = None):
        """
        Set the maximum lives of a super duck
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()

        if value:
            if value < 1:
                await ctx.send(_("❌️ Super ducks will live !",
                                 channel=ctx.channel,
                                 ))
                return
            elif value < db_channel.super_ducks_min_life:
                await ctx.send(_("❌️ You need to provide a higher value than the one set in `super_ducks_min_life` !",
                                 channel=ctx.channel,
                                 ))
                return

            db_channel.super_ducks_max_life = value
            await db_channel.save()

        await ctx.send(_("On {channel.mention}, super ducks will get a minimum of {value} lives.",
                         channel=ctx.channel,
                         value=db_channel.super_ducks_max_life))


setup = SettingsCommands.setup
