import datetime
import random
from typing import List

import discord
from discord.ext import commands, tasks

from cogs.inventory_commands import INV_COMMON_ITEMS
from utils.cog_class import Cog
from utils.models import get_enabled_channels, DiscordChannel, Player, DiscordUser


class DuckBoss(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop.start()

    def cog_unload(self):
        self.background_loop.cancel()

    async def create_boss_embed(self):
        embed = discord.Embed(
            color=discord.Color.green(),
            title="A boss spawned!",
            description="React with 🔫 to kill it.")

        embed.set_image(url="https://media.discordapp.net/attachments/734810933091762188/779515302382796870/boss.png")


        return embed

    @tasks.loop(minutes=1)
    async def background_loop(self):
        channel = self.bot.get_channel(self.config()['boss_channel_id'])
        latest_message = await channel.fetch_message(channel.last_message_id)

        if latest_message.author.id != self.bot.user.id:
            boss_message = None
        elif len(latest_message.embeds) == 0:
            boss_message = None
        else:
            latest_message_embed = latest_message.embeds[0]
            if latest_message_embed.color == discord.Color.green():
                boss_message = latest_message
            else:
                boss_message = None

        if boss_message:
            reaction: discord.Reaction = boss_message.reactions[0]
            bangs = reaction.count

            if bangs >= self.config()['required_bangs']:
                # Kill the boss
                users = await reaction.users().flatten()
                ids = [u.id for u in users]
                discordusers: List[DiscordUser] = await DiscordUser.filter(discord_id__in=ids).only('inventory', 'discord_id').all()

                for discorduser in discordusers:
                    discorduser.inventory.append(INV_COMMON_ITEMS['foie_gras'])
                    await discorduser.save(update_fields=['inventory'])
                await channel.send(f"The boss has been defeated! Congratulations to the {bangs} players who participed!")

        else:
            if random.randint(1, 1440) == 1:
                boss_message = await channel.send(embed=await self.create_boss_embed(),)
                await boss_message.add_reaction("🔫")

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

setup = DuckBoss.setup
