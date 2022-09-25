from sys import argv
from os import environ

from toml import load, dump


assert len(argv) == 3, "Excepting config load file as first argument and output file as second argument"

FROM_CONFIG = argv[1]
TO_CONFIG = argv[2]

with open(FROM_CONFIG, "r") as f:
    config = load(f)

config['auth']['discord']['token'] = environ['BOT_TOKEN']

config['database']['host'] = environ['DB_HOST']
config['database']['port'] = environ['DB_PORT']
config['database']['user'] = environ['DB_USER']
config['database']['password'] = environ['DB_PASSWORD']
config['database']['database'] = environ['DB_NAME']

config['cogs']['RestAPI']['global_access_keys'].append(environ['GLOBAL_API_KEY'])
config['cogs']['BotsListVoting']['statcord_token'] = environ['STATCORD_TOKEN']


with open(TO_CONFIG, "w") as f:
    dump(config, f)
