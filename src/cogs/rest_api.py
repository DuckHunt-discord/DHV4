import datetime
from typing import Union, Optional

import aiohttp_cors
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from discord.ext import commands, tasks
from discord.ext.commands import Command, Group

from utils.cog_class import Cog
from utils.models import get_enabled_channels, DiscordChannel, get_from_db, Player, AccessLevel


class RestAPI(Cog):
    """
    If someone wants to do a dashboard or something to control DuckHunt, there are a few api routes already. They all return JSON or HTTP404/403/500.

    **Routes**:

    `/api/channels`  [Global Authentication required] -> Returns some information about all channels enabled on the bot.
    `/api/channels/{channel_id}`  [Authentication required] -> Returns information about the channel, like the ducks currently spawned.
    `/api/channels/{channel_id}/settings`  [Authentication required] -> Returns channel settings
    `/api/channels/{channel_id}/top` [No authentication required] -> Returns the top scores (all players on the channel and some info about players)
    `/api/channels/{channel_id}/player/{player_id}` [No authentication required] -> Returns *all* the data for a specific user

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
        self.cors = aiohttp_cors.setup(self.app)
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

    async def channels_list(self, request):
        """
        /channels/

        Get all channels enabled on the bot
        """

        await self.authenticate_request(request)

        channels = await DiscordChannel.filter(enabled=True).prefetch_related("guild").all()

        return web.json_response([{
            "channel_name": channel.name,
            "channel_discord_id": channel.discord_id,
            "guild_discord_id": channel.guild.discord_id,
            "guild_name": channel.guild.name,
            "prefix": channel.guild.prefix,
            "vip": channel.guild.vip,
            "language": channel.guild.language,
        } for channel in channels])

    async def channel_info(self, request):
        """
        /channels/<channel_id>

        Get information about a specific channel ID
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        if channel is None:
            raise HTTPNotFound(reason="Unknown channel")

        try:
            await self.authenticate_request(request, channel=channel)
        except HTTPForbidden:
            return web.json_response(
                {'id': channel.id,
                 'name': channel.name,
                 'authentication': False,
                 })

        ducks_spawned = self.bot.ducks_spawned[channel]
        ducks_left = self.bot.enabled_channels[channel]

        return web.json_response(
            {'id': channel.id,
             'name': channel.name,
             'ducks': [duck.serialize() for duck in ducks_spawned],
             'ducks_left_today': ducks_left,
             'authentication': True,
             })

    async def channel_settings(self, request):
        """
        /channels/<channel_id>/settings

        Get information about a specific channel ID
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        if channel is None:
            raise HTTPNotFound(reason="Unknown channel")

        await self.authenticate_request(request, channel=channel)

        db_channel = await get_from_db(channel)

        return web.json_response(db_channel.serialize())

    async def channel_top(self, request):
        """
        /channels/<channel_id>/top

        Get players data, ordered by experience
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        if not channel:
            raise HTTPNotFound(reason="Unknown channel")

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

    def get_help_dict(self, group: Union[Group, Cog]):
        commands = {}
        if isinstance(group, Group):
            commands_list = group.commands
        else:
            commands_list = group.get_commands()

        for command in commands_list:
            access: Optional[AccessLevel] = None
            for check in command.checks:
                if hasattr(check, "access"):
                    access = check.access
                    break

            if not command.hidden:
                commands[command.name] = {
                    'name': command.qualified_name,
                    'short_doc': command.short_doc,
                    'brief': command.brief,
                    'help': command.help,
                    'usage': command.usage,
                    'aliases': command.aliases,
                    'enabled': command.enabled,
                    'description': command.description,
                    'signature': command.signature,
                    'invoke_with': f"{command.qualified_name} {command.signature}" if command.signature else command.qualified_name,
                }
                if isinstance(command, Group):
                    commands[command.name]['subcommands'] = self.get_help_dict(command)

                if access:
                    commands[command.name]['access_value'] = access.value
                    commands[command.name]['access_name'] = access.name

        return commands

    async def commands(self, request):
        """
        /help/commands

        Get list of commands
        """

        help_dict = {}

        for cog_name, cog in self.bot.cogs.items():
            help_dict = {**help_dict, **self.get_help_dict(cog)}

        return web.json_response(help_dict)

    async def run(self):
        await self.bot.wait_until_ready()
        listen_ip = self.config()['listen_ip']
        listen_port = self.config()['listen_port']
        route_prefix = self.config()['route_prefix']
        routes = [
            ('GET', f'{route_prefix}/channels', self.channels_list),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}', self.channel_info),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/top', self.channel_top),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/settings', self.channel_settings),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/player/{{player_id:\\d+}}', self.player_info),
            ('GET', f'{route_prefix}/help/commands', self.commands),
        ]
        for route_method, route_path, route_coro in routes:
            resource = self.cors.add(self.app.router.add_resource(route_path))
            route = self.cors.add(
                    resource.add_route(route_method, route_coro), {
                        "*": aiohttp_cors.ResourceOptions(
                            allow_credentials=True,
                            allow_headers=("X-Requested-With", "Content-Type", "Authorization",),
                            max_age=3600,
                        )
                })

        await self.runner.setup()
        self.site = web.TCPSite(self.runner, listen_ip, listen_port)
        await self.site.start()
        self.bot.logger.info(f"DuckHunt JSON API listening on http://{listen_ip}:{listen_port}")


setup = RestAPI.setup
