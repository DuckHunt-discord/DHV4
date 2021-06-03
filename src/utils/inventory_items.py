import abc
import random
import typing
import discord

from utils.ctx_class import MyContext
from utils.ducks import spawn_random_weighted_duck
from utils.models import UserInventory, DiscordUser, get_user_inventory, get_from_db, get_player


class InvalidUsesCount(Exception):
    pass


class NotInInventory(Exception):
    pass


def _(s):
    return s


# Abstract base classes

class Item(abc.ABC):
    name: str = ""
    description: str = ""
    _shortcode: str = None

    db_name: str = ""

    def __init__(self, inventory: UserInventory, uses=1):
        self.inventory = inventory
        self.uses = uses

    @property
    def shortcode(self):
        return self.get_shortcode()

    @classmethod
    def get_shortcode(cls):
        return cls._shortcode or cls.db_name.replace(" ", "_").lower()

    def is_in_inventory(self):
        """
        Check if a item is in a given inventory
        """
        return self.count_in_inventory() >= self.uses

    def count_in_inventory(self):
        """
        Count uses of the item in a given inventory
        """
        return getattr(self.inventory, self.db_name + "_left")

    async def add_to_inventory(self):
        """
        Adds (one use of) the item to an inventory. Doesn't save the given inventory.
        """
        setattr(self.inventory, self.db_name + "_left", getattr(self.inventory, self.db_name + "_left") + self.uses)

    async def remove_from_inventory(self):
        """
        Removes (one use of) the item from an inventory. Doesn't save the given inventory.
        """
        setattr(self.inventory, self.db_name + "_left", getattr(self.inventory, self.db_name + "_left") - self.uses)

    async def delete_from_inventory(self):
        """
        Removes the item from an inventory. Doesn't save the given inventory.
        """
        setattr(self.inventory, self.db_name + "_left", 0)

    @abc.abstractmethod
    async def use_item(self, ctx: MyContext, *,
                       db_user=None, db_guild=None, db_channel=None, db_member=None, db_player=None):
        """
        Use the given item in a given context channel. Accept db_* to avoid duplicate queries,
        and to save the objects.
        """
        await self.remove_from_inventory()
        await self.inventory.save()

    @classmethod
    async def give_to(cls, user: typing.Union[UserInventory, DiscordUser, discord.User, discord.Member], **kwargs):
        """
        Convenience method to give the item to a user
        """
        if isinstance(user, UserInventory):
            inventory = user
        else:
            inventory = await get_user_inventory(user)
        item = cls(inventory, **kwargs)
        await item.add_to_inventory()

        await inventory.save()

    @classmethod
    async def use_by(cls, ctx: MyContext, user: typing.Union[UserInventory, DiscordUser, discord.User, discord.Member] = None, uses: int = 1, **kwargs):
        """
        Convenience method to make a user use the item
        """
        if user is None:
            user = ctx.author

        if isinstance(user, UserInventory):
            inventory = user
        else:
            inventory = await get_user_inventory(user)
        item = cls(inventory, uses=uses)
        if item.is_in_inventory():
            await item.use_item(ctx, **kwargs)
        else:
            raise NotInInventory()


class Lootbox(Item):
    items_inside: typing.Tuple[typing.Type[Item], int, int] = [
        # (ItemCls, luck, uses)
    ]

    async def get_items_to_give(self) -> typing.List[Item]:
        given = []
        for ItemCls, luck, uses in self.items_inside:
            uses = sum([int(random.randint(0, 99) < luck) for i in range(uses * self.uses)])

            if uses != 0:
                given.append(ItemCls(self.inventory, uses=uses))

        return given

    async def use_item(self, ctx: MyContext, **kwargs):
        """
        Use the given item in a given context channel. Accept db_user and db_channel to avoid duplicate queries,
        and to save the objects.
        """
        _ = await ctx.get_translate_function(user_language=True)
        embed = discord.Embed(title=_('Lootbox opened'))
        description = []

        items = await self.get_items_to_give()
        for item in items:
            await item.add_to_inventory()
            item_name = _(item.name)
            item_desc = _(item.description)
            item_uses = item.uses
            description.append(f"**{item_uses}x {item_name}**\n{item_desc}")

        await super().use_item(ctx, **kwargs)

        if len(description) > 0:
            embed.description = "\n\n".join(description)
        else:
            embed.description = _("A lot of air and a starved mosquito.")

        await ctx.reply(embed=embed)


# Items


class VipCard(Item):
    name: str = _("VIP card")
    description: str = _("A nice and shiny card that allow you to set a server as VIP.")
    _shortcode: str = "vip"

    db_name: str = "item_vip_card"

    async def use_item(self, ctx: MyContext, db_guild=None, **kwargs):
        if self.uses != 1:
            raise InvalidUsesCount()

        _ = await ctx.get_translate_function(user_language=True)
        db_guild = db_guild or await get_from_db(ctx.guild)

        if db_guild.vip:
            await ctx.send(_('❌ {guild.name} is already VIP.', guild=ctx.guild))
            return False

        await super().use_item(ctx, db_guild=db_guild, **kwargs)
        db_guild.vip = True
        await db_guild.save()
        await ctx.send(_('✨ {guild.name} is now VIP! Thanks.', guild=ctx.guild))


