import itertools
from typing import Optional, Union

import discord
from discord.ext import commands
from discord.ext.commands import CommandError, Command, Group

from utils.bot_class import MyBot
from utils.cog_class import Cog
from utils.ctx_class import MyContext


class ButtonsHelp:
    def __init__(self, *args, **kwargs):
        self.context: MyContext = None
        super().__init__(*args, **kwargs)

    def get_command_signature(self, command):
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'

    @property
    def invoked_with(self):
        try:
            return super().invoked_with
        except AttributeError:
            return "help"

    async def send(self, *args, **kwargs):
        raise RuntimeError('ButtonsHelp subclass must provide a send method.')

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        _ = await ctx.get_translate_function()

        view = await BotHelpView(bot, ctx).initialize()

        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=_("DuckHunt help"),
                              url=self.context.bot.config['website_url'] + "commands")

        embed.description = _("**Welcome to DuckHunt**\n\n"
                              "This is a help command designed to let you find all the commands in the bot.\n"
                              "However, it's *not* the best way to get started with it. I suggest reading the wiki instead, "
                              "here's [a link](https://duckhunt.me/docs).\n"
                              "If you have questions, you can DM the bot, or join the [support server](https://duckhunt.me/support).\n"
                              "Thanks for playing.")

        embed.set_footer(text=_('Use {prefix}{help} [command] for more info on a command.', prefix="dh!", help=self.invoked_with))

        await self.send("<https://duckhunt.me/docs>", embed=embed, view=view)

    async def send_cog_help(self, cog):
        ctx = self.context
        bot = ctx.bot

        _ = await ctx.get_translate_function()

        view = await CogHelpView(bot, cog, ctx).initialize()

        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=_("{cog} help", cog=cog.qualified_name),
                              url=self.context.bot.config['website_url'] + "commands")

        if cog.description:
            embed.description = _(cog.description)

        filtered = await filter_commands(cog.get_commands(), context=ctx, sort=True)

        for command in filtered:
            value = '...'
            if command.brief:
                value = _(command.brief)
            elif command.help:
                value = _(command.help).split('\n', 1)[0]

            embed.add_field(name=self.get_command_signature(command), value=value, inline=False)

        embed.set_footer(text=_('Use {prefix}{help} [command] for more info on a command.', prefix="dh!", help=self.invoked_with))

        await self.send("<https://duckhunt.me/docs>", embed=embed, view=view)

    async def send_group_help(self, group):
        ctx = self.context
        bot = ctx.bot

        _ = await ctx.get_translate_function()

        view = await CogHelpView(bot, group, ctx).initialize()

        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=_("{cog} help", cog=group.qualified_name),
                              url=self.context.bot.config['website_url'] + f"commands/{group.qualified_name.replace(' ', '/')}")

        if group.description:
            embed.description = _(group.description)

        filtered = await filter_commands(group.commands, context=ctx, sort=True)

        for command in filtered:
            value = '...'
            if command.brief:
                value = _(command.brief)
            elif command.help:
                value = _(command.help).split('\n', 1)[0]

            embed.add_field(name=self.get_command_signature(command), value=value, inline=False)

        embed.set_footer(text=_('Use {prefix}{help} [command] for more info on a command.', prefix="dh!", help=self.invoked_with))

        await self.send("<https://duckhunt.me/docs>", embed=embed, view=view)

    async def send_command_help(self, command):
        _ = await self.context.get_translate_function()

        embed = discord.Embed(title=_("{cog} help", cog=command.qualified_name), colour=discord.Colour.blurple(), )
        embed.url = self.context.bot.config['website_url'] + f"commands/{command.qualified_name.replace(' ', '/')}"

        if command.help:
            embed.description = _(command.help)

        embed.set_footer(text=_('Use {prefix}{help} [command] for more info on a command.', prefix="dh!", help=self.invoked_with))

        await self.send(embed=embed)


class ButtonsHelpCommand(ButtonsHelp, commands.MinimalHelpCommand):
    async def send(self, *args, **kwargs):
        await self.get_destination().send(*args, **kwargs)


class ButtonsHelpInteraction(ButtonsHelp):
    def __init__(self, context: MyContext, interaction: discord.Interaction, **options):
        super().__init__(**options)
        self.interaction = interaction
        self.context = context

    async def send(self, *args, **kwargs):
        await self.interaction.response.send_message(*args, **kwargs, ephemeral=True)

    @property
    def invoked_with(self):
        ctx = self.context
        if ctx is None or ctx.command is None:
            return "help"

        return ctx.invoked_with


async def filter_commands(commands, *, context=None, sort=False, key=None):
    if sort and key is None:
        def newkey(c):
            return c.name
    elif sort:
        def newkey(c):
            return key(c)
    else:
        def newkey(c):
            return c

    iterator = commands if not context else filter(lambda c: not c.hidden, commands)

    if context is None:
        # if we do not need to verify the checks then we can just
        # run it straight through normally without using await.
        return sorted(iterator, key=newkey) if sort else list(iterator)

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
        ret.sort(key=newkey)
    return ret


