import asyncio
import datetime
import json
import random
from typing import Dict

import discord
from utils.cog_class import Cog
from utils import ducks
from time import time

from utils.ducks import deserialize_duck, compute_sun_state
from utils.events import Events
from utils.models import get_enabled_channels, DiscordChannel, get_from_db, DucksLeft

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class DucksSpawning(Cog):
    hidden = True

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0

    async def cog_load(self) -> None:
        self.background_loop = self.bot.loop.create_task(self.loop())
        self.interval = 1
        self.last_planned_day = 0
        self.current_iteration_public = 0

    async def loop(self):
        try:
            await self.before()
        except:
            self.bot.logger.exception("Error in before_loop")
            raise
        now = time()
        current_iteration = int(now)
        while not self.background_loop.cancelled():
            # Precalculate timings
            now = time()
            current_iteration = current_iteration + self.interval
            self.current_iteration_public = current_iteration

            delay = now - current_iteration
            if delay >= 30:
                self.bot.logger.error(f"Ignoring iterations to compensate for delays ({delay} seconds)!")
                current_iteration = int(now)
            elif delay >= 5:
                self.bot.logger.warning(f"Loop running with severe delays ({delay} seconds)!")

            self.bot.logger.debug(f"Ducks spawning loop : [{int(current_iteration)}/{int(now)}]")

            # Loop part
            try:
                await self.spawn_ducks(current_iteration)
            except Exception as e:
                self.bot.logger.exception("Ignoring exception inside loop and hoping for the best...")

            # Loop the loop
            now = time()
            next_iteration = current_iteration + self.interval
            await asyncio.sleep(max(0.0, next_iteration - now))

    async def spawn_ducks(self, now: int):
        SECONDS_SPENT_TODAY = now % 86400
        SECONDS_LEFT_TODAY = 86400 - SECONDS_SPENT_TODAY

        if self.bot.allow_ducks_spawning:
            start_spawning = time()
            ducks_spawned = 0
            for channel, ducks_left_to_spawn in self.bot.enabled_channels.items():
                maybe_spawn_type = await ducks_left_to_spawn.maybe_spawn_type(now)
                if maybe_spawn_type is not None:
                    if self.bot.current_event == Events.CONNECTION and random.randint(1, 10) == 10:
                        continue

                    asyncio.ensure_future(
                        ducks.spawn_random_weighted_duck(self.bot, channel,
                                                         ducks_left_to_spawn.db_channel,
                                                         sun=maybe_spawn_type)
                    )
                    ducks_spawned += 1

                    if self.bot.current_event == Events.MIGRATING and random.randint(1, 10) == 10:
                        asyncio.ensure_future(
                            ducks.spawn_random_weighted_duck(self.bot, channel,
                                                             ducks_left_to_spawn.db_channel,
                                                             sun=maybe_spawn_type))
                        ducks_spawned += 1

                if ducks_spawned > 20:
                    self.bot.logger.warning(f"Tried to make more than {ducks_spawned} ducks spawn at once, "
                                            f"stopping there to protect rate limits...")
                    break

            end_spawning = time()

            if end_spawning-start_spawning > 0.7:
                duration = round(end_spawning-start_spawning, 2)
                self.bot.logger.error(f"Spawning {ducks_spawned} ducks took more than {duration} seconds...")

        start_leaving = time()
        total_leaves = 0
        for channel, ducks_queue in self.bot.ducks_spawned.copy().items():
            for duck in ducks_queue.copy():
                left = await duck.maybe_leave()
                if not left:
                    break
                else:
                    total_leaves += 1

            if total_leaves > 25:
                self.bot.logger.warning(f"Tried to make more than {total_leaves} ducks leave at once, "
                                        f"stopping there to protect rate limits...")
                break

        end_leaving = time()

        if end_leaving-start_leaving > 0.7:
            duration = round(end_leaving - start_leaving, 2)
            self.bot.logger.error(f"Leaving {total_leaves} ducks took more than {duration} seconds...")

        CURRENT_PLANNED_DAY = now - (now % DAY)
        if CURRENT_PLANNED_DAY != self.last_planned_day:
            await self.planify(now)
            embed = discord.Embed()

            embed.colour = discord.Colour.green()
            embed.title = f"It's freetime !"
            embed.description = f"Your magazines have been refilled, and confiscated weapons have just been released"
            dtnow = datetime.datetime.fromtimestamp(now)
            if dtnow.day == 1 and dtnow.month == 4:
                # April 1st
                embed.set_footer(text="🐟️")
            else:
                embed.set_footer(text="Freetime happens every 24 hours.")
            await self.bot.log_to_channel(embed=embed)

        if SECONDS_LEFT_TODAY % HOUR == 0:
            await self.change_event()

    def cog_unload(self):
        self.background_loop.cancel()

        self.bot.logger.info(f"Saving ducks to cache...")

        ducks_spawned = self.bot.ducks_spawned

        ducks_count = 0

        serialized = {}

        # Copy to avoid
        # RuntimeError: dictionary changed size during iteration
        for channel, ducks in ducks_spawned.copy().items():
            ducks_in_channel = []
            for duck in ducks:
                ducks_in_channel.append(duck.serialize())
                ducks_count += 1
            serialized[channel.id] = ducks_in_channel

        with open("cache/ducks_spawned_cache.json", "w") as f:
            json.dump(serialized, f)

        self.bot.logger.info(f"Saved {ducks_count} to cache/ducks_spawned_cache.json")

    async def planify(self, now=None):
        if now is None:
            now = int(time())

        self.last_planned_day = now - (now % DAY)

        db_channels = await get_enabled_channels()

        self.bot.logger.debug(f"Planifying ducks spawns on {len(db_channels)} channels")

        channels_to_disable = []

        channels: Dict[int, discord.TextChannel] = {c.id: c for c in self.bot.get_all_channels()}
        i = 0

        for db_channel in db_channels:
            i += 1
            channel = channels.get(db_channel.discord_id)

            if i % 100 == 0:
                await asyncio.sleep(0)
                self.bot.logger.debug(f"Planifying ducks spawns on {i}/{len(db_channels)} channels")

            if channel:
                self.bot.enabled_channels[channel] = await DucksLeft(channel).compute_ducks_count(db_channel, now)
            else:
                self.bot.logger.warning(f"Channel {db_channel.name} is unknown, marking for disable")
                channels_to_disable.append(db_channel)

        if 0 < len(channels_to_disable) < 100:
            self.bot.logger.warning(f"Disabling {len(channels_to_disable)} channels "
                                    f"that are no longer available to the bot.")
            for db_channel in channels_to_disable:
                # TODO : We can probably only do 1 big query here, but for that I'd have to learn Tortoise.
                # To be honest, improvement would be limited since 100 queries max isn't that slow and there obviously
                # aren't that many channels that get disabled during a reboot...
                db_channel.enabled = False
                await db_channel.save()
                await asyncio.sleep(0)  # Just in case
            self.bot.logger.warning(f"Disabled {len(channels_to_disable)} channels "
                                    f"that are no longer available to the bot.")
        elif len(channels_to_disable) >= 100:
            self.bot.logger.error(f"Too many unavailable channels ({len(channels_to_disable)}) "
                                  f"to disable them. Is discord healthy ?")
            self.bot.logger.error("Consider rebooting the bot once the outage is over. https://discordstatus.com/ for more info.")
            self.bot.logger.error("Bad examples : " + ', '.join([str(c.discord_id) for c in channels_to_disable[:10]]))
        else:
            self.bot.logger.debug(f"All the channels are available :)")

    async def before(self):
        self.bot.logger.info(f"Waiting for ready-ness to planify duck spawns...")

        await self.bot.wait_until_ready()
        # Wait 5 seconds because discord.py can send the ready event a little bit too early
        await asyncio.sleep(5)
        # Then try again to make sure we are still good.
        await self.bot.wait_until_ready()

        self.bot.logger.info(f"Restoring ducks from cache...")

        ducks_count = 0
        try:
            with open("cache/ducks_spawned_cache.json", "r") as f:
                serialized = json.load(f)
        except FileNotFoundError:
            self.bot.logger.warning("No ducks_spawned_cache.json found. Normal on first run.")
            serialized = {}

        self.bot.logger.info(f"Loaded JSON file...")

        self.bot.logger.debug(f"Building channels hash table for fast-access...")
        channels = {c.id: c for c in self.bot.get_all_channels()}
        self.bot.logger.debug(f"Hash table built, restoring ducks...")

        for channel_id, ducks in serialized.items():
            channel = channels.get(int(channel_id), None)

            if channel:
                for data in ducks:
                    ducks_count += 1
                    duck = deserialize_duck(self.bot, channel, data)
                    await duck.spawn(loud=False)

        self.bot.logger.info(f"{ducks_count} ducks restored!")

        await asyncio.sleep(1)

        self.bot.logger.info(f"Planifying ducks spawns for the rest of the day")

        await self.planify()

        embed = discord.Embed()

        embed.colour = discord.Colour.dark_green()
        embed.title = f"Bot restarted"
        embed.description = f"The bot restarted and is now ready to spawn ducks. Get your rifles out!"
        embed.add_field(name="Statistics", value=f"{len(self.bot.guilds)} servers, "
                                                 f"{len(self.bot.enabled_channels)} channels")
        embed.add_field(name="Help and support", value="https://duckhunt.me/support")
        embed.set_footer(text="Ducks that were on the channel previously should have been restored, and can be killed.")
        await self.bot.log_to_channel(embed=embed)

        self.bot.logger.info(f"Restoring an event for the rest of the hour")

        try:
            with open("cache/event_cache.json", "r") as f:
                event_cache = json.load(f)
            event_name = event_cache["current_event"]
            event = Events[event_name]
            self.bot.current_event = event
        except FileNotFoundError:
            self.bot.logger.warning("No event_cache.json found. Normal on first run. Rolling an event instead.")
            await self.change_event()
        except KeyError:
            self.bot.logger.exception("event_cache.json found, but couldn't read it. Rolling an event instead.")
            await self.change_event()

        game = discord.Game(self.bot.current_event.value[0])
        await self.bot.change_presence(status=discord.Status.online, activity=game)

        self.bot.logger.info(f"Ducks spawning started")

    async def calculate_ducks_per_day(self, db_channel: DiscordChannel, now: int):
        # TODO : Compute ducks sleep
        ducks_per_day = db_channel.ducks_per_day

        seconds_elapsed = now % DAY
        seconds_left_in_day = DAY - seconds_elapsed

        pct_day = round(seconds_elapsed / DAY, 2) * 100

        ducks = int((seconds_left_in_day * ducks_per_day) / DAY)

        # self.bot.logger.debug(f"Recomputing : {pct_day}% day done, {ducks}/{ducks_per_day} ducks to spawn today")

        return ducks

    async def recompute_channel(self, channel: discord.TextChannel):
        self.bot.enabled_channels[channel] = await DucksLeft(channel).compute_ducks_count()

    async def change_event(self, force=False):
        if random.randint(1, 12) != 1 and not force:
            self.bot.logger.info("No new event this time!")
            self.bot.current_event = Events.CALM
        else:
            self.bot.logger.debug("It's time for an EVENT!")
            events = [event for event in Events if event != Events.CALM]
            event_choosen:Events = random.choice(events)
            self.bot.logger.info(f"New event : {event_choosen.name}")

            self.bot.current_event = event_choosen
        game = discord.Game(self.bot.current_event.value[0])
        await self.bot.change_presence(status=discord.Status.online, activity=game)

        embed = discord.Embed()
        if self.bot.current_event == Events.CALM:
            embed.colour = discord.Colour.green()
            embed.title = f"{self.bot.current_event.value[0]} (no event for now)"
            embed.description = self.bot.current_event.value[1]
        else:
            embed.colour = discord.Colour.orange()
            embed.title = f"New event : {self.bot.current_event.value[0]}"
            embed.description = self.bot.current_event.value[1]

        embed.set_footer(text="Events change every hour")

        await self.bot.log_to_channel(embed=embed)

        with open("cache/event_cache.json", "w") as f:
            json.dump({
                "current_event": self.bot.current_event.name
            }, f)


setup = DucksSpawning.setup
