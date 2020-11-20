import asyncio
import io

import discord
import typing
from discord import Message
from discord.errors import InvalidArgument
from discord.ext import commands

from utils.models import get_from_db
from utils.translations import translate

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot

from utils.interaction import delete_messages_if_message_removed
from utils.logger import LoggerConstant


class MyContext(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: 'MyBot'

        self.logger = LoggerConstant(self.bot.logger, self.guild, self.channel, self.author)

    async def reply(self, *args, **kwargs):  # When V2 releases...
        return await self.send(*args, **kwargs)

    async def send(self, content=None, *, delete_on_invoke_removed=True, file=None, files=None, reply=False, **kwargs) -> Message:
        # Case for a too-big message
        if content and len(content) > 1990:
            self.logger.warning("Message content is too big to be sent, putting in a text file for sending.")

            message_file = discord.File(io.BytesIO(content.encode()), filename="message.txt")
            content = None

            if file is not None and files is not None:
                raise InvalidArgument('Cannot pass both file and files parameter to send()')
            elif file is not None:
                files = [message_file, file]
                file = None
            elif files is not None:
                if len(files) == 10:
                    raise InvalidArgument('Content is too big, and too many files were provided')
                else:
                    files = [message_file] + files
            else:
                file = message_file

        if reply:
            message = await self.reply(content, file=file, files=files, **kwargs)
        else:
            message = await super().send(content, file=file, files=files, **kwargs)

        # Message deletion if source is deleted
        if delete_on_invoke_removed:
            asyncio.ensure_future(delete_messages_if_message_removed(self.bot, self.message, message))

        return message

    def ducks(self):
        self.bot: 'MyBot'
        return self.bot.ducks_spawned[self.channel]

    async def target_next_duck(self):
        ducks = self.ducks()
        try:
            myduck = ducks[0]
        except IndexError:
            return None

        if myduck.fake and len(ducks) > 1:
            myduck.despawn()
            return await self.target_next_duck()

        await myduck.target(self.author)
        if not await myduck.is_killed():
            return myduck
        else:
            return await myduck.target(self.author)

    def author_permissions(self):
        return self.channel.permissions_for(self.author)

    async def get_language_code(self, user_language=False):
        if self.guild and not user_language:
            db_guild = await get_from_db(self.guild)
            language = db_guild.language
        else:
            db_user = await get_from_db(self.author, as_user=True)
            language = db_user.language

        return language

    async def translate(self, message):
        language_code = await self.get_language_code()
        return translate(message, language_code)

    async def get_translate_function(self, user_language=False):
        language_code = await self.get_language_code(user_language=user_language)

        def _(message, **kwargs):
            kwargs = {'ctx': self, **kwargs}
            return translate(message, language_code).format(**kwargs)

        return _

    async def is_channel_enabled(self):
        db_channel = await get_from_db(self.channel)
        return db_channel.enabled

