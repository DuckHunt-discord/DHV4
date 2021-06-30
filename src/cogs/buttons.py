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

from discord.ext import commands
import discord


class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Green', style=discord.ButtonStyle.green, custom_id='test_persistent_view:green')
    async def green(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message('This is green.', ephemeral=True)

    @discord.ui.button(label='Red', style=discord.ButtonStyle.red, custom_id='test_persistent_view:red')
    async def red(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message('This is red.', ephemeral=True)

    @discord.ui.button(label='Grey', style=discord.ButtonStyle.grey, custom_id='test_persistent_view:grey')
    async def grey(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message('This is grey.', ephemeral=True)


class Buttons(Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            # Register the persistent view for listening here.
            # Note that this does not send the view to any message.
            # In order to do this you need to first send a message with the View, which is shown below.
            # If you have the message_id you can also pass it as a keyword argument, but for this example
            # we don't have one.
            self.bot.add_view(PersistentView())
            self.persistent_views_added = True

    @commands.command()
    async def prepare_view(self, ctx: MyContext):
        """Starts a persistent view."""
        # In order for a persistent view to be listened to, it needs to be sent to an actual message.
        # Call this method once just to store it somewhere.
        # In a more complicated program you might fetch the message_id from a database for use later.
        # However this is outside of the scope of this simple example.
        await ctx.send("What's your favourite colour?", view=PersistentView())
