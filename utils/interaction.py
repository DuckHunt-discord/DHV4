import asyncio
import random
import typing

import discord

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot


def escape_everything(str_to_escape: str):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(str_to_escape))


async def delete_messages_if_message_removed(bot: 'MyBot', watch_message: discord.Message,
                                             message_to_delete: discord.Message):
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
        c = check_pinned
    else:
        def c(m):
            check(m) and check_pinned(m)

    return await channel.purge(check=c, **kwargs)
