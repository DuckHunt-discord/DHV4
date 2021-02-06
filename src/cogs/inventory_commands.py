import asyncio
import random

import discord
from discord.ext import commands
from discord.ext import menus

from utils import checks, models
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.ducks import spawn_random_weighted_duck
from utils.models import get_from_db, get_player, DiscordUser, Player


def _(s):
    return s


INV_COMMON_ITEMS = {
    'welcome_package':
        {"type": "lootbox", "action": "welcome", "name": _("A welcome gift"), "description": _("Open it in your inventory")},
    'foie_gras':
        {"type": "lootbox", "action": "foie_gras", "name": _("A clean box of foie gras"), "description": _("The boss dropped that when he died")},
    'vip_card':
        {"type": "item", "action": "set_vip", "uses": 1, "name": _("VIP Card"), "description": _("A nice and shiny card that allow you to set a server as VIP.")},
    'boost_exp':
        {"type": "item", "action": "add_exp", "uses": 1, "amount": 35, "name": _("A book"), "description": _("Reading it will give you experience")},
    'spawn_ducks':
        {"type": "item", "action": "spawn_ducks", "uses": 1, "name": _("A good ol' egg"), "description": _("Crack it open !")},
    'refill_magazines':
        {"type": "item", "action": "refill_magazines", "uses": 1, "name": _("A free card for magazines"), "description": _("Redeem it to refill your weapon.")},
}

INV_LOOTBOX_ITEMS = {
    'welcome':
        [
            {"luck": 100, "item": INV_COMMON_ITEMS['boost_exp']},
            {"luck": 100, "item": INV_COMMON_ITEMS['refill_magazines']},
        ],
    'foie_gras':
        [
            {"luck": 35, "item": INV_COMMON_ITEMS['boost_exp']},
            {"luck": 100, "item": INV_COMMON_ITEMS['refill_magazines']},
            {"luck": 10, "item": INV_COMMON_ITEMS['spawn_ducks']},
        ],
    'fois_gras':
        [
            {"luck": 35, "item": INV_COMMON_ITEMS['boost_exp']},
            {"luck": 100, "item": INV_COMMON_ITEMS['refill_magazines']},
            {"luck": 10, "item": INV_COMMON_ITEMS['spawn_ducks']},
        ],
    'vote':
        [
            {"luck": 5, "item": INV_COMMON_ITEMS['boost_exp']},
            {"luck": 100, "item": INV_COMMON_ITEMS["refill_magazines"]},
        ],
}


class ItemsMenusSource(menus.ListPageSource):
    def __init__(self, ctx: MyContext, data, title, numbers):
        super().__init__(data, per_page=6)
        self.ctx = ctx
        self.title = title
        self.numbers = numbers

    async def format_page(self, menu, entries):
        _ = await self.ctx.get_translate_function(user_language=True)
        e = discord.Embed()
        e.title = self.title
        offset = menu.current_page * self.per_page

        for i, item in enumerate(entries, start=offset):
            uses = item.get("uses", 1)
            if uses > 1:
                uses_str = f"{uses}x "
            else:
                uses_str = ""

            if self.numbers:
                e.add_field(name=f"**{i + 1}** - {uses_str}" + _(item["name"]), value=_(item["description"]), inline=False)
            else:
                e.add_field(name=f"- {uses_str}" + _(item["name"]), value=_(item["description"]), inline=False)

        if not entries:
            e.description = _("A lot of air and a starved mosquito.")

        return e


async def show_items_menu(ctx, items, title: str, numbers=True):
    pages = menus.MenuPages(source=ItemsMenusSource(ctx, items, title, numbers=numbers), clear_reactions_after=True)
    await pages.start(ctx)


class InventoryCommands(Cog):
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
            inventory = db_user.inventory

            await show_items_menu(ctx, inventory, title=_("Your inventory"))

    @inventory.command(name="give")
    @checks.needs_access_level(models.AccessLevel.BOT_MODERATOR)
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

    @inventory.command(name="use", aliases=["open"])
    async def inv_use(self, ctx: MyContext, item_number: int):
        """
        Use one of the items in your inventory.
        """
        _ = await ctx.get_translate_function(user_language=True)

        db_user = await get_from_db(ctx.author, as_user=True)
        db_player = await get_player(ctx.author, ctx.channel)
        db_channel = await get_from_db(ctx.channel)

        if not db_channel.allow_global_items:
            await ctx.send(_('❌ Items usage is disabled on this channel.'))
            return

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
            await show_items_menu(ctx, items_given, title=_("Lootbox opened"), numbers=False)

        elif item_type == "item":
            if item.get("uses", 1) > 1:
                item["uses"] -= 1
                db_user.inventory.append(item)

            item_action = item.get("action")
            if item_action == "set_vip":
                db_guild = await get_from_db(ctx.guild)
                if db_guild.vip:
                    await ctx.send(_('❌ {guild.name} is already VIP.', guild=ctx.guild))
                    return
                db_guild.vip = True
                await db_guild.save()
                await ctx.send(_('✨ {guild.name} is now VIP! Thanks.', guild=ctx.guild))
            elif item_action == "add_exp":
                amount = item.get("amount")
                await db_player.edit_experience_with_levelups(ctx, amount)

                await ctx.send(_('✨ You learned a lot, adding {amount} experience points to your profile.', amount=amount))
            elif item_action == "refill_magazines":
                level_info = db_player.level_info()
                db_player.magazines = level_info['magazines']
                db_player.bullets = level_info['bullets']
                await ctx.send(_('✨ Yay! Free ammo!'))
            elif item_action == "spawn_ducks":
                for i in range(2):
                    await spawn_random_weighted_duck(self.bot, ctx.channel)

                await ctx.send(_('✨ Oh look, ducks! Ducks are everywhere!'))

        await db_user.save()
        await db_player.save()


setup = InventoryCommands.setup
