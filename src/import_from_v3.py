import asyncio
import datetime
import json
import time

from tortoise import Tortoise
from tqdm import tqdm

from utils import models
from utils.config import load_config
from utils.models import init_db_connection, DiscordGuild, DiscordChannel, DiscordUser, DiscordMember, AccessLevel, \
    Player

DHV3_PLAYERS_FILE = "import_v3_data/DHV3_players.json"
DHV3_SETTINGS_FILE = "import_v3_data/DHV3_settings.json"

guilds_cache = {}
channels_cache = {}
users_cache = {}
members_cache = {}

now = time.time()


async def get_or_create_guild(guild_id: int, **kwargs):
    try:
        return guilds_cache[guild_id]
    except KeyError:
        guild = DiscordGuild(discord_id=guild_id, **kwargs)
        await guild.save()
        guilds_cache[guild_id] = guild
        return guild


async def get_or_create_user(user_id: int, **kwargs):
    try:
        return users_cache[user_id]
    except KeyError:
        user = DiscordUser(
            discord_id=user_id,
            **kwargs,
        )
        await user.save()
        users_cache[user_id] = user
        return user


async def get_or_create_member(user_id: int, guild_id: int, **kwargs):
    try:
        return members_cache[(user_id, guild_id)]
    except KeyError:
        member = DiscordMember(
            user=await get_or_create_user(user_id),
            guild=await get_or_create_guild(guild_id),
            **kwargs,
        )
        await member.save()
        members_cache[(user_id, guild_id)] = member
        return member


def remove_empty_data(dct: dict):
    cleaned = {}
    for key, value in dct.items():
        if value:
            cleaned[key] = value

    return cleaned


