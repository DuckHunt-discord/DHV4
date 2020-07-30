import asyncio
import datetime
import random
from typing import Optional

import discord
from discord.ext import commands

from utils import checks, permissions
from utils.bot_class import MyBot
from utils.human_time import ShortTime
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck

from utils.cog_class import Cog
from utils.ctx_class import MyContext


async def wait_cd(monitored_player, ctx, name, dt):
    _ = await ctx.get_translate_function(user_language=True)
    now = datetime.datetime.utcnow()

    seconds = (dt - now).total_seconds()
    seconds = max(seconds, 1)
    await asyncio.sleep(seconds)
    ctx.logger.debug(f"{monitored_player.name} cooldown for {name} expired, notifying.")
    await ctx.send(_("{monitored_player.mention}, RPG cooldown: **{name}** expired.", name=name, monitored_player=monitored_player))


class Community(Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.epic_rpg_cd_coros = {}

    async def is_in_server(self, message):
        return message.guild and message.guild.id in self.config()["servers"]

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not await self.is_in_server(message):
            return

        if message.author.id == 555955826880413696:
            await self.epic_rpg_cooldowns(message)
            await self.epic_rpg_pings(message)

        if message.content.lower().startswith("rpg"):
            await message.delete(delay=10)


    async def parse_embed_cooldowns(self, embed: discord.Embed):
        now = datetime.datetime.utcnow()
        cooldowns = []

        for field in embed.fields:
            for cooldown in str(field.value).splitlines():
                splitted_cooldown = cooldown.split(" ")
                emoji = splitted_cooldown[0]

                if emoji == ":clock4:":
                    name_and_duration = splitted_cooldown[2:]
                    in_name = True
                    name = ""
                    duration = ""

                    for element in name_and_duration:
                        if in_name:
                            name += element.replace("*", "").replace("`", "")
                            if element.endswith("`**"):
                                in_name = False
                            else:
                                name += " "
                        else:
                            duration += element.replace("*", "").replace("(", "").replace(")", "")

                    parsed_duration = ShortTime(duration, now=now)
                    cooldowns.append((name, parsed_duration.dt))
        return cooldowns

    async def get_rpg_role(self, ctx):
        return discord.utils.get(ctx.guild.roles, name=self.config()["rpg_role_name"])

    async def epic_rpg_pings(self, message: discord.Message):
        has_embeds = len(message.embeds)
        is_pingable = False

        if has_embeds:
            embed: discord.Embed = message.embeds[0]
            is_pingable = str(embed.description).startswith("<:epicrpgarena:697563611698298922>")
            is_pingable = is_pingable or (str(embed.author.name).endswith("'s miniboss") and embed.footer.text)
            if len(embed.fields) >= 1:
                first_field_name = str(embed.fields[0].name).replace("*", "").replace("`", "").lower()
                is_pingable = is_pingable or first_field_name.startswith("an epic tree has just grown")
                is_pingable = is_pingable or first_field_name.startswith("<:coin:541384484201693185>")
                is_pingable = is_pingable or first_field_name.startswith("epic npc: i have a special trade today!")
                is_pingable = is_pingable or first_field_name.startswith("<:epiccoin:551605190965329926> oops!")
                is_pingable = is_pingable or first_field_name.startswith("a megalodon has spawned")
                is_pingable = is_pingable or first_field_name.startswith("it's raining coins")

        if is_pingable:
            ctx: MyContext = await self.bot.get_context(message, cls=MyContext)
            rpg_role = await self.get_rpg_role(ctx)
            _ = await ctx.get_translate_function()
            await ctx.send(_("{rpg_role.mention}, you might want to click the reaction above/do what the bot says.", rpg_role=rpg_role))

    async def epic_rpg_cooldowns(self, message: discord.Message):
        is_cooldown = False
        has_embeds = len(message.embeds)
        if has_embeds:
            embed: discord.Embed = message.embeds[0]
            is_cooldown = str(embed.author.name).endswith("'s cooldowns")

        if is_cooldown:
            ctx: MyContext = await self.bot.get_context(message, cls=MyContext)
            try:
                monitored_player_id = int(embed.author.icon_url.split("/")[4])  # ID
            except ValueError:
                print(embed.author.icon_url.split("/"))
            monitored_player: discord.Member = ctx.guild.get_member(monitored_player_id)

            maybe_gather = self.epic_rpg_cd_coros.get(monitored_player_id, None)
            if maybe_gather:
                try:
                    maybe_gather.cancel()
                    await maybe_gather
                except asyncio.CancelledError:
                    pass

            rpg_role = await self.get_rpg_role(ctx)
            if rpg_role in monitored_player.roles:
                cooldowns = await self.parse_embed_cooldowns(embed)

                coros = []
                for name, dt in cooldowns:
                    coros.append(wait_cd(monitored_player, ctx, name, dt))

                await message.add_reaction("<:ah:327906673249484800>")
                ctx.logger.debug(f"Adding monitoring for {len(coros)} cooldowns for the RPG account of {monitored_player.name}.")
                self.epic_rpg_cd_coros[monitored_player_id] = asyncio.gather(*coros)


setup = Community.setup
