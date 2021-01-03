import asyncio
import datetime

import discord
import typing
from typing import List
import random

from utils.models import get_from_db, DiscordChannel

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot


def get_timedelta(event, now):
    return datetime.datetime.fromtimestamp(event) - datetime.datetime.fromtimestamp(now)


def escape_everything(mystr: str):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(mystr))


async def delete_messages_if_message_removed(bot: 'MyBot', watch_message: discord.Message, message_to_delete: discord.Message):
    def check(message: discord.RawMessageDeleteEvent):
        return message.message_id == watch_message.id

    try:
        await bot.wait_for('raw_message_delete', check=check, timeout=3600)
    except asyncio.TimeoutError:
        pass
    else:
        await message_to_delete.delete(delay=(random.randrange(1, 10) / 10))


async def purge_channel_messages(channel: discord.TextChannel, check=None, **kwargs):
    def check_pinned(message: discord.Message):
        return not message.pinned

    if check is None:
        check = check_pinned
    else:
        check = lambda m: check(m) and check_pinned(m)

    return await channel.purge(check=check, **kwargs)


async def create_and_save_webhook(bot: 'MyBot', channel: typing.Union[DiscordChannel, discord.TextChannel], force=False):
    if isinstance(channel, DiscordChannel):
        db_channel = await get_from_db(bot.get_channel(channel.discord_id))
    else:
        db_channel: DiscordChannel = await get_from_db(channel)

    webhook = None
    try:
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            webhook: discord.Webhook
            if webhook.name == "DuckHunt":
                db_channel.webhook_urls.append(webhook.url)
        if len(db_channel.webhook_urls) == 0 or force:
            webhook = await channel.create_webhook(name="DuckHunt", reason="Better Ducks")
            db_channel.webhook_urls.append(webhook.url)

    except discord.Forbidden:
        db_channel.use_webhooks = False

    await db_channel.save()
    return webhook


async def get_webhook_if_possible(bot: 'MyBot', channel: typing.Union[DiscordChannel, discord.TextChannel]):
    if isinstance(channel, DiscordChannel):
        db_channel = channel
    else:
        db_channel: DiscordChannel = await get_from_db(channel)

    if len(db_channel.webhook_urls) == 0:
        webhook = await create_and_save_webhook(bot, channel)
    else:
        webhook = discord.Webhook.from_url(random.choice(db_channel.webhook_urls), adapter=discord.AsyncWebhookAdapter(bot.client_session))

    return webhook


def anti_bot_zero_width(mystr: str):
    """Add zero-width spaces and replace lookalikes characters in a string to make it harder to detect for bots"""

    addings = [
        "​",  # ZWSP
        ]

    replacements = {
        " ": [" "]  # ['\u00A0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200A', '\u202F', '\u205F']
    }

    out = []
    for char in mystr:
        if char in replacements.keys():
            if random.randint(1, 100) <= 50:
                out.append(random.choice(replacements[char]))
            else:
                out.append(char)
        else:
            out.append(char)
        if random.randint(1, 100) <= 15 and char not in ["\\", "*", "`", "~", ">", "|"]:
            out.append(random.choice(addings))

    return ''.join(out)
