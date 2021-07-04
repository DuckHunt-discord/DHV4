from abc import ABC
from typing import Iterable, List, Any, Optional, Dict, Union

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
    fake_message.author = interaction.user

    ctx = await bot.get_context(fake_message, cls=MyContext)
    ctx.interaction = interaction

    return ctx


class BigButtonMixin(ui.Button):
    button_pad_to = 78

    def __init__(self, *args, label: Optional[str] = None,  **kwargs):
        if label:
            label = self.pad_value(label)

        super().__init__(*args, label=label, **kwargs)

    def pad_value(self, value: str) -> str:
        return value.center(self.button_pad_to, "⠀")

    @property
    def label(self):
        return super().label

    @label.setter
    def label(self, value):
        super().label.fset(self, self.pad_value(value))


class CommandButton(BigButtonMixin, ui.Button):
    def __init__(self, bot, command, command_args=None, command_kwargs=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if command_kwargs is None:
            command_kwargs = {}

        if command_args is None:
            command_args = []

        self.bot = bot
        self.command = command
        self.command_args = command_args
        self.command_kwargs = command_kwargs

    async def get_command_args(self, interaction: Interaction):
        return self.command_args

    async def get_command_kwargs(self, interaction: Interaction):
        return self.command_kwargs

    async def callback(self, interaction: Interaction):
        ctx = await get_context_from_interaction(self.bot, interaction)
        return await ctx.invoke(self.command, *await self.get_command_args(interaction), **await self.get_command_kwargs(interaction))


class View(ui.View):
    def __init__(self, bot, timeout=None):
        self.bot = bot
        self.sent_to: Optional[Messageable] = None
        self.sent_message: Optional[Message] = None
        super().__init__(timeout=timeout)

    def disable(self):
        """
        Disable all the items in the view
        """
        for item in self.children:
            item.disabled = True

        return self

    async def send(self, where: Messageable, *args, **kwargs):
        self.sent_to = where
        self.sent_message = await where.send(*args, view=self, **kwargs)
        return self.sent_message

    async def refresh_message(self):
        """Refresh the view on the message where it was sent."""
        if self.sent_to:
            await self.sent_message.edit(view=self)
        else:
            return None


class AuthorizedUserMixin(View):
    authorized_users_ids = []

    async def get_authorized_users_ids(self) -> Iterable[int]:
        """|coro|

        Returns a list of users authorized to run the callback.
        """
        return self.authorized_users_ids

    async def is_user_authorized(self, interaction: Interaction) -> bool:
        """|coro|

        Check if the user is authorized to run the callback.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that triggered this UI item.
        """
        authorized_ids = await self.get_authorized_users_ids()
        return authorized_ids == '__all__' or interaction.user.id in authorized_ids

    async def interaction_check(self, interaction: Interaction) -> bool:
        return await self.is_user_authorized(interaction) and await super().interaction_check(interaction)


class DisableViewOnTimeoutMixin(View):
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
                 persist: bool = True,
                 **button_kwargs, ):

        super().__init__(bot)

        if isinstance(command_to_be_ran, str):
            command_to_be_ran = bot.get_command(command_to_be_ran)

        if command_to_be_ran is None:
            raise RuntimeError("The command passed can't be found.")

        if command_args or command_kwargs or authorized_users != '__all__':
            persist = False

        if persist:
            persistance_id = f"command_view:f{command_to_be_ran.qualified_name}"
        else:
            persistance_id = None

        self.authorized_users_ids = authorized_users

        self.add_item(CommandButton(bot, command_to_be_ran, command_args, command_kwargs, custom_id=persistance_id, row=0, **button_kwargs))


class ConfirmView(DisableViewOnTimeoutMixin, AuthorizedUserMixin, View):
    def __init__(self, ctx: MyContext, _,  timeout=60):
        super().__init__(ctx.bot, timeout=timeout)
        self.ctx = ctx
        self.value = None

        self.cancel.label = _('Cancel')
        self.confirm.label = _('Confirm')

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
        await super().send(self.ctx, *args, **kwargs)

        # Wait for the View to stop listening for input...
        await self.wait()

        return self.value

    async def is_user_authorized(self, interaction: Interaction) -> bool:
        """|coro|

        Check if the user is authorized to run the callback.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that triggered this UI item.
        """
        ret = interaction.user.id == self.ctx.author.id

        return ret


async def init_all_persistant_command_views(bot: MyBot):
    for command in bot.walk_commands():
        bot.add_view(CommandView(bot, command, persist=True, label=f'{command.qualified_name}', style=ButtonStyle.blurple))
