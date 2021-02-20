"""
Tags are snippet of text that can be used to quickly send a message.
"""
import discord
from discord.ext import commands, menus

from utils import checks
from utils.checks import BotIgnore
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import AccessLevel, Tag, get_tag, get_from_db, TagAlias


class TagName(commands.clean_content):
    async def convert(self, ctx, argument):
        converted = await super().convert(ctx, argument)
        lower = converted.lower().strip()

        if not lower:
            raise commands.BadArgument('Missing tag name')

        if " " in lower:
            raise commands.BadArgument("Tags names can't contain spaces")

        if len(lower) > 90:
            raise commands.BadArgument('Tag name is a maximum of 90 characters')

        return lower


class TagMenuSource(menus.ListPageSource):
    def __init__(self, ctx: MyContext, tag: Tag):
        self.ctx = ctx
        self.tag = tag

        data = [s.strip(" \n") for s in tag.content.split('\n\n---')]
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entry):
        _ = await self.ctx.get_translate_function(user_language=True)
        e = discord.Embed()
        e.title = self.tag.name.title()
        e.url = f"https://duckhunt.me/tags/{self.tag.name}"

        if len(entry) == 0:
            entry = " "

        # Embed the image directly
        lines = entry.splitlines()
        last_line = lines[-1]
        if last_line.endswith(".jpg") or last_line.endswith(".png") or last_line.endswith(".gif"):
            if last_line.startswith("https://") and not " " in last_line:
                e.set_image(url=last_line)
                entry = "\n".join(lines[:-1])

        e.description = entry

        return e


async def show_tag_embed(ctx: MyContext, tag: Tag):
    pages = menus.MenuPages(source=TagMenuSource(ctx, tag), clear_reactions_after=True)
    await pages.start(ctx)


class Tags(Cog):
    async def cog_check(self, ctx: MyContext):
        if ctx.guild and ctx.guild.id in self.config()['allowed_in_guilds']:
            return True
        else:
            # Raise BotIgnore to fail silently.
            raise BotIgnore()

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
        tag = await get_tag(tag_name, increment_uses=False)
        if tag:
            await ctx.reply(_("❌ This tag already exists."))
        else:
            db_user = await get_from_db(ctx.author, as_user=True)
            tag = Tag(name=tag_name, content=tag_content, owner=db_user)

            await tag.save()
            await ctx.reply(_("👌 Tag created: {tag.name} (`{tag.pk}`)", tag=tag))

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def alias(self, ctx: MyContext, alias_name: TagName, tag_name: TagName):
        _ = await ctx.get_translate_function()
        alias_tag = await get_tag(alias_name, increment_uses=False)
        if alias_tag:
            await ctx.reply(_("❌ This tag already exists."))
            return

        target_tag = await get_tag(tag_name, increment_uses=False)

        if not target_tag:
            await ctx.reply(_("❌ This tag doesn't exist."))
            return

        db_user = await get_from_db(ctx.author, as_user=True)
        tag_alias = TagAlias(owner=db_user, tag=target_tag, name=alias_name)
        await tag_alias.save()

        await ctx.reply(_("👌 Alias created: {tag_alias.name} -> {tag_alias.tag.name} (`{tag_alias.pk}`)", tag=tag_alias))

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def edit(self, ctx: MyContext, tag_name: TagName, *, tag_content):
        _ = await ctx.get_translate_function()

        tag = await get_tag(tag_name, increment_uses=False)
        if not tag:
            await ctx.reply(_("❌ This tag doesn't exist yet. You might want to create it."))
            return

        tag.content = tag_content
        tag.revisions += 1
        await tag.save()
        await ctx.reply(_("👌 Tag {tag.name} edited.", tag=tag))

    @tags.command()
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def raw(self, ctx: MyContext, *, tag_name: TagName):
        _ = await ctx.get_translate_function()

        tag = await get_tag(tag_name)

        if not tag:
            await ctx.reply(_("❌ This tag doesn't exist yet. You might want to create it."))
            return

        escaped_content = discord.utils.escape_markdown(tag.content)

        await ctx.reply(escaped_content)


setup = Tags.setup
