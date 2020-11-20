import asyncio
import random

import discord
from discord.ext import commands
from discord.ext import menus

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db, get_player, DiscordUser, Player


def _(s):
    return s


INV_COMMON_ITEMS = {
    'welcome_package': {"type": "lootbox", "action": "welcome", "name": _("A welcome gift"), "description": _("Open in the lootbox menu")},
    'vip_card': {"type": "item", "action": "set_vip", "uses": 1, "name": _("VIP Card"), "description": _("A nice and shiny card that allow you to set a server as VIP.")},
    'boost_exp': {"type": "item", "action": "add_exp", "uses": 1, "amount": 50, "name": _("A book"), "description": _("Reading it will give you experience")},
    'refill_magazines': {"type": "item", "action": "refill_magazines", "uses": 2, "name": _("A free card for magazines"), "description": _("Redeem it to refill your weapon.")}
}

INV_LOOTBOX_ITEMS = {
    'welcome': [{"luck": 100, "item": INV_COMMON_ITEMS['boost_exp']}, {"luck": 100, "item": INV_COMMON_ITEMS['refill_magazines']}],
    'vote': [{"luck": 5, "item": INV_COMMON_ITEMS['boost_exp']}, {"luck": 100, "item": INV_COMMON_ITEMS["refill_magazines"]}]
}

BP_COMMON_ITEMS = {

}

BP_LOOTBOX_ITEMS = {

}


class ItemsMenusSource(menus.ListPageSource):
    def __init__(self, ctx: MyContext, data, title):
        super().__init__(data, per_page=4)
        self.ctx = ctx
        self.title = title

    async def format_page(self, menu, entries):
        _ = await self.ctx.get_translate_function(user_language=True)
        e = discord.Embed()
        e.title = self.title
        offset = menu.current_page * self.per_page

        for i, item in enumerate(entries, start=offset):
            e.add_field(name=f"**{i + 1}** - " + _(item["name"]), value=_(item["description"]), inline=False)
        return e


async def show_items_menu(ctx, items, title: str):
    pages = menus.MenuPages(source=ItemsMenusSource(ctx, items, title), clear_reactions_after=True)
    await pages.start(ctx)


class InventoryCommands(Cog):
    @commands.group(aliases=["inv"])
    @checks.channel_enabled()
    async def inventory(self, ctx: MyContext):
        """
        Show your inventory content (The global backpack)
        """
        if not ctx.invoked_subcommand:
            _ = await ctx.get_translate_function(user_language=True)

            db_user: DiscordUser = await get_from_db(ctx.author, as_user=True)
            inventory = db_user.inventory

            await show_items_menu(ctx, inventory, title=_("Your inventory"))

    @inventory.command(name="give")
    @checks.channel_enabled()
    async def inv_give(self, ctx: MyContext, target: discord.User, item_name: str):
        """
        Give something to some player.
        """
        _ = await ctx.get_translate_function(user_language=True)
        db_target = await get_from_db(target, as_user=True)

        item = INV_COMMON_ITEMS.get(item_name, None)
        if not item:
            await ctx.send(_("❌ Unknown item."))
            return

        db_target.inventory.append(item)
        await db_target.save()
        await ctx.send(_("👌 Item has been given to {target.name}.", target=target))

    @inventory.command(name="use")
    async def inv_use(self, ctx: MyContext, item_number: int):
        """
        Use one of your items
        """
        _ = await ctx.get_translate_function(user_language=True)

        db_user = await get_from_db(ctx.author, as_user=True)
        db_player = await get_player(ctx.author, ctx.channel)

        try:
            item = db_user.inventory.pop(item_number - 1)
        except IndexError:
            await ctx.send(_('❌ Unknown item number.'))
            return

        item_type = item.get('type')

        if item_type == "lootbox":
            items_given = []
            for item_info_to_give in INV_LOOTBOX_ITEMS[item.get("action")]:
                luck = item_info_to_give.get("luck", 100)
                item_to_give = item_info_to_give.get("item")
                if random.randint(0, 100) <= luck:
                    items_given.append(item_to_give)

            db_user.inventory.extend(items_given)
            await show_items_menu(ctx, items_given, title=_("Lootbox opened"))

        elif item_type == "item":
            if item.get("uses", 1) > 1:
                item["uses"] -= 1
                db_user.inventory.append(item)

            item_action = item.get("action")
            if item_action == "set_vip":
                db_guild = await get_from_db(ctx.guild)
                db_guild.vip = True
                await db_guild.save()
                await ctx.send(_('✨ {guild.name} is now VIP! Thanks.', guild=ctx.guild))
            elif item_action == "add_exp":
                amount = item.get("amount")
                db_player.experience += amount
                await ctx.send(_('✨ You learned a lot, adding {amount} experience points to your profile.', amount=amount))
            elif item_action == "refill_magazines":
                db_player.magazines = 6
                db_player.bullets = 6
                await ctx.send(_('✨ Yay! Free ammo!'))

        await db_user.save()
        await db_player.save()

    @commands.group(aliases=["bp"])
    async def backpack(self, ctx: MyContext):
        """
        Show your backpack content
        """
        if not ctx.invoked_subcommand:
            _ = await ctx.get_translate_function(user_language=True)

            db_player: Player = await get_player(ctx.author, ctx.channel)
            backpack = db_player.backpack
            await show_items_menu(ctx, backpack, title=_("Your backpack on {channel.mention}", channel=ctx.channel))

    @backpack.command(name="give")
    async def bp_give(self, ctx: MyContext, target: discord.User, item_name: str):
        """
        Give something to some player.
        """
        _ = await ctx.get_translate_function(user_language=True)
        db_target = await get_from_db(target, as_user=True)

        item = BP_COMMON_ITEMS.get(item_name, None)
        if not item:
            await ctx.send(_("❌ Unknown item."))
            return

        db_target.inventory.append(item)
        await db_target.save()
        await ctx.send(_("👌 Item has been given to {target.name}.", target=target))

    @backpack.command(name="use")
    async def bp_use(self, ctx: MyContext, item_number: int):
        """
        Use one of your items
        """
        _ = await ctx.get_translate_function(user_language=True)

        db_player = await get_player(ctx.author, ctx.channel)

        try:
            item = db_player.backpack.pop(item_number - 1)
        except IndexError:
            await ctx.send(_('❌ Unknown item number.'))
            return

        await db_player.save()


setup = InventoryCommands.setup
