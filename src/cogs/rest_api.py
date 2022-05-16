from collections import defaultdict
from typing import Union, Optional

import aiohttp_cors
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from discord.ext.commands import Group

from utils.cog_class import Cog
from utils.models import DiscordChannel, get_from_db, Player, AccessLevel


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

    async def cog_load(self):
        self.app = web.Application()
        self.cors = aiohttp_cors.setup(self.app)
        self.runner = web.AppRunner(self.app, access_log=self.bot.logger.logger)
        self.site = None
        self.bot.loop.create_task(self.run())

    async def cog_unload(self):
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
        ducks = self.bot.enabled_channels[channel]

        return web.json_response(
            {'id': channel.id,
             'name': channel.name,
             'ducks': [duck.serialize() for duck in ducks_spawned],
             'ducks_left_today': ducks.ducks_left,
             'ducks_left_day': ducks.day_ducks,
             'ducks_left_night': ducks.night_ducks,
             'authentication': True,
             })

    async def channel_settings(self, request):
        """
        /channels/<channel_id>/settings

        Get settings for a specific channel ID
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

        Get players data for a specific channel ID, ordered by experience
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        if not channel:
            raise HTTPNotFound(reason="Unknown channel")

        players = await Player.all().filter(channel__discord_id=channel.id).order_by('-experience').prefetch_related(
            "member__user")

        if not players:
            raise HTTPNotFound(reason="Unknown channel in database")

        fields = ["experience", "best_times", "killed", "last_giveback", "shooting_stats"]

        return web.json_response([
            player.serialize(serialize_fields=fields) for player in players
        ])

    async def player_info(self, request):
        """
        /channels/<channel_id>/player/<player_id>

        Get information for a specific player ID and channel ID
        """
        channel = self.bot.get_channel(int(request.match_info['channel_id']))

        # await self.authenticate_request(request, channel=channel)

        player = await Player \
            .filter(channel__discord_id=channel.id,
                    member__user__discord_id=int(request.match_info['player_id'])) \
            .first() \
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
                aliases = []
                for alias in command.aliases:
                    try:
                        alias.encode('ascii')
                    except UnicodeEncodeError:
                        continue
                    aliases.append(alias)

                commands[command.name] = {
                    'name': command.qualified_name,
                    'short_doc': command.short_doc,
                    'brief': command.brief,
                    'help': command.help,
                    'usage': command.usage,
                    'aliases': aliases,
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

    async def status(self, request):
        """
        /status

        Check the status of every shard the bot is hosting.
        """
        shards_status = []
        latencies = sorted(self.bot.latencies, key=lambda l: l[0])  # Sort by shard n°

        guilds_by_shard = defaultdict(list)
        for guild in sorted(self.bot.available_guilds, key=lambda g: -g.member_count):
            guilds_by_shard[guild.shard_id].append({"id": guild.id, "name": guild.name, "members": guild.member_count})

        for shard, latency in latencies:
            shards_status.append(
                {
                    "shard_id": shard,
                    "latency": round(latency, 2),
                    "ready": shard in self.bot.shards_ready,
                    "guilds": guilds_by_shard[shard]
                }
            )

        return web.json_response(
            {
                "bot_latency": round(self.bot.latency, 2),
                "shards_status": shards_status,
                "unsharded_guilds": guilds_by_shard[None]
            }
        )

    async def stats(self, request):
        """
        /stats

        Get some global statistics about the bot.
        """

        try:
            total_members = sum((g.member_count for g in self.bot.available_guilds))
        except:
            self.bot.logger.exception("Couldn't get total member count.")
            total_members = 0

        return web.json_response(
            {
                "members_count": total_members,
                "guilds_count": len(self.bot.guilds),
                "channels_count": sum((len(g.channels) for g in self.bot.available_guilds)),
                "players_count": await Player.all().count(),
                "alive_ducks_count": sum(len(v) for v in self.bot.ducks_spawned.values()),
                "uptime": int(self.bot.uptime.timestamp()),
                "current_event_name": self.bot.current_event.name,
                "current_event_value": self.bot.current_event.value,
                "global_ready": self.bot.is_ready()
            }
        )

    async def run(self):
        # Don't wait for ready to avoid blocking the website
        # await self.bot.wait_until_ready()
        listen_ip = self.config()['listen_ip']
        listen_port = self.config()['listen_port']
        route_prefix = self.config()['route_prefix']

        botlist_cog = self.bot.get_cog("BotsListVoting")

        routes = [
            ('GET', f'{route_prefix}/channels', self.channels_list),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}', self.channel_info),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/top', self.channel_top),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/settings', self.channel_settings),
            ('GET', f'{route_prefix}/channels/{{channel_id:\\d+}}/player/{{player_id:\\d+}}', self.player_info),
            ('GET', f'{route_prefix}/help/commands', self.commands),
            ('GET', f'{route_prefix}/status', self.status),
            ('GET', f'{route_prefix}/stats', self.stats),
        ]

        if not botlist_cog:
            self.bot.logger.error("API was loaded before the bots_list cog")
        else:
            routes += await botlist_cog.get_routes(f"{route_prefix}/votes")

        self.bot.logger.debug(f"Defined routes {routes}")

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
        # noinspection HttpUrlsUsage
        self.bot.logger.info(f"DuckHunt JSON API listening on http://{listen_ip}:{listen_port}")


setup = RestAPI.setup
