from discord.ext import commands
import discord


class EmbedHelpCommand(commands.HelpCommand):
    """This is an example of a HelpCommand that utilizes embeds.
    It's pretty basic but it lacks some nuances that people might expect.
    1. It breaks if you have more than 25 cogs or more than 25 subcommands. (Most people don't reach this)
    2. It doesn't DM users. To do this, you have to override `get_destination`. It's simple.
    Other than those two things this is a basic skeleton to get you started. It should
    be simple to modify if you desire some other behaviour.

    To use this, pass it to the bot constructor e.g.:

    bot = commands.Bot(help_command=EmbedHelpCommand())
    """
    # Set the embed colour here
    COLOUR = discord.Colour.blurple()

    def get_ending_note(self, _):
        return _('Use {prefix}{help} [command] for more info on a command.', prefix=self.clean_prefix, help=self.invoked_with)

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
        _ = await self.context.get_translate_function()

        embed = discord.Embed(title=group.qualified_name, colour=self.COLOUR)
        embed.url = self.context.bot.config['website_url'] + f"commands/{group.qualified_name.replace(' ', '/')}"

        if group.help:
            embed.description = _(group.help)

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                value = '...'
                if command.brief:
                    value = _(command.brief)
                elif command.help:
                    value = _(command.help).split('\n', 1)[0]
                embed.add_field(name=self.get_command_signature(command), value=value, inline=False)

        embed.set_footer(text=self.get_ending_note(_))
        await self.get_destination().send(embed=embed)

    # This makes it so it uses the function above
    # Less work for us to do since they're both similar.
    # If you want to make regular command help look different then override it
    send_command_help = send_group_help