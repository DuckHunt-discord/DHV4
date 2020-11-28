import discord
from discord.ext import commands

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.levels import get_higher_level
from utils.models import Player, get_player


class PrestigeCommands(Cog):
    @commands.group(aliases=["restart"])
    @checks.channel_enabled()
    async def prestige(self, ctx: MyContext):
        """
        Prestige related commands. Reset your adventure for exclusive bonuses.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @prestige.command()
    async def info(self, ctx: MyContext):
        """
        More info about prestige
        """
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        _ = await ctx.get_translate_function()
        higher_level = get_higher_level()
        needed_exp = higher_level["expMin"]
        current_exp = db_hunter.experience
        missing_exp = needed_exp - current_exp
        progression = round(current_exp/needed_exp * 100)

        e = discord.Embed(title=_("Prestige Information"))
        e.color = discord.Color.dark_theme()

        description = _("Prestige is a way for you to restart the DuckHunt adventure, resetting your account (experience, statistics, ...)\n"
                        "In exchange for the reset, you'll get new items to help you progress faster.\n\n")

        if current_exp < needed_exp:
            description += _("Prestige will be unlocked when you reach the maximum level. "
                             "You are at {pct}% there (you need {missing_exp} more experience).",
                             pct=progression, missing_exp=missing_exp)
        else:
            kept_exp = round(-missing_exp/10)
            description += _("Prestige is available for you now ! Go ahead and use `{ctx.prefix}prestige confirm`. "
                             "By using it now, you'll keep {kept_exp} exp.",
                             kept_exp=kept_exp)

        e.description = description

        if db_hunter.prestige > 0:
            e.add_field(name=_("✨ Current prestige level ✨️"), value=_("You have reached level {level}", level=db_hunter.prestige), inline=False)
        else:
            e.add_field(name="⚠️", value=_("**Remember**, using prestige means losing your statistics and most of your experience. "
                                           "However, you'll get the following items to help you"), inline=False)

        e.add_field(name=_("Level 1"), value=_("**Unbreakable sunglasses**: Never buy sunglasses again"))
        e.add_field(name=_("Level 2"), value=_("**Coat colour**: Choose the colour of your coat"))
        e.add_field(name=_("Level 3"), value=_("**Daily command**: Get more experience every day"))
        e.add_field(name=_("Level 4"), value=_("**Icelandic water**: Wet others for longer"))
        e.add_field(name=_("Level 5"), value=_("**Untearable coat**: Buy it for life"))
        e.add_field(name=_("Level 6"), value=_("**Military grade silencer**: Better silencers, make no noise"))
        e.add_field(name=_("Level 7"), value=_("**Permanent licence to kill**: Secret DuckHunt service"))
        e.add_field(name=_("Level 8"), value=_("**Bigger ammo pack**: Load twice as many bullets in your gun"))
        e.add_field(name=_("Level 9"), value=_("**???**: Suggestions are welcome"))

        f = discord.File("assets/Rich_Ducc_Globloxmen.jpg")
        e.set_image(url=f"attachment://Rich_Ducc_Globloxmen.jpg")

        await ctx.send(embed=e, file=f)

    @prestige.command()
    async def confirm(self, ctx: MyContext):
        """Execute the prestige process. Your data **WILL** be deleted."""
        old_db_hunter: Player = await get_player(ctx.author, ctx.channel)

        _ = await ctx.get_translate_function()
        higher_level = get_higher_level()
        needed_exp = higher_level["expMin"]
        current_exp = old_db_hunter.experience
        missing_exp = needed_exp - current_exp
        progression = round(current_exp / needed_exp * 100)
        kept_exp = round(-missing_exp / 10)

        if current_exp < needed_exp:
            await ctx.send(_("❌ You haven't unlocked prestige yet. See `{ctx.prefix}prestige info` to learn more."))
            return False

        async with ctx.typing():
            old_prestige = old_db_hunter.prestige
            new_prestige = old_db_hunter.prestige + 1

            e = discord.Embed(title=_("Prestige {old_prestige} -> {new_prestige}",
                                      old_prestige=old_prestige,
                                      new_prestige=new_prestige))

            e.color = discord.Color.green()

            e.description = _("You used prestige after reaching {pct}% of the required threshold.", pct=progression)
            e.add_field(name=_("✨ New run"), value=_("You'll restart the game with {kept_exp} experience.", kept_exp=kept_exp))

            await old_db_hunter.delete()
            new_db_hunter: Player = await get_player(ctx.author, ctx.channel)
            new_db_hunter.experience = kept_exp
            new_db_hunter.prestige = new_prestige

            level_info = new_db_hunter.level_info()
            new_db_hunter.magazines = level_info["magazines"]
            new_db_hunter.bullets = level_info["bullets"]

            await new_db_hunter.save()

        await ctx.send(embed=e)




setup = PrestigeCommands.setup
