import datetime

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from discord.ext import commands, tasks
from utils.cog_class import Cog
from utils.models import get_enabled_channels, DiscordChannel, get_from_db, Player


class RestAPI(Cog):
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

        if channel is None:
            raise HTTPNotFound(reason="Unknown channel")

        await self.authenticate_request(request, channel=channel)

        players = await Player.all().filter(channel__discord_id=channel.id).order_by('-experience').prefetch_related("member__user")

        return web.json_response([
            player.serialize() for player in players
        ])

    async def run(self):
        await self.bot.wait_until_ready()
        listen_ip = self.config()['listen_ip']
        listen_port = self.config()['listen_port']
        route_prefix = self.config()['route_prefix']
        self.app.add_routes([
            web.get(f'{route_prefix}/channels/{{channel_id:\\d+}}', self.channel_info),
            web.get(f'{route_prefix}/channels/{{channel_id:\\d+}}/top', self.channel_top),
        ])
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, listen_ip, listen_port)
        await self.site.start()
        self.bot.logger.info(f"DuckHunt JSON API listening on http://{listen_ip}:{listen_port}")


setup = RestAPI.setup
