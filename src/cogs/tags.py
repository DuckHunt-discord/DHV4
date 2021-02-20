"""
Tags are snippet of text that can be used to quickly send a message.
"""
import discord
from discord.ext import commands, menus

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import AccessLevel, Tag, get_tag, get_from_db


class TagName(commands.clean_content):
    async def convert(self, ctx, argument):
        converted = await super().convert(ctx, argument)
        lower = converted.lower().strip()

        if not lower:
            raise commands.BadArgument('Missing tag name.')

        if len(lower) > 90:
            raise commands.BadArgument('Tag name is a maximum of 90 characters.')

        return lower


class TagMenuSource(menus.ListPageSource):
    def __init__(self, ctx: MyContext, tag: Tag):
        self.ctx = ctx
        self.tag = tag

        data = tag.content.split('\n---\n')
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entry):
        _ = await self.ctx.get_translate_function(user_language=True)
        e = discord.Embed()
        e.title = self.tag.name.title()

        if len(entry) == 0:
            entry = " "

        e.description = entry

        return e


async def show_tag_embed(ctx: MyContext, tag: Tag):
    pages = menus.MenuPages(source=TagMenuSource(ctx, tag), clear_reactions_after=True)
    await pages.start(ctx)


class Tags(Cog):
    @commands.command(aliases=["t"])
    async def tag(self, ctx: MyContext, *, tag_name:TagName):
        tag = await get_tag(tag_name)

        await show_tag_embed(ctx, tag)

    @commands.group()
    async def tags(self, ctx: MyContext):
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def create(self, ctx: MyContext, tag_name: TagName, *, tag_content):
        _ = await ctx.get_translate_function()
        tag = await get_tag(tag_name)
        if tag:
            await ctx.reply(_("❌ This tag already exists."))
        else:
            db_user = await get_from_db(ctx.author, as_user=True)
            tag = Tag(name=tag_name, content=tag_content, owner=db_user)

            await tag.save()
            await ctx.reply(_("👌 Tag created: {tag.name} ({tag.pk})", tag=tag))

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def alias(self, ctx: MyContext, alias_name: TagName, tag_name: TagName):
        await ctx.reply("Not yet implemented.")

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def edit(self, ctx: MyContext, tag_name: TagName, *, tag_content):
        await ctx.reply("Not yet implemented.")

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def raw(self, ctx: MyContext, tag_name: TagName):
        await ctx.reply("Not yet implemented.")

    @tags.command()
    async def url(self, ctx: MyContext, tag_name: TagName):
        await ctx.reply("Not yet implemented.")


setup = Tags.setup
