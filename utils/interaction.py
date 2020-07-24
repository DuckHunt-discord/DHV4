import asyncio

import discord
import typing
from typing import List
import random

from utils.models import get_from_db, DiscordChannel

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot


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


async def get_webhook_if_possible(bot: 'MyBot', channel: discord.TextChannel):
    db_channel: DiscordChannel = await get_from_db(channel)

    if not db_channel.webhook_url:
        try:
            webhook = await channel.create_webhook(name="DuckHunt", reason="Better Ducks")
            db_channel.webhook_url = webhook.url
            await db_channel.save()
        except discord.Forbidden:
            return None

    else:
        webhook = discord.Webhook.from_url(db_channel.webhook_url, adapter=discord.AsyncWebhookAdapter(bot.client_session))

    return webhook


def anti_bot_zero_width(mystr: str):
    """Add zero-width spaces and replace lookalikes characters in a string to make it harder to detect for bots"""

    addings = ["\u2060",  # Word joiner
               "​"      ,  # ZWSP
    ]

    replacements = {
        " ": ['\u00A0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200A', '\u202F', '\u205F', '\u3000']
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
        if random.randint(1, 100) <= 15 and char not in ["\\"]:
            out.append(random.choice(addings))

    return ''.join(out)

