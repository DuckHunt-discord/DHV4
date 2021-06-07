import time

import discord
from discord.ext import commands

from utils.cog_class import Cog
from utils.ctx_class import MyContext

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class CounterView(discord.ui.View):
    @discord.ui.button(label='0', style=discord.ButtonStyle.red)
    async def count(self, button: discord.ui.Button, interaction: discord.Interaction):
        number = int(button.label)
        if number + 1 >= 5:
            button.style = discord.ButtonStyle.green
        button.label = str(number + 1)
        await interaction.message.edit(view=self)


class Buttons(Cog):
    @commands.command()
    async def count(self, ctx: MyContext):
        """
        Click on the button to count.
        """
        await ctx.send(content="Click me to count!", view=CounterView())


setup = Buttons.setup