def get_category(command):
    cog = command.cog
    return cog.name if cog is not None else "\u200b"


def get_group_name(command):
    group = command.parent
    return group.name if group is not None else "\u200b"


def get_cog(command):
    cog = command.cog
    return cog if cog is not None else None


def get_group(command):
    group = command.parent
    return group if group is not None else None


class CogHelpButton(discord.ui.Button):
    """
    Buttons to direct user to a cog help.
    """

    def __init__(self, context: MyContext, cog: Cog):
        custom_id = f"bot_help_cog:{type(cog).__name__}"
        super().__init__(style=getattr(discord.ButtonStyle, getattr(cog, 'help_color', 'grey')), label=cog.name, custom_id=custom_id)
        self.cog = cog
        self.context = context

    async def callback(self, interaction: discord.Interaction):
        await ButtonsHelpInteraction(self.context, interaction).send_cog_help(self.cog)


class BotHelpView(discord.ui.View):
    """
    Show buttons for all the cogs in a bot.
    """

    def __init__(self, bot: MyBot, ctx: Optional[MyContext] = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    async def initialize(self):
        filtered = await filter_commands(self.bot.commands, context=self.ctx, sort=True, key=get_category)
        commands_by_cog = list(itertools.groupby(filtered, key=get_cog))
        commands_by_cog.sort(key=lambda kv: (getattr(kv[0], 'help_priority', 10), kv[0].name) if kv[0] else (100, kv[0]))

        for cog, commands in commands_by_cog:
            if cog is not None:
                if not getattr(cog, 'hidden', False):
                    self.add_item(CogHelpButton(self.ctx, cog))
            else:
                # Don't show the help command in the help command, ffs
                pass

        return self


class GroupHelpButton(discord.ui.Button):
    """
    Buttons to direct user to a group help
    """

    def __init__(self, context: MyContext, group: Group):
        group_id = group.qualified_name.replace(' ', '_')
        custom_id = f"bot_help_group:{group_id}"
        super().__init__(style=discord.ButtonStyle.green, label=f"{group.name} ({len(group.commands)} subcommands)", custom_id=custom_id)
        self.group = group
        self.context = context

    async def callback(self, interaction: discord.Interaction):
        await ButtonsHelpInteraction(self.context, interaction).send_group_help(self.group)


class CommandHelpButton(discord.ui.Button):
    """
    Buttons to direct user to a command help
    """

    def __init__(self, context: MyContext, command: Command):
        command_id = command.qualified_name.replace(' ', '_')
        custom_id = f"bot_help_command:{command_id}"
        super().__init__(style=discord.ButtonStyle.green, label=command.name, custom_id=custom_id)
        self.command = command
        self.context = context

    async def callback(self, interaction: discord.Interaction):
        await ButtonsHelpInteraction(self.context, interaction).send_command_help(self.command)


class CogHelpView(discord.ui.View):
    """
    Show buttons for all the commands and groups in a cog or a group.
    """

    def __init__(self, bot: MyBot, cog: Union[Cog, Group], ctx: Optional[MyContext] = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.ctx = ctx

    async def initialize(self):
        if self.ctx:
            _ = await self.ctx.get_translate_function()
        else:
            def _(s):
                return s

        items_shown = 0
        if isinstance(self.cog, Cog):
            commands = self.cog.get_commands()
        else:
            commands = self.cog.commands

        self.ctx.logger.debug(f"Displaying {len(commands)} subcommands")

        filtered = await filter_commands(commands, context=self.ctx, sort=True, key=get_group_name)

        for command in filtered:
            items_shown += 1
            if items_shown >= 5 * 3:
                self.add_item(discord.ui.Button(style=discord.ButtonStyle.blurple,
                                                label=_("... More available online"),
                                                url=self.bot.config['website_url'] + f"commands/{self.cog.qualified_name.replace(' ', '/')}"))
                break
            if isinstance(command, Group):
                self.add_item(GroupHelpButton(self.ctx, command))
            else:
                self.add_item(CommandHelpButton(self.ctx, command))

        return self


class HelpCog(Cog):
    hidden = True

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

            for cog in self.bot.cogs:
                self.bot.add_view(await CogHelpView(self.bot, cog).initialize())

            for command in self.bot.commands:
                if isinstance(command, Group):
                    self.bot.add_view(await CogHelpView(self.bot, command).initialize())

            self.persistent_views_added = True

    async def cog_unload(self):
        self.bot.logger.debug("Restoring previous help command...")
        self.bot.help_command = self.old_help_command
        self.bot.logger.debug("Help command restored...")

    @classmethod
    async def setup(cls, bot: MyBot):
        cog = cls(bot)
        await bot.add_cog(cog)
        bot.logger.debug("Replacing previous help command...")
        cog.old_help_command = bot.help_command
        bot.help_command = ButtonsHelpCommand()
        bot.logger.debug("Help command replaced...")

        return cog


#setup = HelpCog.setup

async def setup(*args, **kwargs):
    pass
