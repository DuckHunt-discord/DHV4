import discord
from discord.ext import commands

from utils import checks, models
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.inventory_items import ALL_INVENTORY, ALL_SHORTCODE, InvalidUsesCount, NotInInventory
from utils.models import get_from_db, DiscordUser, get_user_inventory


def _(message):
    return message


class InventoryCommands(Cog):
    display_name = _("Inventory")
    help_priority = 9

    @commands.command(aliases=["open"])
    @checks.channel_enabled()
    async def use(self, ctx: MyContext, item_shortcode: str, item_uses:int = 1):
        """
        Alias for dh!inv use, so that you can just type dh!use instead.
        """
        await self.inv_use(ctx, item_shortcode, item_uses)

    @commands.group(aliases=["inv"])
    @checks.channel_enabled()
    async def inventory(self, ctx: MyContext):
        """
        Show your inventory content.

        The inventory is global. It means that all items you can store in it can be used on (almost) every server.
        Server administrators can disable inventory usage on specific channels.
        """
        if not ctx.invoked_subcommand:
            _ = await ctx.get_translate_function(user_language=True)

            db_user: DiscordUser = await get_from_db(ctx.author, as_user=True)
            inventory = await get_user_inventory(db_user)

            embed = discord.Embed(title=_("Your inventory"))
            empty = True
            for Item in ALL_INVENTORY:
                item = Item(inventory)
                if item.is_in_inventory():
                    empty = False
                    item_name = _(item.name)
                    item_shortcode = _(item.shortcode)
                    item_desc = _(item.description)
                    item_uses = item.count_in_inventory()
                    embed.add_field(name=f"**{item_uses}x {item_name}** ({item_shortcode})",
                                    value=item_desc)

            if empty:
                embed.description = _("A lot of air and a starved mosquito.")
            else:
                embed.set_footer(text=_("`{prefix}inv use shortcode` to use an item", prefix=ctx.prefix))

            await ctx.send(embed=embed)

    @inventory.command(name="give")
    @checks.needs_access_level(models.AccessLevel.BOT_MODERATOR)
    async def inv_give(self, ctx: MyContext, target: discord.User, item_shortcode: str, item_uses: int = 1):
        """
        Give something to some player.
        """
        _ = await ctx.get_translate_function(user_language=True)
        db_target = await get_from_db(target, as_user=True)

        # noinspection PyPep8Naming
        Item = ALL_SHORTCODE.get(item_shortcode, None)
        if Item is None:
            await ctx.send(_("❌ Unknown item."))
            return

        await Item.give_to(db_target, uses=item_uses)

        await ctx.send(_("👌 Item has been given to {target.name}.", target=target))

    @inventory.command(name="use", aliases=["open"])
    async def inv_use(self, ctx: MyContext, item_shortcode: str, item_uses: int = 1):
        """
        Use one of the items in your inventory.
        """
        _ = await ctx.get_translate_function(user_language=True)

        db_channel = await get_from_db(ctx.channel)

        if not db_channel.allow_global_items:
            await ctx.send(_('❌ Items usage is disabled on this channel.'))
            return

        if item_uses < 1:
            await ctx.send(_('❌ The number of items to use must be a number greater or equal to 1.'))
            return

        # noinspection PyPep8Naming
        Item = ALL_SHORTCODE.get(item_shortcode, None)
        if Item is None:
            await ctx.send(_("❌ Unknown item."))
            return

        try:
            await Item.use_by(ctx, uses=item_uses, db_channel=db_channel)
        except InvalidUsesCount:
            await ctx.send(_("❌ You can't use this item that many times."))
            return
        except NotInInventory:
            await ctx.send(_("❌ You don't have that item."))
            return


setup = InventoryCommands.setup
