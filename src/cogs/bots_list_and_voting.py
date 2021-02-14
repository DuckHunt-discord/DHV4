import asyncio
import time

import aiohttp
from aiohttp import web
from discord.ext import commands

from utils.cog_class import Cog
import datetime
from typing import Tuple, Dict, Any, List

import discord

from utils import config, checks
from cogs.inventory_commands import INV_COMMON_ITEMS
from utils.ctx_class import MyContext
from utils.models import DiscordUser, get_from_db

config = config.load_config()["bot_lists"]


class BotsListVoting(Cog):
    async def get_bot_dict(self) -> Dict[str, Dict[str, Any]]:
        BOTS_DICT = {
            "top_gg": {
                # **Generic data**
                # The name of the bot list
                "name": "top.gg",
                # URL for the main bot page
                "bot_url": "https://top.gg/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["topgg_shared_secret"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://top.gg/bot/187636089073172481/vote",
                # And how often
                "vote_every": datetime.timedelta(hours=12),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": "https://top.gg/api/bots/187636089073172481/check?userId={user.id}",
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": "voted",
                # Does the boolean says if the user has voted (True) or if he can vote (False) ?
                "check_vote_negate": True,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_topgg_hook,
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "topgg",
                # Secret used for authentication of the webhooks messages if not the same the auth token
                # "webhook_auth": "",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://top.gg/api/bots/187636089073172481/stats",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "server_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": "shard_count",
            },
            "discord_bots_gg": {
                # **Generic data**
                # The name of the bot list
                "name": "discord.bots.gg",
                # URL for the main bot page
                "bot_url": "https://discord.bots.gg/bots/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["discordbotsgg_api_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": False,

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://discord.bots.gg/api/v1/bots/187636089073172481/stats",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "guildCount",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": "shardCount",
            },
            "discordbotslist": {
                # **Generic data**
                # The name of the bot list
                "name": "Discord Bots List",
                # URL for the main bot page
                "bot_url": "https://discordbotlist.com/bots/duckhunt",
                # Token to authenticate requests to and from the website
                "auth": config["discordbotlist_api_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://discordbotlist.com/bots/duckhunt/upvote",
                # And how often
                "vote_every": datetime.timedelta(hours=12),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": None,
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": None,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("discordbotslist"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "discordbotslist",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://discordbotlist.com/api/v1/bots/187636089073172481/stats",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "guilds",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": None,
            },
            "fateslist": {
                # **Generic data**
                # The name of the bot list
                "name": "Fateslist",
                # URL for the main bot page
                "bot_url": "https://fateslist.xyz/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["fateslist_api_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://fateslist.xyz/bot/187636089073172481/vote",
                # And how often
                "vote_every": datetime.timedelta(hours=8),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": "https://fateslist.xyz/api/bots/187636089073172481/votes?user_id={user.id}",
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": "vote_right_now",
                # Does the boolean says if the user has voted (True) or if he can vote (False) ?
                "check_vote_negate": False,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("fateslist"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "fateslist",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://fateslist.xyz/api/bots/187636089073172481/stats",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "guild_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": "shard_count",
            },
            "botsfordiscord": {
                # **Generic data**
                # The name of the bot list
                "name": "Bots For Discord",
                # URL for the main bot page
                "bot_url": "https://botsfordiscord.com/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["botsfordiscord_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://botsfordiscord.com/bot/187636089073172481/vote",
                # And how often
                "vote_every": datetime.timedelta(days=1),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": None,
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": None,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("botsfordiscord", user_id_json_field="user"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "botsfordiscord",
                # Secret used for authentication of the webhooks messages if not the same the auth token
                "webhook_auth": config["botsfordiscord_token"][:60],

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://botsfordiscord.com/api/bot/187636089073172481",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "server_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": None,
            },
            "discordboats": {
                # **Generic data**
                # The name of the bot list
                "name": "Discord Boats",
                # URL for the main bot page
                "bot_url": "https://discord.boats/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["discordboats_api_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://discord.boats/bot/187636089073172481/vote",
                # And how often
                "vote_every": datetime.timedelta(hours=12),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": "https://discord.boats/api/bot/187636089073172481/voted?id={user.id}",
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": "voted",
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("discordboats", user_id_json_field="user.id"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "discordboats",
                # Secret used for authentication of the webhooks messages if not the same the auth token
                # "webhook_auth": "",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://discord.boats/api/bot/187636089073172481",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "server_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": None,
            },
            "botlistspace": {
                # **Generic data**
                # The name of the bot list
                "name": "botlist.space",
                # URL for the main bot page
                "bot_url": "https://botlist.space/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["botlist_space_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://botlist.space/bot/187636089073172481/upvote",
                # And how often
                "vote_every": datetime.timedelta(days=1),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": None,
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": "voted",
                # Does the boolean says if the user has voted (True) or if he can vote (False) ?
                "check_vote_negate": True,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("botlistspace", user_id_json_field="user.id"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "botlistspace",
                # Secret used for authentication of the webhooks messages if not the same the auth token
                # "webhook_auth": "",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://api.botlist.space/v1/bots/187636089073172481",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "server_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": None,
            },
            "discordextremelist": {
                # **Generic data**
                # The name of the bot list
                "name": "Discord Extreme List",
                # URL for the main bot page
                "bot_url": "https://discordextremelist.xyz/en-US/bots/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["discordextremelist_token"],

                # **Votes**
                # Can people vote on that bot list ?
                # They can, but only once, so let's say they can't because I can't be bothered
                "can_vote": False,

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://api.discordextremelist.xyz/v2/bot/187636089073172481/stats",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "guildCount",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": "shardCount",
            },
            "voidbots": {
                # **Generic data**
                # The name of the bot list
                "name": "Void Bots",
                # URL for the main bot page
                "bot_url": "https://voidbots.net/bot/187636089073172481",
                # Token to authenticate requests to and from the website
                "auth": config["voidbots_token"],

                # **Votes**
                # Can people vote on that bot list ?
                "can_vote": True,
                # If they can vote, on what URL ?
                "vote_url": "https://voidbots.net/bot/187636089073172481/vote",
                # And how often
                "vote_every": datetime.timedelta(hours=12),
                # Is there a URL the bot can query to see if some `user` has voted recently
                "check_vote_url": "https://api.voidbots.net/bot/voted/187636089073172481/{user.id}",
                # What is the key used to specify the vote in the JSON returned by the URL above ?
                "check_vote_key": "voted",
                # Does the boolean says if the user has voted (True) or if he can vote (False) ?
                "check_vote_negate": True,
                # What is the function that'll receive the request from the vote hooks
                "webhook_handler": self.votes_generic_hook_factory("voidbots", user_id_json_field="user"),
                # What's the key in the URL https://duckhunt.me/api/votes/{key}/hook
                "webhook_key": "voidbots",
                # Secret used for authentication of the webhooks messages if not the same the auth token
                # "webhook_auth": "",

                # **Statistics**
                # On what endpoint can the bot send statistics
                "post_stats_url": "https://api.voidbots.net/bot/stats/187636089073172481",
                # In the JSON, how should we call the server count ?
                "post_stats_server_count_key": "server_count",
                # In the JSON, how should we call the guild count ?
                "post_stats_shard_count_key": "shard_count",
            },
        }

        return BOTS_DICT

    async def get_bot_list(self) -> List[Dict[str, Any]]:
        BOTS_LIST = list((await self.get_bot_dict()).values())

        return BOTS_LIST

    async def get_routes(self, route_prefix):
        routes = []

        for bot_list in await self.get_bot_list():
            handler = bot_list.get("webhook_handler", None)
            if handler:
                webhook_key = bot_list.get("webhook_key", bot_list["name"])
                routes.append(('POST', f'{route_prefix}/{webhook_key}/hook', handler))

        return routes

    def votes_generic_hook_factory(self, bot_list_key, authorization_header="Authorization", user_id_json_field="id"):
        """
        Creates votes handlers for specific bots lists
        """

        async def votes_hook(request: web.Request):
            """
            Handle users votes for fateslist
            """
            bot_list = (await self.get_bot_dict())[bot_list_key]

            auth = request.headers.get(authorization_header, "")
            local_auth = bot_list.get('webhook_auth', bot_list['auth'])

            if auth != local_auth:
                self.bot.logger.warning(
                    f"Bad authentification ({auth} vs {local_auth}) provided to {bot_list['name']} API.")
                return web.Response(status=401, text="Unauthorized, bad auth")

            post_data = await request.json()

            if '.' not in user_id_json_field:
                user_id = int(post_data[user_id_json_field])
            else:
                user_id = post_data
                for part in user_id_json_field.split('.'):
                    user_id = user_id[part]
                user_id = int(user_id)

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
        bot_list = (await self.get_bot_dict())["top_gg"]
        auth = request.headers.get("Authorization", "")

        if auth != bot_list["auth"]:
            self.bot.logger.warning(f"Bad authentification provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad auth")

        post_data = await request.json()
        user_id = int(post_data["user"])

        bot_id = int(post_data["bot"])

        if bot_id != self.bot.user.id:
            self.bot.logger.warning(f"Bad bot ID ({bot_id}) provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad bot ID")

        is_test = post_data["type"] == "test"
        is_weekend = post_data["isWeekend"]

        multiplicator = int(is_weekend) + 1

        result, message = await self.handle_vote(user_id, bot_list, multiplicator=multiplicator, is_test=is_test)

        if result:
            return web.Response(status=200, text=message)
        else:
            return web.Response(status=400, text=message)

    async def handle_vote(self, user_id, bot_list, multiplicator=1, is_test=False) -> Tuple[bool, str]:
        bot_list_key = bot_list.get("webhook_key", bot_list["name"])
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.errors.NotFound:
            self.bot.logger.warning(f"Bad user ID provided to votes API {bot_list['name']}: {user_id}.")
            return False, "Unauthorized, bad user ID"

        db_user: DiscordUser = await get_from_db(user)

        db_user.votes[bot_list_key] += multiplicator
        db_user.last_votes[bot_list_key] = int(time.time())
        db_user.add_to_inventory(INV_COMMON_ITEMS["i_voted"])

        if not is_test:
            self.bot.logger.info(f"{multiplicator} vote(s) recorded for {user.name}#{user.discriminator} on {bot_list['name']}.")
            await db_user.save()
        else:
            self.bot.logger.warning(f"{multiplicator} test vote(s) received for {user.name}#{user.discriminator}. Not saved.")

        try:
            await user.send(f"✨ Thanks for voting for DuckHunt on {bot_list['name']}! "
                            f"Check your inventory with `dh!inv` in a game channel.")
        except discord.errors.Forbidden:
            pass

        return True, "Vote recorded"

    async def can_vote(self, bot_list, user, db_user):
        vote_check_url = bot_list.get("check_vote_url", None)
        vote_every = bot_list.get("vote_every", None)

        if not bot_list["can_vote"]:
            return False
        elif not vote_check_url and vote_every:
            bot_list_key = bot_list.get("webhook_key", bot_list["name"])

            last_vote = db_user.last_votes.get(bot_list_key, 0)
            now = int(time.time())

            time_elapsed = now - last_vote
            td_elapsed = datetime.timedelta(seconds=time_elapsed)

            # We wait for five more minutes just in case clocks desync'ed
            if td_elapsed > (vote_every + datetime.timedelta(minutes=5)):
                return True
            else:
                return False
        elif not vote_check_url:
            return None
        else:
            timeout = aiohttp.ClientTimeout(total=5)
            headers = {'accept': 'application/json', "Authorization": bot_list.get("auth", "")}
            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list['name']}")
            try:
                async with self.bot.client_session.get(vote_check_url.format(user=user), timeout=timeout, headers=headers) as resp:
                    json_resp = await resp.json()
            except asyncio.TimeoutError:
                return False  # Can't vote if the bot list is down

            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list['name']} -> {json_resp}")

            if '.' not in bot_list['check_vote_key']:
                voted_resp = str(json_resp.get(bot_list['check_vote_key']))
            else:
                voted_resp = json_resp
                for part in bot_list['check_vote_key'].split('.'):
                    voted_resp = json_resp[part]

            if voted_resp.isdigit():
                voted = bool(int(voted_resp))
            elif voted_resp.lower() == "true":
                voted = True
            elif voted_resp.lower() == "false":
                voted = False
            else:
                self.bot.logger.warning(f"Unknown response for {bot_list['name']} votechecking: {voted_resp}")
                voted = False

            if bot_list.get("check_vote_negate", True):
                return not voted
            else:
                return voted

    async def get_votable_lists(self, user: discord.User):
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
                text = votable_lists[0]['vote_url']
                embed.title = _("You can vote !")
                embed.description = _("Thanks for supporting the bot by voting !")
                embed.url = votable_lists[0]['vote_url']
                embed.colour = discord.Colour.green()
            elif maybe_lists:
                text = maybe_lists[0]['vote_url']
                embed.title = _("You might be able to vote !")
                embed.description = _("Thanks for supporting the bot by voting as much as you can. It makes a difference !")
                embed.url = maybe_lists[0]['vote_url']
                embed.colour = discord.Colour.orange()
            else:
                text = _("Oh no! No bot list is currently available for you to vote.")
                embed.title = _("There is nowhere for you to vote at the time !")
                embed.description = _("Thanks for supporting the bot. It makes a difference! \n"
                                      "Unfortunately, you voted everywhere you could for now, but you can check back in a few hours.")
                embed.colour = discord.Colour.red()

            click_me_to_vote = _("Click me to vote")
            for bot_list in votable_lists:
                embed.add_field(name=_("You can vote on {bl_name}", bl_name=bot_list['name']),
                                value=f"[{click_me_to_vote}]({bot_list['vote_url']})", inline=False)

            for bot_list in maybe_lists:
                embed.add_field(name=_("You might be able to vote on {bl_name}", bl_name=bot_list['name']),
                                value=f"[{click_me_to_vote}]({bot_list['vote_url']})", inline=True)

            await m.edit(embed=embed, content=text)

    @Cog.listener("on_guild_join")
    @Cog.listener("on_guild_remove")
    @Cog.listener("on_ready")
    async def post_stats(self, *args, **kwargs):
        self.bot.logger.debug(f"Updating stats on bots list")

        server_count = len(self.bot.guilds)
        shard_count = self.bot.shard_count

        for bot_list in await self.get_bot_list():
            stats_url = bot_list.get("post_stats_url", None)
            if stats_url:
                timeout = aiohttp.ClientTimeout(total=5)
                headers = {'Content-Type': 'application/json',
                           'accept': 'application/json',
                           "Authorization": bot_list.get("auth", "")}
                post_data = {}

                post_stats_server_count_key = bot_list.get("post_stats_server_count_key", "server_count")
                if post_stats_server_count_key:
                    post_data[post_stats_server_count_key] = server_count

                post_stats_shard_count_key = bot_list.get("post_stats_shard_count_key", "shard_count")
                if post_stats_shard_count_key:
                    post_data[post_stats_shard_count_key] = shard_count
                try:
                    resp = await self.bot.client_session.post(stats_url, timeout=timeout, headers=headers, json=post_data)
                except asyncio.TimeoutError:
                    self.bot.logger.warning(f"Push stats to {bot_list['name']}: resp [TIMEOUT]")
                else:
                    text = await resp.text()
                    status = resp.status
                    if status == 200:
                        self.bot.logger.debug(f"Pushed stats to {bot_list['name']} : resp [{status}] {text}")
                    else:
                        self.bot.logger.warning(f"Pushed stats to {bot_list['name']} : resp [{status}] {text}")


setup = BotsListVoting.setup
