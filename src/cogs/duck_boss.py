import datetime
import random
from typing import List

import discord
from babel.dates import format_timedelta
from discord.ext import commands, tasks

from cogs.inventory_commands import INV_COMMON_ITEMS
from utils.cog_class import Cog
from utils.interaction import get_timedelta
from utils.models import get_enabled_channels, DiscordChannel, Player, DiscordUser


class DuckBoss(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop.start()

    def cog_unload(self):
        self.background_loop.cancel()

    async def create_boss_embed(self, bangs=0, boss_message=None):
        boss_life = self.config()['required_bangs']

        new_embed = discord.Embed(
            title=random.choice(["A duck boss is here...", "A wild boss has appeared...", "A boss has spawned...", "KILL THE BOSS !",
                                 "Who wants some foie gras ?", "There is a Duck Boss nearby...", "You cannot sleep when enemies are nearby."]),
            color=discord.Color.green(),
            description="React with 🔫 to kill it.",
        )

        new_embed.set_image(url="https://media.discordapp.net/attachments/795225915248214036/795404123443953705/boss_Calgeka.png")
        new_embed.add_field(name="Health", value=f"{boss_life - bangs}/{boss_life}")
        if boss_message:
            time_delta = datetime.datetime.now() - boss_message.created_at
            new_embed.set_footer(text=f"The boss spawned {format_timedelta(time_delta, locale='en_US')} ago")
        else:
            new_embed.set_footer(text=f"The boss just spawned")

        return new_embed

    @tasks.loop(minutes=1)
    async def background_loop(self):
        channel = self.bot.get_channel(self.config()['boss_channel_id'])
        latest_messages = await channel.history(limit=1).flatten()

        if not latest_messages:
            boss_message = None
        else:
            latest_message = latest_messages[0]

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
            boss_life = self.config()['required_bangs']

            if bangs >= boss_life:
                # Kill the boss
                users = await reaction.users().flatten()
                ids = [u.id for u in users]
                discordusers: List[DiscordUser] = await DiscordUser.filter(discord_id__in=ids).only('inventory', 'discord_id').all()

                for discorduser in discordusers:
                    discorduser.inventory.append(INV_COMMON_ITEMS['foie_gras'])
                    await discorduser.save(update_fields=['inventory'])

                new_embed = discord.Embed(
                    title=random.choice(["The boss was defeated !"]),
                    color=discord.Color.red(),
                    description=f"Thanks to the {bangs} players who helped in this quest. Check your inventories with `d!inv` for these drops.",
                )

                new_embed.set_image(url="https://media.discordapp.net/attachments/734810933091762188/779515302382796870/boss.png")
                new_embed.add_field(name="Health", value=f"0/{boss_life}")

                time_delta = datetime.datetime.now() - boss_message.created_at
                new_embed.set_footer(text=f"The boss lived for {format_timedelta(time_delta, locale='en_US')}.")

                await boss_message.edit(embed=new_embed)
            else:
                new_embed = await self.create_boss_embed(bangs=bangs, boss_message=boss_message)

                await boss_message.edit(embed=new_embed)

        else:
            if random.randint(1, 1440) == 1:
                boss_message = await channel.send(embed=await self.create_boss_embed(),)
                await boss_message.add_reaction("🔫")

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

setup = DuckBoss.setup
