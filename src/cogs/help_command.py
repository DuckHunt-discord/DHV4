import itertools
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import CommandError

from utils.bot_class import MyBot
from utils.cog_class import Cog
from utils.ctx_class import MyContext


class ButtonsHelpCommand(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        view = BotHelpView(bot, ctx)

        await ctx.send("The help is currently being coded, please wait :)", view=await view.initialize())


async def filter_commands(commands, *, context=None, sort=False, key=None, show_hidden=False):
    if sort and key is None:
        key = lambda c: c.name

    iterator = commands if show_hidden else filter(lambda c: not c.hidden, commands)

    if context is None:
        # if we do not need to verify the checks then we can just
        # run it straight through normally without using await.
        return sorted(iterator, key=key) if sort else list(iterator)

    # if we're here then we need to check every command if it can run
    async def predicate(cmd):
        try:
            return await cmd.can_run(context)
        except CommandError:
            return False

    ret = []
    for cmd in iterator:
        valid = await predicate(cmd)
        if valid:
            ret.append(cmd)

    if sort:
        ret.sort(key=key)
    return ret


def get_category(command):
    cog = command.cog
    return cog.qualified_name if cog is not None else "\u200b"


def get_cog(command):
    cog = command.cog
    return cog if cog is not None else None


class BotHelpButton(discord.ui.Button):
    def __init__(self, cog: Cog):
        custom_id = f"bot_help_cog:{cog.name}"
        super().__init__(style=discord.ButtonStyle.green, label=cog.name, custom_id=custom_id)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'You clicked on {self.cog.name}.', ephemeral=True)


class BotHelpView(discord.ui.View):
    def __init__(self, bot: MyBot, ctx: Optional[MyContext] = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    async def initialize(self):
        filtered = await filter_commands(self.bot.commands, context=self.ctx, sort=True, key=get_category)
        commands_by_cog = itertools.groupby(filtered, key=get_cog)

        for cog, commands in commands_by_cog:
            self.add_item(BotHelpButton(cog))

        return self


class HelpCog(Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.persistent_views_added = False
        self.old_help_command = None

    async def on_ready(self):
        if not self.persistent_views_added:
            # Register the persistent view for listening here.
            # Note that this does not send the view to any message.
            # In order to do this you need to first send a message with the View, which is shown below.
            # If you have the message_id you can also pass it as a keyword argument, but for this example
            # we don't have one.
            self.bot.add_view(await BotHelpView(self.bot).initialize())
            self.persistent_views_added = True

    def cog_unload(self):
        self.bot.logger.debug("Restoring previous help command...")
        self.bot.help_command = self.old_help_command
        self.bot.logger.debug("Help command restored...")

    @classmethod
    def setup(cls, bot: MyBot):
        cog = cls(bot)
        bot.add_cog(cog)
        bot.logger.debug("Replacing previous help command...")
        cog.old_help_command = bot.help_command
        bot.help_command = ButtonsHelpCommand()
        bot.logger.debug("Help command replaced...")

        return cog


setup = HelpCog.setup