class Book(Item):
    name: str = _("A book")
    description: str = _("Reading it will give you experience.")
    _shortcode: str = "book"

    db_name: str = "item_norm_exp_boost"
    item_exp_amount = 35

    async def use_item(self, ctx: MyContext, db_player=None, **kwargs):
        db_player = db_player or await get_player(ctx.author, ctx.channel)
        await super().use_item(ctx, db_player=db_player, **kwargs)
        _ = await ctx.get_translate_function(user_language=True)
        amount = self.uses * self.item_exp_amount

        await db_player.edit_experience_with_levelups(ctx, amount)
        await db_player.save()
        await ctx.send(_('✨ You learned a lot, adding {amount} experience points to your profile.', amount=amount))


class ForeignBook(Book):
    name: str = _("A book in a foreign language")
    description: str = _("Can you read it ?")
    _shortcode: str = "foreign_book"

    db_name: str = "item_mini_exp_boost"
    item_exp_amount = 15


class Encyclopedia(Book):
    name: str = _("An encyclopedia")
    description: str = _("Reading it will give you a lot of experience ?")
    _shortcode: str = "encyclo"

    db_name: str = "item_maxi_exp_boost"
    item_exp_amount = 75


class Bullet(Item):
    name: str = _("A bullet")
    description: str = _("This is just a normal bullet, but it might help you to get that special achievement.")
    _shortcode: str = "bullet"

    db_name: str = "item_one_bullet"

    async def use_item(self, ctx: MyContext, db_player=None, **kwargs):
        db_player = db_player or await get_player(ctx.author, ctx.channel)
        await super().use_item(ctx, db_player=db_player, **kwargs)
        _ = await ctx.get_translate_function(user_language=True)

        db_player.bullets += self.uses
        await db_player.save()
        await ctx.send(_('✨ Oh, is this a bullet ?'))


class Egg(Item):
    name: str = _("A good ol' egg")
    description: str = _("Crack it open !")
    _shortcode: str = "egg"

    db_name: str = "item_spawn_ducks"

    async def use_item(self, ctx: MyContext, db_channel=None, **kwargs):
        if self.uses >= 5:
            raise InvalidUsesCount()

        _ = await ctx.get_translate_function(user_language=True)
        await super().use_item(ctx, db_channel=db_channel, **kwargs)

        for i in range(self.uses * 2):
            await spawn_random_weighted_duck(ctx.bot, ctx.channel, db_channel=db_channel)

        await ctx.send(_('✨ Oh look, ducks! Ducks are everywhere!'))


class RefillMagazines(Item):
    name: str = _("A free card for magazines")
    description: str = _("Redeem it to refill your weapon.")
    _shortcode: str = "mags"

    db_name: str = "item_refill_magazines"

    async def use_item(self, ctx: MyContext, db_player=None, **kwargs):
        if self.uses != 1:
            raise InvalidUsesCount()

        _ = await ctx.get_translate_function(user_language=True)

        db_player = db_player or await get_player(ctx.author, ctx.channel)

        level_info = db_player.level_info()

        mags, bullets = db_player.magazines, db_player.bullets
        new_mags, new_bullets = level_info['magazines'], level_info['bullets']

        if mags < new_mags or bullets < new_bullets:
            await super().use_item(ctx, db_player=db_player, **kwargs)
            db_player.magazines = max(mags, new_mags)
            db_player.bullets = max(bullets, new_bullets)
            await db_player.save()
            await ctx.send(_('✨ Yay! Free ammo!'))
        else:
            await ctx.send(_('❌ Your ammo is already full!'))


# Lootboxes
class WelcomePackage(Lootbox):
    name: str = _("A welcome gift")
    description: str = _("Open it in your inventory")
    _shortcode: str = "welcome"

    db_name: str = "lootbox_welcome"
    items_inside = [
        (Book,            100, 1),
        (RefillMagazines, 100, 1),
    ]


class FoieGras(Lootbox):
    name: str = _("A clean box of foie gras")
    description: str = _("The boss dropped that when he died")
    _shortcode: str = "foie"

    db_name: str = "lootbox_boss"
    items_inside = [
        (Encyclopedia,      1, 1),
        (Book,             20, 1),
        (ForeignBook,      45, 1),
        (RefillMagazines, 100, 1),
        (Egg,              10, 1),
    ]


class Voted(Lootbox):
    name: str = _("A little something for helping the bot")
    description: str = _("Thanks for voting for DuckHunt")
    _shortcode: str = "vote"

    db_name: str = "lootbox_vote"
    items_inside = [
        (RefillMagazines, 3, 2),
        (Encyclopedia,    1, 1),
        (Book,            2, 1),
        (ForeignBook,    10, 1),
        (Bullet,        100, 1),
    ]


ITEMS: typing.List[typing.Type[Item]] = [VipCard, Book, ForeignBook, Encyclopedia, Bullet, Egg, RefillMagazines]
LOOTBOXES: typing.List[typing.Type[Item]] = [WelcomePackage, FoieGras, Voted]

ALL_INVENTORY: typing.List[typing.Type[Item]] = LOOTBOXES + ITEMS

ITEMS_SHORTCODE: typing.Dict[str, typing.Type[Item]] = {_Item.get_shortcode(): _Item for _Item in ITEMS}
LOOTBOXES_SHORTCODE: typing.Dict[str, typing.Type[Item]] = {_Lootbox.get_shortcode(): _Lootbox for _Lootbox in LOOTBOXES}

ALL_SHORTCODE: typing.Dict[str, typing.Type[Item]] = {**ITEMS_SHORTCODE, **LOOTBOXES_SHORTCODE}
