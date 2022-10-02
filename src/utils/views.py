from abc import ABC
from typing import Iterable, List, Any, Optional, Dict, Union

import discord
from discord import ui, Interaction, ButtonStyle, Message
from discord.abc import Messageable
from discord.ext.commands import Command

from utils.bot_class import MyBot
from utils.ctx_class import MyContext


async def get_context_from_interaction(bot: MyBot, interaction: Interaction) -> MyContext:
    """
    Return a modified, probably invalid but "good enough" context for use with the commands extensions.
    The referenced message is invalid, but the author is the user that clicked.

    This might not work in DMs
    """
    fake_message = interaction.message

    if fake_message is None:
        fake_message = interaction.channel.last_message or await interaction.channel.fetch_message(interaction.channel.last_message_id)
        bot.logger.debug("Got last message from cache/network for get_context")
    fake_message.author = interaction.user

    ctx = await bot.get_context(fake_message, cls=MyContext)
    ctx.interaction = interaction

    bot.logger.debug(f"Created fake_context {ctx}")

    return ctx


class BigButtonMixin(ui.Button):
    """
    Makes buttons bigger, by padding them using invisible characters.
    It works well on desktop, but not very well on mobile, because text might be truncated there.

    Use with caution.
    """
    def __init__(self, *args, button_pad_to: int = 78, label: Optional[str] = None, **kwargs):
        """
        Adds a new argument to button creation : the total length of the button (invalid if higher than 80).
        """
        self.button_pad_to = button_pad_to

        if label:
            label = self.pad_value(label)

        super().__init__(*args, label=label, **kwargs)

    def pad_value(self, value: str) -> str:
        """
        Override this function to change how padding is applied to the label
        """
        return value.center(self.button_pad_to, "⠀")

    @property
    def label(self) -> Optional[str]:
        """Optional[:class:`str`]: The label of the button, if available."""
        return self._underlying.label

    @label.setter
    def label(self, value: Optional[str]):
        self._underlying.label = self.pad_value(value) if value is not None else value


class AutomaticDeferMixin(ui.Item, ABC):
    """
    Add this to prevent the action from erroring out client-side, by deferring it anyway.
    """
    async def callback(self, interaction: Interaction):
        await super().callback(interaction)

        if not interaction.response.is_done():
            # Hopefully prevent the button from erroring out.
            await interaction.response.defer()


class CommandButton(AutomaticDeferMixin, ui.Button):
    def __init__(self, bot, command, command_args=None, command_kwargs=None, *args, **kwargs):
        """
        Button to execute a command. A list of args and kwargs can be passed to run the command with those args.
        """
        super().__init__(*args, **kwargs)

        if command_kwargs is None:
            command_kwargs = {}

        if command_args is None:
            command_args = []

        self.bot = bot
        self.command: Command = command
        self.command_args = command_args
        self.command_kwargs = command_kwargs

    async def get_command_args(self, interaction: Interaction):
        """
        Get all the command arguments. By default, this uses the list provided when creating the button,
        but behavior can be changed here.
        """
        return self.command_args

    async def get_command_kwargs(self, interaction: Interaction):
        """
        Get all the command keyword arguments. By default, this uses the dictionary provided when creating
        the button, but behavior can be changed here.
        """
        return self.command_kwargs

    async def callback(self, interaction: Interaction):
        ctx = await get_context_from_interaction(self.bot, interaction)

        try:
            can_run = await self.command.can_run(ctx)
        except Exception as e:
            ctx.logger.info(f"Can run is false for {self} - {e}")
            _ = await ctx.get_translate_function(user_language=True)
            await interaction.response.send_message(_('❌ You cannot run this command.'), ephemeral=True)
            return

        if can_run:
            return await ctx.invoke(self.command, *await self.get_command_args(interaction), **await self.get_command_kwargs(interaction))


