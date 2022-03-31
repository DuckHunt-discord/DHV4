import asyncio
import time

import statcord
import aiohttp
import datetime
import discord

from aiohttp import web
from discord.ext import commands
from tortoise import timezone

from utils.cog_class import Cog
from typing import Tuple, List
from utils import checks
from utils.ctx_class import MyContext
from utils.inventory_items import Voted
from utils.models import DiscordUser, get_from_db, BotList, Vote, Player


def _(message):
    return message


class BotsListVoting(Cog):
    display_name = _("Voting")
    help_priority = 11
    help_color = 'green'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

    async def cog_load(self):
        self.statcord_api = statcord.Client(self.bot, self.config()['statcord_token'],
                                            custom1=self.statcord_custom_value_ducks_spawned,
                                            custom2=self.statcord_custom_value_players_count)
        self.statcord_api.start_loop()
        self.last_stats_post = 0

    @Cog.listener()
    async def on_command(self, ctx):
        self.statcord_api.command_run(ctx)

    async def statcord_custom_value_ducks_spawned(self):
        return sum(len(v) for v in self.bot.ducks_spawned.values())

    async def statcord_custom_value_players_count(self):
        return await Player.all().count()

    async def get_bot_list(self) -> List[BotList]:
        return await BotList.all()

    async def get_routes(self, route_prefix):
        routes = []

        for bot_list in await self.get_bot_list():
            webhook_key = bot_list.key

            handler_type = bot_list.webhook_handler
            if handler_type == "generic":
                handler = self.votes_generic_hook_factory(bot_list)
            elif handler_type == "top.gg":
                handler = self.votes_topgg_hook
            elif handler_type == "None":
                continue
            else:
                self.bot.logger.error(f"Unknown hook type for {bot_list.name} : {handler_type}")
                continue

            routes.append(('POST', f'{route_prefix}/{webhook_key}/hook', handler))

        return routes

    def votes_generic_hook_factory(self, bot_list: BotList):
        """
        Creates votes handlers for specific bots lists
        """

        async def votes_hook(request: web.Request):
            """
            Handle users votes for fateslist
            """
            auth = request.headers.get(bot_list.webhook_authorization_header, "")
            local_auth = bot_list.webhook_auth or bot_list.auth

            if auth != local_auth:
                self.bot.logger.warning(
                    f"Bad authentification ({auth} vs {local_auth}) provided to {bot_list.name} API.")
                return web.Response(status=401, text="Unauthorized, bad auth")

            post_data = await request.json()

            if '.' not in bot_list.webhook_user_id_json_field:
                user_id = post_data[bot_list.webhook_user_id_json_field]
            else:
                user_id = post_data
                for part in bot_list.webhook_user_id_json_field.split('.'):
                    user_id = user_id[part]

            # This is just to make sure that the ID is an integer
            # Thanks, discordbots.co test webhooks...
            if str(user_id).isdigit():
                user_id = int(user_id)
            elif "test" in user_id.lower():
                return web.Response(status=201, text="Test OK")
            else:
                return web.Response(status=400, text="Bad user ID")

            result, message = await self.handle_vote(user_id, bot_list)

            if result:
                return web.Response(status=200, text=message)
            else:
                return web.Response(status=400, text=message)

        return votes_hook

    async def votes_topgg_hook(self, request: web.Request):
        """
        Handle users votes for top.gg
        """
        bot_list = await BotList.filter(key="top.gg").get()
        auth = request.headers.get("Authorization", "")

        if auth != bot_list.auth:
            self.bot.logger.warning(f"Bad authentification provided to {bot_list.name} API.")
            return web.Response(status=401, text="Unauthorized, bad auth")

        post_data = await request.json()
        user_id = int(post_data["user"])

        bot_id = int(post_data["bot"])

        if bot_id != self.bot.user.id:
            self.bot.logger.warning(f"Bad bot ID ({bot_id}) provided to {bot_list.name} API.")
            return web.Response(status=401, text="Unauthorized, bad bot ID")

        is_test = post_data["type"] == "test"
        is_weekend = post_data["isWeekend"]

        multiplicator = int(is_weekend) + 1

        result, message = await self.handle_vote(user_id, bot_list, multiplicator=multiplicator, is_test=is_test)

        if result:
            return web.Response(status=200, text=message)
        else:
            return web.Response(status=400, text=message)

    async def handle_vote(self, user_id: int, bot_list: BotList, multiplicator: int = 1, is_test: bool = False) -> Tuple[bool, str]:
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.errors.NotFound:
            self.bot.logger.warning(f"Bad user ID provided to votes API {bot_list.name}: {user_id}.")
            return False, "Unauthorized, bad user ID"

        db_user: DiscordUser = await get_from_db(user)

        vote = Vote(user=db_user, bot_list=bot_list, multiplicator=multiplicator)

        if not is_test:
            self.bot.logger.info(f"{multiplicator} vote(s) recorded for {user.name}#{user.discriminator} on {bot_list.name}.")
            await vote.save()
            await Voted.give_to(db_user)
            await db_user.save()
        else:
            self.bot.logger.warning(f"{multiplicator} test vote(s) received for {user.name}#{user.discriminator}. Not saved.")

        try:
            await user.send(f"✨ Thanks for voting for DuckHunt on {bot_list.name}! "
                            f"Check your inventory with `dh!inv` in a game channel.")
        except discord.errors.Forbidden:
            pass

        return True, "Vote recorded"

    async def can_vote(self, bot_list: BotList, user: discord.User, db_user: DiscordUser):
        vote_check_url = bot_list.check_vote_url
        vote_every = bot_list.vote_every

        if not bot_list.can_vote:
            return False
        elif not vote_check_url and vote_every:
            last_vote = await Vote.filter(user=db_user, bot_list=bot_list).order_by('-at').first()

            if last_vote:
                # We wait for five more minutes just in case clocks desync'ed
                if timezone.now() > (last_vote.at + vote_every + datetime.timedelta(minutes=5)):
                    return True
                else:
                    return False
            else:
                # Never voted
                return True

        elif not vote_check_url:
            return None
        else:
            timeout = aiohttp.ClientTimeout(total=5)
            headers = {'accept': 'application/json', "Authorization": bot_list.auth}
            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list.name}")
            try:
                async with self.bot.client_session.get(vote_check_url.format(user=user), timeout=timeout, headers=headers) as resp:
                    json_resp = await resp.json()
            except (asyncio.TimeoutError, aiohttp.ContentTypeError):
                self.bot.logger.warning(f"Checking user {user.id} vote on {bot_list.name} -> The bot list seems down.")

                return False  # Can't vote if the bot list is down

            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list.name} -> {json_resp}")

            if '.' not in bot_list.check_vote_key:
                voted_resp = str(json_resp.get(bot_list.check_vote_key))
            else:
                voted_resp = json_resp
                for part in bot_list.check_vote_key.split('.'):
                    voted_resp = json_resp[part]

            if voted_resp.isdigit():
                voted = bool(int(voted_resp))
            elif voted_resp.lower() == "true":
                voted = True
            elif voted_resp.lower() == "false":
                voted = False
            else:
                self.bot.logger.warning(f"Unknown response for {bot_list.name} votechecking: {voted_resp}")
                voted = False

            if bot_list.check_vote_negate:
                return not voted
            else:
                return voted

    async def get_votable_lists(self, user: discord.User) -> Tuple[List[BotList], List[BotList], List[BotList]]:
        votable_lists = []
        maybe_lists = []
        nope_lists = []

        db_user = await get_from_db(user, as_user=True)

        for bot_list in await self.get_bot_list():
            res = await self.can_vote(bot_list, user, db_user)
            if res is True:
                votable_lists.append(bot_list)
            elif res is None:
                maybe_lists.append(bot_list)
            else:
                nope_lists.append(bot_list)

        return votable_lists, maybe_lists, nope_lists

    @commands.command()
    @checks.channel_enabled()
    async def vote(self, ctx: MyContext):
        """
        Sends the link you can use to vote for DuckHunt on bot lists
        """
        _ = await ctx.get_translate_function()

        m = await ctx.reply(_("Please wait while I check where you can vote..."))

        async with ctx.typing():
            votable_lists, maybe_lists, nope_lists = await self.get_votable_lists(ctx.author)

            embed = discord.Embed()

            if votable_lists:
                text = votable_lists[0].vote_url
                embed.title = _("You can vote !")
                embed.description = _("Thanks for supporting the bot by voting !")
                embed.url = votable_lists[0].vote_url
                embed.colour = discord.Colour.green()
            elif maybe_lists:
                text = maybe_lists[0].vote_url
                embed.title = _("You might be able to vote !")
                embed.description = _("Thanks for supporting the bot by voting as much as you can. It makes a difference !")
                embed.url = maybe_lists[0].vote_url
                embed.colour = discord.Colour.orange()
            else:
                text = _("Oh no! No bot list is currently available for you to vote.")
                embed.title = _("There is nowhere for you to vote at the time !")
                embed.description = _("Thanks for supporting the bot. It makes a difference! \n"
                                      "Unfortunately, you voted everywhere you could for now, but you can check back in a few hours.")
                embed.colour = discord.Colour.red()

            click_me_to_vote = _("Click me to vote")
            for bot_list in votable_lists:
                embed.add_field(name=_("You can vote on {bl_name}", bl_name=bot_list.name),
                                value=f"[{click_me_to_vote}]({bot_list.vote_url})", inline=False)

            for bot_list in maybe_lists:
                embed.add_field(name=_("You might be able to vote on {bl_name}", bl_name=bot_list.name),
                                value=f"[{click_me_to_vote}]({bot_list.vote_url})", inline=True)

            await m.edit(embed=embed, content=text)

    @Cog.listener("on_guild_join")
    @Cog.listener("on_guild_remove")
    @Cog.listener("on_ready")
    async def post_stats(self, *args, **kwargs):
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)
        await self.bot.wait_until_ready()

        if int(time.time()) - self.last_stats_post < 30 * 60:
            return "Can't post stats more than twice per hour."
        else:
            self.last_stats_post = int(time.time())

        self.bot.logger.debug(f"Updating stats on bots list")

        server_count = len(self.bot.guilds)
        shard_count = self.bot.shard_count

        for bot_list in await self.get_bot_list():
            stats_url = bot_list.post_stats_url
            if stats_url:
                timeout = aiohttp.ClientTimeout(total=5)
                headers = {'Content-Type': 'application/json',
                           'accept': 'application/json',
                           "Authorization": bot_list.auth}
                post_data = {}
                method = bot_list.post_stats_method

                post_stats_server_count_key = bot_list.post_stats_server_count_key
                if "." in post_stats_server_count_key:
                    keys = list(reversed(post_stats_server_count_key.split('.')))

                    # FIXME : This is fragile, and will not merge multiple dicts together.
                    #  Why the fuck are bot lists so fucking complicated 😢
                    mydict = {
                        keys[0]: server_count
                    }

                    for key in keys[1:]:
                        mydict = {
                            key: mydict
                        }

                    post_data = {**post_data, **mydict}

                elif post_stats_server_count_key:
                    post_data[post_stats_server_count_key] = server_count

                post_stats_shard_count_key = bot_list.post_stats_shard_count_key
                if post_stats_shard_count_key:
                    post_data[post_stats_shard_count_key] = shard_count
                try:
                    if method == "POST":
                        resp = await self.bot.client_session.post(stats_url, timeout=timeout, headers=headers, json=post_data)
                    elif method == "PATCH":
                        resp = await self.bot.client_session.patch(stats_url, timeout=timeout, headers=headers, json=post_data)
                    elif method == "None":
                        continue
                    else:
                        self.bot.logger.error(f"Unknown HTTP method to post stats on {bot_list.name}: {method}")
                except asyncio.TimeoutError:
                    self.bot.logger.warning(f"Push stats to {bot_list.name}: resp [TIMEOUT]")
                else:
                    text = (await resp.text())[:100]
                    status = resp.status
                    if status in [200, 204]:
                        self.bot.logger.debug(f"Pushed stats to {bot_list.name} : resp [{status}] {text}")
                    else:
                        self.bot.logger.warning(f"Pushed stats to {bot_list.name} : resp [{status}] {text}")


setup = BotsListVoting.setup
