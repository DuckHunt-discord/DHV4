import time
import typing

import discord
from discord.ext import commands

from utils.bot_class import MyBot
from utils.cog_class import Cog
from utils.ctx_class import MyContext

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class CounterView(discord.ui.View):

    @discord.ui.button(label='0', style=discord.ButtonStyle.red, custom_id='count_button')
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
        m = await ctx.send(content="Click me to count!", view=CounterView(timeout=None))
        # self.bot.add_view(CounterView(timeout=None), message_id=m.id)


setup = Buttons.setup
