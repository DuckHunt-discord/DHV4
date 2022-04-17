from discord.ext import commands
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.random_ducks import get_random_duck_file


def _(message):
    return message


class RandomDucks(Cog):
    display_name = _("Images")
    help_priority = 10

    @commands.command(aliases=["rd"])
    async def random_duck(self, ctx: MyContext, artist="Calgeka", debug=False, with_background=True):
        """
        Shows a random duck image, courtesy of Globloxmen assets.
        This is mostly used to debug the random duck functions,
        and uses the same pipeline as for the random duck avatars.

        You can specify if you want a background or not for your random duck, and it defaults to yes.
        """
        _ = await ctx.get_translate_function()
        artist = artist.title()
        if artist not in ["Calgeka", "Globloxmen"]:
            await ctx.send(_("That artist is not known. Choose either Calgeka or Globloxmen."))
            return

        async with ctx.typing():
            file, debug_data = await get_random_duck_file(self.bot, artist, with_background)
            if debug:
                show_lines = []
                for dir_name, image_name in debug_data:
                    dir_no_num = dir_name.split(' - ')[1]
                    image_no_ext = image_name.replace('.png', '')
                    if len(show_lines) == 0:
                        show_lines.append(f"  {dir_no_num} ({image_no_ext})")
                    else:
                        show_lines.append(f"+ {dir_no_num} ({image_no_ext})")

                await ctx.reply(content="```\n" + "\n".join(show_lines) + "\n```", file=file)
            else:
                await ctx.reply(file=file)


setup = RandomDucks.setup
