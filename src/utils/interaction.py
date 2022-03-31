import asyncio
import datetime

import discord
import typing
from typing import List
import random

from discord.ext import menus
from discord.ext.commands import MemberConverter

from utils.models import get_from_db, DiscordChannel

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot


class EmbedCounterPaginator(menus.ListPageSource):
    def __init__(self, entries, *, per_page,
                 embed_title="Counter paginator",
                 embed_color=discord.Color.magenta(),
                 name_str="{elem}",
                 value_str="{n}",
                 field_inline=True
                 ):
        super().__init__(entries, per_page=per_page)
        self.embed_title = embed_title
        self.embed_color = embed_color
        self.name_str = name_str
        self.value_str = value_str
        self.field_inline = field_inline

    async def format_page(self, menu, entries):
        embed = discord.Embed(title=self.embed_title, colour=self.embed_color)

        for elem, n in entries:
            embed.add_field(name=self.name_str.format(elem=elem),
                            value=self.value_str.format(n=n),
                            inline=self.field_inline)

        # you can format the embed however you'd like
        return embed


class SmartMemberConverter(MemberConverter):
    async def query_member_named(self, guild, argument):
        if len(argument) > 5 and argument[-5] == '#':
            await super().query_member_named(guild, argument)
        else:
            # Don't use names to convert. It's fucking stupid.
            return None


def get_timedelta(event, now):
    return datetime.datetime.fromtimestamp(event) - datetime.datetime.fromtimestamp(now)


def escape_everything(mystr: str):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(mystr))


async def delete_messages_if_message_removed(bot: 'MyBot', watch_message: discord.Message,
                                             message_to_delete: discord.Message):
    def check(message: discord.RawMessageDeleteEvent):
        return message.message_id == watch_message.id

    try:
        await bot.wait_for('raw_message_delete', check=check, timeout=3600)
    except asyncio.TimeoutError:
        pass
    else:
        bot.logger.debug(f"Deleting message {message_to_delete.id} following deletion of invoke - {watch_message.id}")
        await message_to_delete.delete(delay=(random.randrange(1, 10) / 10))


async def purge_channel_messages(channel: discord.TextChannel, check=None, **kwargs):
    def check_pinned(message: discord.Message):
        return not message.pinned

    if check is None:
        check = check_pinned
    else:
        check = lambda m: check(m) and check_pinned(m)

    return await channel.purge(check=check, **kwargs)


async def create_and_save_webhook(bot: 'MyBot', channel: typing.Union[DiscordChannel, discord.TextChannel],
                                  force=False):
    if isinstance(channel, DiscordChannel):
        channel = bot.get_channel(channel.discord_id)
        if channel is None:
            return None
        db_channel = await get_from_db(channel)
    else:
        db_channel: DiscordChannel = await get_from_db(channel)

    webhook = None
    try:
        webhooks = await channel.webhooks()
        db_channel.webhook_urls = []
        for webhook in webhooks:
            webhook: discord.Webhook
            if webhook.name == "DuckHunt":
                db_channel.webhook_urls.append(webhook.url)
        if len(db_channel.webhook_urls) == 0 or (force and len(db_channel.webhook_urls) <= 5):
            webhook = await channel.create_webhook(name="DuckHunt", reason="Better Ducks")
            db_channel.webhook_urls.append(webhook.url)
        else:
            return None

    except discord.Forbidden:
        db_channel.use_webhooks = False
    except discord.HTTPException:
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
        url = random.choice(db_channel.webhook_urls)
        try:
            webhook = discord.Webhook.from_url(url, session=bot.client_session)
        except ValueError:
            db_channel.webhook_urls.remove(url)
            await db_channel.save()
            webhook = None

    return webhook


def anti_bot_zero_width(mystr: str):
    """Add zero-width spaces and replace lookalikes characters in a string to make it harder to detect for bots"""

    addings = [
        "​",  # ZWSP
    ]

    replacements = {
        " ": [" "]
        # ['\u00A0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200A', '\u202F', '\u205F']
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


async def make_message_embed(message: discord.Message):
    embed = discord.Embed(color=discord.Colour.blurple())
    embed.set_author(name=message.author.name, icon_url=str(message.author.display_avatar.url))
    embed.description = message.content

    if len(message.attachments) == 1:
        url = str(message.attachments[0].url)
        if not message.channel.nsfw and (url.endswith(".webp") or url.endswith(".png") or url.endswith(".jpg")):
            embed.set_image(url=url)
        else:
            embed.add_field(name="Attached", value=url)

    elif len(message.attachments) > 1:
        for attach in message.attachments:
            embed.add_field(name="Attached", value=attach.url)

    if not message.guild:
        embed.set_footer(text=f"Private message",
                         icon_url=str(message.guild.icon.url))
    elif message.channel.is_nsfw():
        embed.set_footer(text=f"{message.guild.name}: [NSFW] #{message.channel.name}",
                         icon_url=str(message.guild.icon.url))
    else:
        embed.set_footer(text=f"{message.guild.name}: #{message.channel.name}",
                         icon_url=str(message.guild.icon.url))

    embed.timestamp = message.created_at

    return embed
