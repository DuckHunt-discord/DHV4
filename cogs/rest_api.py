import datetime

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from discord.ext import commands, tasks
from utils.cog_class import Cog
from utils.models import get_enabled_channels, DiscordChannel, get_from_db, Player


class RestAPI(Cog):
    """
    If someone wants to do a dashboard or something to control DuckHunt, there are a few api routes already. They all return JSON or HTTP404/403/500.

    **Routes**:

    `/api/channel/{channel_id}`  [Authentication required] -> Returns information about the channel, like the ducks currently spawned.
    `/api/channel/{channel_id}/top` -> [No authentication required] Returns the top scores (all players on the channel and some info about players)
    `/api/channel/{channel_id}/player/{player_id}` -> [No authentication required] Returns *all* the data for a specific user

    **Authentication**:

    If you have one, pass the API key on the Authorization HTTP header.

    Two types of keys exist :

    - Channel specific keys, available with `settings api_key`. They only work for a specific channel data.
    - Global keys, that allow UNLIMITED access to every channel data. They are available on request with me.

    Api keys (local or global) are uuid4, and look like this : `d84af260-c806-4066-8387-1d5144b7fa72`
    """
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.app = web.Application()
        self.runner = web.AppRunner(self.app, access_log=self.bot.logger.logger)
        self.site = None
        bot.loop.create_task(self.run())

    def cog_unload(self):
        self.bot.logger.info(f"DuckHunt JSON API is shutting down...")
        self.bot.loop.create_task(self.site.stop())

    async def authenticate_request(self, request, channel=None):
        api_key = request.headers.get('Authorization')
        if api_key is None:
            raise HTTPForbidden(reason="No API key provided in Authorization header")

        api_key = api_key.lower()

        if api_key in self.config()["global_access_keys"]:
            return True

        if not channel:
            raise HTTPForbidden(reason="This route requires a GLOBAL api key. Ask the bot owner.")

        if channel:
            db_channel = await get_from_db(channel)
            channel_api_key = str(db_channel.api_key)
            if channel_api_key != api_key:
                raise HTTPForbidden(reason="The API key provided isn't valid for the specified channel.")
            else:
                return True

    async def channel_info(self, request):
        """
        /channels/<channel_id>

        Get information about a specific channel ID
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        if channel is None:
            raise HTTPNotFound(reason="Unknown channel")

        await self.authenticate_request(request, channel=channel)

        ducks_spawned = self.bot.ducks_spawned[channel]

        return web.json_response(
            {'id': channel.id,
             'name': channel.name,
             'ducks': [duck.serialize() for duck in ducks_spawned]
             })

    async def channel_top(self, request):
        """
        /channels/<channel_id>/top

        Get players data, ordered by experience
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        await self.authenticate_request(request, channel=channel)

        players = await Player.all().filter(channel__discord_id=channel.id).order_by('-experience').prefetch_related("member__user")

        if not players:
            raise HTTPNotFound(reason="Unknown channel in database")

        fields = ["experience", "best_times", "killed", "last_giveback"]

        return web.json_response([
            player.serialize(serialize_fields=fields) for player in players
        ])

    async def player_info(self, request):
        """
        /channels/<channel_id>/player/<player_id>

        Get players data, ordered by experience
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        await self.authenticate_request(request, channel=channel)

        player = await Player\
            .filter(channel__discord_id=channel.id,
                    member__user__discord_id=int(request.match_info['player_id']))\
            .first()\
            .prefetch_related("member__user")

        if not player:
            raise HTTPNotFound(reason="Unknown player/channel/user")

        return web.json_response(player.serialize())

    async def run(self):
        await self.bot.wait_until_ready()
        listen_ip = self.config()['listen_ip']
        listen_port = self.config()['listen_port']
        route_prefix = self.config()['route_prefix']
        self.app.add_routes([
            web.get(f'{route_prefix}/channels/{{channel_id:\\d+}}', self.channel_info),
            web.get(f'{route_prefix}/channels/{{channel_id:\\d+}}/top', self.channel_top),
            web.get(f'{route_prefix}/channels/{{channel_id:\\d+}}/player/{{player_id:\\d+}}', self.player_info),
        ])
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, listen_ip, listen_port)
        await self.site.start()
        self.bot.logger.info(f"DuckHunt JSON API listening on http://{listen_ip}:{listen_port}")


setup = RestAPI.setup