class View(ui.View):
    """
    Nicer view subclass, providing some convenience methods for subclasses.
    """
    def __init__(self, bot, timeout=None):
        self.bot = bot
        self.sent_to: Optional[Messageable] = None
        self.sent_message: Optional[Message] = None
        super().__init__(timeout=timeout)

    def disable(self):
        """
        Disable all the items in the view. You MUST edit the message (see refresh_message) to disable the buttons in the message.
        """
        for item in self.children:
            item.disabled = True

        return self

    async def send(self, where: Messageable, *args, **kwargs):
        """
        Used to send the view in a message somewhere. Use this to be able to call refresh_message later.

        Args and kwargs are passed to the where.send method.
        """
        if len(args) == 0 and kwargs.get('content', None) is None:
            kwargs['content'] = "\u200b"  # Zero width space, to send the view only.

        self.sent_to = where
        self.sent_message = await where.send(*args, view=self, **kwargs)
        return self.sent_message

    async def refresh_message(self):
        """
        Refresh the view on the message where it was sent.
        """
        if self.sent_to:
            await self.sent_message.edit(view=self)
        else:
            return None


class AuthorizedUserMixin(View):
    authorized_users_ids = []

    async def get_authorized_users_ids(self) -> Iterable[int]:
        """
        Returns a list of users authorized to run the callback.
        """
        return self.authorized_users_ids

    async def is_user_authorized(self, interaction: Interaction) -> bool:
        """
        Check if the user is authorized to run the callback.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that triggered this UI item.
        """
        authorized_ids = await self.get_authorized_users_ids()
        return authorized_ids == '__all__' or interaction.user.id in authorized_ids

    async def interaction_check(self, interaction: Interaction) -> bool:
        if await self.is_user_authorized(interaction):
            return await super().interaction_check(interaction)
        else:
            await self.authorization_check_failed(interaction)
            return False

    async def authorization_check_failed(self, interaction):
        """
        Function ran when the authorization check failed. Use this to send a message to the user
        instead of just failing the view in the client.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that triggered this UI item.
        """
        ctx = await get_context_from_interaction(self.bot, interaction)
        _ = await ctx.get_translate_function(user_language=True)

        await interaction.response.send_message(_('❌ You are not allowed to click on this button'), ephemeral=True)


class DisableViewOnTimeoutMixin(View):
    """
    Mixin to automatically disable buttons in the view when the view times out.
    """
    async def on_timeout(self):
        self.disable()
        await self.refresh_message()

        return await super().on_timeout()


class CommandView(AuthorizedUserMixin, View):
    """
    A View that will run a command when the button inside is clicked.
    If you give a persistance_id, you'll have to register the view with the bot when starting it.

    Invoke like so:
    view = CommandView(bot, command, authorized_users=[ctx.author.id], label=_('Do something'), style=discord.ButtonStyle.grey)

    This view won't be persisted when command_args, command_kwargs or authorized_users are passed.
    """

    def __init__(self,
                 bot: MyBot,
                 command_to_be_ran: Union[Command, str],
                 command_args: Optional[List[Any]] = None,
                 command_kwargs: Optional[Dict[str, Any]] = None,
                 authorized_users: Iterable[int] = '__all__',
                 persist: Union[bool, str] = True,
                 **button_kwargs, ):

        super().__init__(bot)

        if isinstance(command_to_be_ran, str):
            command_to_be_ran = bot.get_command(command_to_be_ran)

        if command_to_be_ran is None:
            raise RuntimeError("The command passed can't be found.")

        if isinstance(persist, bool) and command_args or command_kwargs or authorized_users != '__all__':
            persist = False

        if isinstance(persist, str):
            persistance_id = persist
        elif persist:
            persistance_id = f"cmd:cn{command_to_be_ran.qualified_name}"
        else:
            persistance_id = None

        self.authorized_users_ids = authorized_users

        self.add_item(CommandButton(bot, command_to_be_ran, command_args, command_kwargs, custom_id=persistance_id, row=0, **button_kwargs))


