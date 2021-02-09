import toml
import sys
import os

assert len(sys.argv) == 3, "Excepting config load file as first argument and output file as second argument"

FROM_CONFIG = sys.argv[1]
TO_CONFIG = sys.argv[2]
environ = os.environ

with open(FROM_CONFIG, "r") as f:
    config = toml.load(f)

config['auth']['discord']['token'] = environ['BOT_TOKEN']

config['database']['host'] = environ['DB_HOST']
config['database']['port'] = environ['DB_PORT']
config['database']['user'] = environ['DB_USER']
config['database']['password'] = environ['DB_PASSWORD']
config['database']['database'] = environ['DB_NAME']

config['cogs']['RestAPI']['global_access_keys'].append(environ['GLOBAL_API_KEY'])

config['bot_lists']['topgg_shared_secret'] = environ['TOPGG_SHARED_SECRET']
config['bot_lists']['fateslist_api_token'] = environ['FATESLIST_API_TOKEN']
config['bot_lists']['discordbotlist_api_token'] = environ['DISCORDBOTLIST_TOKEN']

with open(TO_CONFIG, "w") as f:
    toml.dump(config, f)
