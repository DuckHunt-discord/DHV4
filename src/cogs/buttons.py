import discord
from discord import ButtonStyle
from discord.ext import commands

from utils import checks
from utils.bot_class import MyBot
from utils.checks import needs_access_level
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import AccessLevel

from utils.views import init_all_persistant_command_views, CommandView, nitro_prank, View, CommandButton

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class GamepadView(View):
    def __init__(self, bot: MyBot, _=lambda s: s):
        super().__init__(bot)

        bang_command = bot.get_command("bang")
        hug_command = bot.get_command("hug")
        reload_command = bot.get_command("reload")
        shop_bul_command = bot.get_command("shop bullet")
        shop_mag_command = bot.get_command("shop magazine")
        shop_clover_command = bot.get_command("shop clover")

        self.add_item(CommandButton(bot, bang_command, [], {'target': None}, custom_id="gamepad_bang", row=0, label=_('🔫 Bang'), style=discord.ButtonStyle.red))
        self.add_item(CommandButton(bot, hug_command, [], {'target': None}, custom_id="gamepad_hug", row=0, label=_('🤗 Hug'), style=discord.ButtonStyle.green))
        self.add_item(CommandButton(bot, reload_command, [], {}, custom_id="gamepad_reload", row=1, label=_('♻️ Reload'), style=discord.ButtonStyle.blurple))
        self.add_item(CommandButton(bot, shop_mag_command, [], {}, custom_id="gamepad_magazine", row=2, label=_('Buy a magazine'), style=discord.ButtonStyle.blurple))
        self.add_item(CommandButton(bot, shop_bul_command, [], {}, custom_id="gamepad_bullet", row=2, label=_('Buy a bullet'), style=discord.ButtonStyle.blurple))
        self.add_item(CommandButton(bot, shop_clover_command, [], {}, custom_id="gamepad_clover", row=2, label=_('🍀 Buy a clover'), style=discord.ButtonStyle.blurple))


class Buttons(Cog):
    hidden = True

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.persistent_views_added = False

    @Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            # Register the persistent view for listening here.
            # Note that this does not send the view to any message.
            # In order to do this you need to first send a message with the View, which is shown below.
            # If you have the message_id you can also pass it as a keyword argument, but for this example
            # we don't have one.
            self.bot.logger.debug("Loading persistant views...")
            await init_all_persistant_command_views(self.bot)
            self.bot.add_view(GamepadView(self.bot))
            self.bot.logger.info("Command persistant views loaded")

            self.persistent_views_added = True

    @commands.command(hidden=True)
    @needs_access_level(AccessLevel.BOT_MODERATOR)
    async def create_command_button(self, ctx: MyContext, *, command_name: str):
        """
        Create a Command view for a given command.
        """
        await CommandView(self.bot, command_to_be_ran=command_name, label=command_name, style=ButtonStyle.blurple).send(ctx)

    @commands.command(hidden=True)
    @needs_access_level(AccessLevel.BOT_OWNER)
    async def get_nitro_button(self, ctx: MyContext):
        await ctx.message.delete(delay=0)
        await nitro_prank(ctx)

    @commands.command(hidden=True)
    @checks.channel_enabled()
    @needs_access_level(AccessLevel.MODERATOR)
    async def gamepad(self, ctx: MyContext):
        """
        Create a GamePadView to allow playing the game with buttons.
        """
        await GamepadView(self.bot, await ctx.get_translate_function()).send(ctx)


setup = Buttons.setup
