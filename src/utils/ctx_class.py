import asyncio
import io

import discord
import typing
from discord import Message, Interaction, AllowedMentions

from discord.ext import commands
from discord.mentions import default
from discord.utils import MISSING

from utils.models import get_from_db
from utils.translations import translate, ntranslate, get_translate_function, get_ntranslate_function

if typing.TYPE_CHECKING:
    from utils.bot_class import MyBot

from utils.interaction import delete_messages_if_message_removed
from utils.logger import LoggerConstant


class InvalidArgument(Exception):
    pass


class MyContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot: 'MyBot'
        self.interaction: typing.Optional[Interaction] = None  # Injected later.
        self._prefix: typing.Optional[str] = None

        self.logger = LoggerConstant(self.bot.logger, self.guild, self.channel, self.author)

    @property
    def prefix(self):
        if self._prefix is not None:
            return self._prefix
        else:
            # Most probably an invalid context, made for running commands with buttons.
            return "dh!"

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    def is_next_send_ephemeral(self):
        return self.interaction and not self.interaction.response.is_done()

    async def reply(self, *args, **kwargs) -> discord.Message:
        return await self.send(*args, **kwargs, reply=True)

    async def send(self,
                   content=None, *,
                   delete_on_invoke_removed=True,
                   file=None,
                   files=None,
                   reply=False,
                   force_public=False,
                   allowed_mentions=None,
                   **kwargs) -> Message:
        if allowed_mentions is None:
            allowed_mentions = discord.AllowedMentions()
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

        send_as_ephemeral = not force_public and self.is_next_send_ephemeral() and not files and not file

        if send_as_ephemeral:
            message = await self.interaction.response.send_message(content,
                                                                   embed=kwargs.get('embed', MISSING),
                                                                   embeds=kwargs.get('embeds', MISSING),
                                                                   view=kwargs.get('view', MISSING),
                                                                   tts=kwargs.get('tts', False),
                                                                   ephemeral=True)
        elif reply:
            db_user = await get_from_db(self.author, as_user=True)
            allowed_mentions = discord.AllowedMentions(replied_user=db_user.ping_friendly).merge(allowed_mentions)

            if self.interaction:
                # We can't respond to the interaction, but it's a button click,
                # so the reply would reply to the message containing the button, which is probably not what we want.
                # Instead, we'll mention the user in the text.

                # Get the mention depending of if the user likes pings.
                if db_user.ping_friendly:
                    mention = self.author.mention
                else:
                    mention = f"{self.author.name}#{self.author.discriminator}"

                # Patch the content to add a mention.
                if content:
                    content = mention + " > " + content
                else:
                    content = mention

                # Then send the message normally.
                message = await super().send(content, file=file, files=files, allowed_mentions=allowed_mentions,
                                             **kwargs)
            else:
                try:
                    # Send a normal reply
                    message = await super().reply(content, file=file, files=files, allowed_mentions=allowed_mentions,
                                                  **kwargs)
                except discord.errors.HTTPException:
                    # Can't reply, probably that the message we are replying to was deleted.
                    # Just send the message instead.
                    # TODO: Maybe add the replied user just like above.
                    #       Not sure if the use-case makes sense here.
                    message = await super().send(content, file=file, files=files, allowed_mentions=allowed_mentions,
                                                 **kwargs)
        else:
            message = await super().send(content, file=file, files=files, allowed_mentions=allowed_mentions, **kwargs)

        # Message deletion if source is deleted
        # Except if the message was only shown to the user.
        if delete_on_invoke_removed and not send_as_ephemeral:
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

        if language == "zh-Hans":
            return "zh"  # Babel don't know about Simplified Chinese
        else:
            language = language.replace('-', '_')

        return language

    async def translate(self, message):
        language_code = await self.get_language_code()
        return translate(message, language_code)

    async def ntranslate(self, singular, plural, n):
        language_code = await self.get_language_code()
        return ntranslate(singular, plural, n, language_code)

    async def get_translate_function(self, user_language=False):
        language_code = await self.get_language_code(user_language=user_language)

        return get_translate_function(self, language_code, additional_kwargs={'ctx': self})

    async def get_ntranslate_function(self, user_language=False):
        language_code = await self.get_language_code(user_language=user_language)

        return get_ntranslate_function(self, language_code, {'ctx': self})

    async def is_channel_enabled(self):
        db_channel = await get_from_db(self.channel)
        if db_channel:
            return db_channel.enabled
        else:
            return False
