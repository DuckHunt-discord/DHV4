from discord.ext import commands, menus
import discord


class HelpGroupPaginator(menus.ListPageSource):
    def __init__(self, help_: 'EmbedHelpCommand', group, entries):
        super().__init__(entries, per_page=7)
        self.group = group
        self.help = help_

    async def format_page(self, menu, entries):
        _ = await self.help.context.get_translate_function()

        embed = discord.Embed(title=self.group.qualified_name, colour=self.help.COLOUR)
        embed.url = self.help.context.bot.config['website_url'] + f"commands/{self.group.qualified_name.replace(' ', '/')}"

        if self.group.help:
            embed.description = _(self.group.help)

        for command in entries:
            value = '...'
            if command.brief:
                value = _(command.brief)
            elif command.help:
                value = _(command.help).split('\n', 1)[0]
            embed.add_field(name=self.help.get_command_signature(command), value=value, inline=False)

        embed.set_footer(text=self.help.get_ending_note(_))

        # you can format the embed however you'd like
        return embed


class EmbedHelpCommand(commands.HelpCommand):
    # Set the embed colour here
    COLOUR = discord.Colour.blurple()

    def get_ending_note(self, _):
        return _('Use {prefix}{help} [command] for more info on a command.', prefix="dh!", help=self.invoked_with)

    def get_command_signature(self, command):
        return '{0.qualified_name} {0.signature}'.format(command)

    async def send_bot_help(self, mapping):
        _ = await self.context.get_translate_function()

        embed = discord.Embed(title='Bot Commands', colour=self.COLOUR)
        embed.url = self.context.bot.config['website_url'] + "commands"
        description = _(self.context.bot.description)
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            name = _('No Category') if cog is None else cog.qualified_name
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                value = '\u2002'.join(c.name for c in commands)
                if cog and cog.description:
                    value = '{0}\n{1}'.format(_(cog.description), _(value))

                embed.add_field(name=name, value=value)

        embed.set_footer(text=self.get_ending_note(_))
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        _ = await self.context.get_translate_function()

        embed = discord.Embed(title=_('{cog_name} Commands', cog_name=cog.qualified_name), colour=self.COLOUR)
        embed.url = self.context.bot.config['website_url'] + "commands"

        if cog.description:
            embed.description = _(cog.description)

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            value = '...'
            if command.brief:
                value = _(command.brief)
            elif command.help:
                value = _(command.help).split('\n', 1)[0]

            embed.add_field(name=self.get_command_signature(command), value=value, inline=False)

        embed.set_footer(text=self.get_ending_note(_))
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        entries = await self.filter_commands(group.commands, sort=True)
        menu = menus.MenuPages(HelpGroupPaginator(self, group, entries))
        await menu.start(self.context)

    async def send_command_help(self, command):
        _ = await self.context.get_translate_function()

        embed = discord.Embed(title=command.qualified_name, colour=self.COLOUR)
        embed.url = self.context.bot.config['website_url'] + f"commands/{command.qualified_name.replace(' ', '/')}"

        if command.help:
            embed.description = _(command.help)

        embed.set_footer(text=self.get_ending_note(_))
        await self.get_destination().send(embed=embed)
