import random

import discord
from discord.ext import commands

from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible
from utils.models import get_from_db, DiscordChannel

DUCKS_IMAGES = {
    "emoji": "https://discordapp.com/assets/5e623785155f790f48901eeb4e5022c9.svg",
    "glare": "https://cdn.discordapp.com/emojis/436542355257163777.png",
    "eyebrows": "https://cdn.discordapp.com/emojis/436542355504627712.png",
}

WEBHOOKS_PARAMETERS = {
    "normal": [{
        "username": "A duck",
        "avatar_url": DUCKS_IMAGES["emoji"],
    }, {
        "username": "Mr. Duck",
        "avatar_url": DUCKS_IMAGES["emoji"],
    }, {
        "username": "#DucksDontSuck",
        "avatar_url": DUCKS_IMAGES["emoji"],
    }, {
        "username": "FreshOuttaThePond",
        "avatar_url": DUCKS_IMAGES["emoji"],
    }],
    "super": [{
        "username": "Big Duck",
        "avatar_url": DUCKS_IMAGES["glare"],
    }, {
        "username": "Mr. Big Duck",
        "avatar_url": DUCKS_IMAGES["emoji"],
    }]
}


async def send_webhook_message(bot: MyBot, channel: discord.TextChannel, this_webhook_parameters, message):
    webhook = await get_webhook_if_possible(bot, channel)

    if webhook:
        await webhook.send(message, **this_webhook_parameters)
    else:
        await channel.send(message)


from utils.cog_class import Cog
from utils.ctx_class import MyContext


class DucksSpawningCommands(Cog):
    @commands.group(aliases=["spawn", "spawnduck"])
    async def coin(self, ctx: MyContext):
        """
        Spawns a duck
        """
        if not ctx.invoked_subcommand:
            await send_webhook_message(ctx.bot, ctx.channel, random.choice(WEBHOOKS_PARAMETERS['normal']), "Coin")

    @coin.command()
    async def super(self, ctx: MyContext, lives: int = 0):
        """
        Spawns a super duck
        """
        await send_webhook_message(ctx.bot, ctx.channel, random.choice(WEBHOOKS_PARAMETERS['normal']), f"Mega coin [{lives} lives]")

setup = DucksSpawningCommands.setup