async def main():
    print(f"Loading data from {DHV3_SETTINGS_FILE}...")

    with open(DHV3_SETTINGS_FILE, "r") as f:
        settings = json.load(f)

    print(f"Loading data from {DHV3_PLAYERS_FILE}...")
    with open(DHV3_PLAYERS_FILE, "r") as f:
        players = json.load(f)

    print("JSON Data loaded into memory...")
    print("Continuing will assume an ERASED database")
    print("If you wish to proceed, press enter. If you changed your mind, type CTRL+C now to exit")

    input("Press ENTER >")

    config = load_config()

    await init_db_connection(config['database'], create_dbs=True)

    for setting in tqdm(settings, desc="Importing settings"):
        language = "en_US" if setting["language"] in ["en", "en_EN"] else setting["language"]
        prefix = setting["prefix"]
        if len(prefix) >= 10:
            prefix = "toolong"

        guild = await get_or_create_guild(setting["server_id"], name="Imported from V3", prefix=prefix,
                                          language=language)

        channel = DiscordChannel(
            discord_id=setting["channel"],
            guild=guild,
            name=setting["channel_name"],
            enabled=bool(int(setting["enabled"])),
            tax_on_user_send=max(min(setting["tax_on_user_give"], 100), 0) if setting["user_can_give_exp"] else 100,
            mentions_when_killed=bool(setting["killed_mentions"]),
            show_duck_lives=bool(setting["show_super_ducks_life"]),
            kill_on_miss_chance=setting["chance_to_kill_on_missed"],
            duck_frighten_chance=setting["duck_frighten_chance"],
            clover_min_experience=setting["clover_min_exp"],
            clover_max_experience=setting["clover_max_exp"],
            base_duck_exp=setting["exp_won_per_duck_killed"],
            per_life_exp=min(int(setting["exp_won_per_duck_killed"] * setting["super_ducks_exp_multiplier"]), 100),
            ducks_per_day=setting["ducks_per_day"],
            night_start_at=setting["sleeping_ducks_start"] * 60 * 60,
            night_end_at=setting["sleeping_ducks_stop"] * 60 * 60,
            spawn_weight_normal_ducks=setting["ducks_chance"],
            spawn_weight_super_ducks=setting["super_ducks_chance"],
            spawn_weight_baby_ducks=setting["baby_ducks_chance"],
            spawn_weight_moad_ducks=setting["mother_of_all_ducks_chance"],
            ducks_time_to_live=setting["time_before_ducks_leave"],
            super_ducks_min_life=setting["super_ducks_minlife"],
            super_ducks_max_life=setting["super_ducks_maxlife"],
        )

        await channel.save()

        channels_cache[setting["channel"]] = channel

    print("Finished with settings, freeing ram.")

    del settings

    print("Now, we are going for the players...")

    for player_obj in tqdm(players, desc="Importing players"):
        guild = guilds_cache[player_obj["server"]]
        channel = channels_cache[player_obj["channel"]]

        splitted_name = player_obj["name"].split("#")
        if len(splitted_name) == 1:
            name = splitted_name[0]
            discriminator = "0000"
        else:
            name, discriminator = ''.join(splitted_name[:-1]), splitted_name[-1]

        if len(discriminator) != 4:
            print(f"Invalid discrim for {player_obj['name']}")
            if discriminator.isdigit():
                discriminator = discriminator[:4].zfill(4)
            else:
                discriminator = "0000"

        user = await get_or_create_user(player_obj["id_"], name=name, discriminator=discriminator,
                                        trophys={"v3_player": True})

        access = AccessLevel.DEFAULT
        if bool(int(player_obj["banned"])):
            access = AccessLevel.BANNED

        member = await get_or_create_member(player_obj["id_"], player_obj["server"], access_level=access)
        player = Player(
            channel=channel,
            member=member,
            active_powerups=remove_empty_data({
                "confiscated": int(player_obj["confisque"]),
                "mirror": 6 if int(player_obj["dazzled"]) > now else 0,
                "jammed": int(player_obj["enrayee"]),
                "wet": int(player_obj["mouille"]),
                "sand": 1 if int(player_obj["sand"]) > now else 0,
                "clover_exp": int(player_obj["trefle_exp"]),
                "clover": int(player_obj["trefle"]),
                "detector": int(player_obj["detecteur_infra_shots_left"]) if player_obj["detecteurInfra"] > now else 0,
                "explosive_ammo": int(player_obj["explosive_ammo"]),
                "grease": int(player_obj["graisse"]),
                "sight": 12 if int(player_obj["sight"]) > now else 0,
                "silencer": int(player_obj["silencieux"]),
                "sunglasses": int(player_obj["sunglasses"])
            }),
            shooting_stats=remove_empty_data({
                "suicides": player_obj["self_killing_shoots"],
                "shots_stopped_by_detector": player_obj["shoots_infrared_detector"],
                "shots_jamming_weapon": player_obj["shoots_jamming_weapon"],
                "shots_without_ducks": player_obj["shoots_no_duck"],
                "shots_when_sabotaged": player_obj["shoots_sabotaged"],
                "shots_when_wet": player_obj["shoots_tried_while_wet"],
                "shots_when_jammed": player_obj["shoots_with_jammed_weapon"],
                "shots_with_empty_magazine": player_obj["shoots_without_bullets"],
                "shots_when_confiscated": player_obj["shoots_without_weapon"],
                "bullets_used": player_obj["shoots_fired"],
                "missed": player_obj["shoots_missed"],
                "killed": player_obj["killed_players"],
                "murders": player_obj["murders"],
                "bonus_experience_earned": player_obj["exp_won_with_clover"] + player_obj["life_insurence_rewards"],
                "reloads": player_obj["reloads"],
                "empty_reloads": player_obj["reloads_without_chargers"],
                "unneeded_reloads": player_obj["unneeded_reloads"],
            }),
            experience=player_obj["exp"],
            spent_experience=player_obj["used_exp"],
            givebacks=player_obj["givebacks"],
            found_items=remove_empty_data({
                "took_trash_old_items": player_obj["trashFound"],
                "took_explosive_ammo": player_obj["found_explosive_ammo"],
                "took_partial_explosive_ammo": player_obj["found_almost_empty_explosive_ammo"],
                "took_magazine": player_obj["found_chargers"],
                "left_magazine": player_obj["found_chargers_not_taken"],
                "took_bullet": player_obj["found_bullets"],
                "left_bullet": player_obj["found_bullets_not_taken"],
                "took_silencer": player_obj["found_silencers"],
                "took_detector": player_obj["found_infrared_detectors"],
                "took_grease": player_obj["found_grease"],
            }),
            bullets=player_obj["balles"],
            magazines=player_obj["chargeurs"],
            last_giveback=datetime.datetime.fromtimestamp(player_obj["lastGiveback"]),
            killed=remove_empty_data({
                "normal": player_obj["killed_normal_ducks"],
                "super": player_obj["killed_super_ducks"],
                "baby": player_obj["killed_baby_ducks"],
                "moad": player_obj["killed_mother_of_all_ducks"],
                "mechanical": player_obj["killed_mechanical_ducks"],
            }),
            hugged=remove_empty_data({
                "baby": player_obj["hugged_baby_ducks"],
                "nothing": player_obj["hugs_no_duck"],
                "v3_nohug": player_obj["hugged_nohug_ducks"],
                "players": player_obj["hugs_human"],
            }),
            harmed=remove_empty_data({
                "super": player_obj["shoots_harmed_duck"]
            }),
            frightened=remove_empty_data({
                "v3": player_obj["shoots_frightened"]
            }),
        )

        await player.save()

    print(
        f"I guess we are done here!\n{len(players)} players saved in {len(channels_cache)} channels/{len(guilds_cache)} guilds")


if __name__ == '__main__':
    asyncio.run(main())