class ConfirmView(DisableViewOnTimeoutMixin, AuthorizedUserMixin, View):
    """
    Sends a confirmation view, with two buttons : cancel and confirm.
    """
    def __init__(self, ctx: MyContext, _,  timeout=60):
        super().__init__(ctx.bot, timeout=timeout)
        self.ctx = ctx
        self.value = None

        self.cancel.label = _('Cancel')
        self.confirm.label = _('Confirm')

    # Ignore passed labels, they are overridden in __init__
    @ui.button(label='cancel', style=ButtonStyle.red)
    async def cancel(self, button: ui.Button, interaction: Interaction):
        self.value = False

        self.disable()
        self.stop()
        await self.refresh_message()

    @ui.button(label='confirm', style=ButtonStyle.green)
    async def confirm(self, button: ui.Button, interaction: Interaction):
        # await interaction.response.send_message('Confirming', ephemeral=True)
        self.value = True

        self.disable()
        self.stop()
        await self.refresh_message()

    async def send(self, *args, **kwargs):
        """
        Run the whole confirmation flow: send the view, wait for input (or timeout), and return the status

        If this returns True, the action was confirmed.
        If this returns False, the action was cancelled.
        If this returns None, a timeout happened.
        """
        await super().send(self.ctx, *args, **kwargs)

        # Wait for the View to stop listening for input...
        await self.wait()

        return self.value

    async def is_user_authorized(self, interaction: Interaction) -> bool:
        """
        Restrict buttons to the user that triggered the confirmation.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that triggered this UI item.
        """
        ret = interaction.user.id == self.ctx.author.id

        return ret


class NitroButton(BigButtonMixin, ui.Button):
    """
    A basic button to demonstrate the above system. This shows a fake, rick-rolling "you've got Nitro" embed+button.
    """
    async def callback(self, interaction: Interaction):
        await interaction.response.send_message("https://media.giphy.com/media/g7GKcSzwQfugw/giphy.mp4", ephemeral=True)
        self.button_pad_to = 40

        self.label = "Claimed"
        self.style = ButtonStyle.gray
        self.view.disable()
        self.view.stop()

        second_embed = discord.Embed(
            colour=discord.Colour.dark_theme(),
            title='A WILD GIFT APPEARS!',
            description="Hmm, it seems someone already claimed this gift."
        )

        second_embed.set_thumbnail(url="https://i.imgur.com/w9aiD6F.png")

        await self.view.sent_message.edit(embed=second_embed, view=self.view)


class NitroView(View):
    """
    The view for the nitro button above.
    """
    def __init__(self, bot):
        super().__init__(bot)

        self.add_item(NitroButton(button_pad_to=29, label='Accept', style=ButtonStyle.green))


async def nitro_prank(ctx: MyContext):
    """
    The full view process for the nitro button above.
    """
    first_embed = discord.Embed(
        colour=discord.Colour.dark_theme(),
        title='A WILD GIFT APPEARS!',
        description="**Nitro**\nExpires in 48 hours."
    )

    first_embed.set_thumbnail(url="https://i.imgur.com/w9aiD6F.png")

    await NitroView(ctx.bot).send(ctx, embed=first_embed, delete_on_invoke_removed=False)


async def init_all_persistant_command_views(bot: MyBot):
    """
    Convenience function to initialize CommandViews for every command in the bot, making them persist.

    Note that CommandViews with parameters are not persisted by default.
    """
    for command in bot.walk_commands():
        bot.add_view(CommandView(bot, command, persist=True, label=f'{command.qualified_name}', style=ButtonStyle.blurple))
        # Having command_can_run set to false is a security risk : buttons IDs can be faked, thereby allowing users to run arbitrary commands without checks.
        # https://discord.com/channels/336642139381301249/669155775700271126/864496918671261717
        # bot.add_view(CommandView(bot, command, persist=True, label=f'{command.qualified_name}', style=ButtonStyle.blurple, command_can_run=False))
