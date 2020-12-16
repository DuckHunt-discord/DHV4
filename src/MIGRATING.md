# How to import data from DHV3

You might want to run a query like this

```sql
SELECT
    *
FROM
    prefs p
    JOIN channels c ON p.server_id = c.server;
```

And export the settings (by channel) from the DB.

Then, run something like

```sql
SELECT
    *
FROM
    players p
    JOIN channels c ON p.channel_id = c.id;
```

To export the players.

Once that is done, you should get json files like those:

Settings:

```json
[
  {
    "server_id": 110373943822540800,
    "announce_level_up": 1,
    "bang_lag": 0.5,
    "chance_to_kill_on_missed": 5,
    "clover_max_exp": 10,
    "clover_min_exp": 1,
    "delete_commands": 0,
    "disable_decoys_when_ducks_are_sleeping": 1,
    "duck_frighten_chance": 5,
    "ducks_per_day": 24,
    "emoji_used": "<:official_Duck_01_reversed:439576463436546050>",
    "exp_won_per_duck_killed": 10,
    "killed_mentions": 1,
    "language": "en_EN",
    "mention_in_topscores": 0,
    "multiplier_miss_chance": 1,
    "pm_most_messages": 0,
    "prefix": "!",
    "show_super_ducks_life": 0,
    "sleeping_ducks_start": 0,
    "sleeping_ducks_stop": 0,
    "super_ducks_chance": 5,
    "baby_ducks_chance": 2,
    "mother_of_all_ducks_chance": 1,
    "ducks_chance": 100,
    "super_ducks_exp_multiplier": 1.1,
    "super_ducks_maxlife": 7,
    "super_ducks_minlife": 3,
    "tax_on_user_give": 15,
    "time_before_ducks_leave": 660,
    "tts_ducks": 0,
    "user_can_give_exp": 1,
    "events_enabled": 1,
    "pm_stats": 0,
    "randomize_mechanical_ducks": 0,
    "users_can_find_objects": 1,
    "vip": 0,
    "debug_show_ducks_class_on_spawn": 0,
    "id": 3,
    "server": 110373943822540800,
    "channel": 119222314964353025,
    "enabled": 0,
    "channel_name": "ultimate-shitposting"
  },
```

Players: 
```json
[
  {
    "id": 182,
    "id_": 138751484517941259,
    "name": "Eyesofcreeper#0001",
    "channel_id": 3,
    "banned": "0",
    "confisque": 0,
    "dazzled": 0,
    "enrayee": 0,
    "mouille": 1477916318,
    "sabotee": "-",
    "sand": 0,
    "exp": 4529,
    "lastGiveback": 1592243459,
    "trefle_exp": 5,
    "ap_ammo": 0,
    "balles": 0,
    "chargeurs": 5,
    "detecteurInfra": 1560949903,
    "detecteur_infra_shots_left": 6,
    "explosive_ammo": 1578347742,
    "graisse": 1578412431,
    "life_insurance": 0,
    "sight": 0,
    "silencieux": 0,
    "sunglasses": 0,
    "trefle": 1471641816,
    "self_killing_shoots": 0,
    "shoots_almost_killed": 0,
    "shoots_frightened": 14,
    "shoots_harmed_duck": 67,
    "shoots_infrared_detector": 0,
    "shoots_jamming_weapon": 10,
    "shoots_no_duck": 39,
    "shoots_sabotaged": 0,
    "shoots_tried_while_wet": 0,
    "shoots_with_jammed_weapon": 1,
    "shoots_without_bullets": 114,
    "shoots_without_weapon": 5,
    "shoots_fired": 664,
    "shoots_missed": 145,
    "killed_ducks": 399,
    "killed_normal_ducks": 366,
    "killed_super_ducks": 33,
    "killed_baby_ducks": 0,
    "killed_mother_of_all_ducks": 0,
    "killed_mechanical_ducks": 0,
    "killed_players": 6,
    "best_time": 2.189402,
    "exp_won_with_clover": 0,
    "givebacks": 117,
    "life_insurence_rewards": 0,
    "reloads": 249,
    "reloads_without_chargers": 13,
    "trashFound": 42,
    "unneeded_reloads": 33,
    "used_exp": 0,
    "found_explosive_ammo": 0,
    "found_almost_empty_explosive_ammo": 1,
    "found_chargers": 0,
    "found_chargers_not_taken": 0,
    "found_bullets": 2,
    "found_bullets_not_taken": 0,
    "found_silencers": 0,
    "found_infrared_detectors": 2,
    "found_grease": 2,
    "murders": 0,
    "avatar_url": "https://cdn.discordapp.com/avatars/138751484517941259/a_7b8ab8ec5cc3f97198eb3ac85d65f292.gif?size=1024",
    "hugs": 2,
    "hugs_no_duck": 0,
    "hugged_baby_ducks": 2,
    "hugged_nohug_ducks": 0,
    "hugs_human": 0,
    "id": 3,
    "server": 110373943822540800,
    "channel": 119222314964353025,
    "enabled": 0,
    "channel_name": "ultimate-shitposting"
  },
```
Once you have those, just run the import_from_v3.py script and wait a few minutes :)
