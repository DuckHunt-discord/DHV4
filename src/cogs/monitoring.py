"""
Bot monitoring.
"""
import asyncio
import time
from datetime import timedelta
from typing import Union, List, Callable

import discord
from discord.ext import tasks
from discord.ext.commands import CommandError

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import BotState


def _(message):
    return message


def get_now():
    return int(time.time())

DB_MEASURE_INTERVAL = timedelta(minutes=10)

def filter_count_event_list(events: List[int], count_predicate: Callable, keep_predicate: Callable) -> int:
    """
    This function count the number of events matching a predicate and filters the events list inplace following another.

    It returns the count of matching events.
    """
    total_count = 0
    filtered_events = []

    for event in events:
        if count_predicate(event):
            total_count += 1

        if keep_predicate(event):
            filtered_events.append(event)

    events[:] = filtered_events
    return total_count


def get_predicate(delta: timedelta, now: int = None) -> Callable:
    now = now or get_now()

    if delta is not None:
        def time_predicate(timestamp):
            return timestamp > (now - delta.total_seconds())
    else:
        def time_predicate(timestamp):
            return True

    return time_predicate


class Monitoring(Cog):
    display_name = _("Support team: monitoring")
    help_priority = 15
    help_color = 'red'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.ws_send_timings = []
        self.ws_recv_timings = []
        self.message_timings = []
        self.command_timings = []
        self.command_error_timings = []
        self.command_completion_timings = []
        self.background_loop.start()

    def cog_unload(self):
        self.background_loop.cancel()

    @tasks.loop(minutes=10)
    async def background_loop(self):
        await self.save_statistics_to_database()

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(DB_MEASURE_INTERVAL.total_seconds())

    async def get_statistics(self, over=DB_MEASURE_INTERVAL, delete_older_than=timedelta(hours=1)):
        now = get_now()
        count_predicate = get_predicate(over, now)
        keep_predicate = get_predicate(delete_older_than, now)

        stats = {
            # Event counts
            "measure_interval": over.total_seconds(),
            "ws_send": filter_count_event_list(self.ws_send_timings, count_predicate, keep_predicate),
            "ws_recv": filter_count_event_list(self.ws_recv_timings, count_predicate, keep_predicate),
            "messages": filter_count_event_list(self.message_timings, count_predicate, keep_predicate),
            "commands": filter_count_event_list(self.command_timings, count_predicate, keep_predicate),
            "command_errors": filter_count_event_list(self.command_error_timings, count_predicate, keep_predicate),
            "command_completions": filter_count_event_list(self.command_completion_timings, count_predicate, keep_predicate),

            # Curent state
            "guilds": len(self.bot.guilds),
            "users": len(self.bot.users),
            "shards": self.bot.shard_count,
            "ready": self.bot.is_ready(),
            "ws_ratelimited": self.bot.is_ws_ratelimited(),
            "ws_latency": self.bot.latency,
        }

        return stats

    async def save_statistics_to_database(self):
        await BotState.create(**await self.get_statistics())

    # These are all "dumb" event listeners that record the time every time an event is triggered.
    @Cog.listener()
    async def on_socket_raw_send(self, payload: Union[str, bytes]):
        self.ws_send_timings.append(get_now())

    @Cog.listener()
    async def on_socket_raw_receive(self, payload: Union[str, bytes]):
        self.ws_recv_timings.append(get_now())

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        self.message_timings.append(get_now())

    @Cog.listener()
    async def on_command(self, ctx: MyContext):
        self.command_timings.append(get_now())

    @Cog.listener()
    async def on_command_error(self, ctx: MyContext, error: CommandError):
        self.command_error_timings.append(get_now())

    @Cog.listener()
    async def on_command_completion(self, ctx: MyContext):
        self.command_completion_timings.append(get_now())




setup = Monitoring.setup
