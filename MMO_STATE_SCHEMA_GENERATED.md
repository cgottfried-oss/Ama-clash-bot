# MMO STATE DATA SCHEMA

Generated from source-code access patterns.

## Top-Level State Keys

- `players` — 38 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/market_commands.py, clash_mmo/commands/pve_commands.py
- `territories` — 7 reference(s) — clash_mmo/commands/territory_commands.py, clash_mmo/game/territory/formatting.py, clash_mmo/game/territory/ownership.py, clash_mmo/game/territory/resources.py
- `marketplace` — 6 reference(s) — clash_mmo/commands/market_commands.py, clash_mmo/game/marketplace/economy.py, clash_mmo/game/marketplace/service.py
- `events` — 5 reference(s) — clash_mmo/commands/event_commands.py, clash_mmo/game/ai_events/service.py
- `raids` — 4 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/raid_commands.py
- `active_raid` — 3 reference(s) — clash_mmo/game/pve/instances.py, clash_mmo/game/pve/service.py
- `wars` — 2 reference(s) — clash_mmo/commands/pvp_commands.py
- `modifiers` — 2 reference(s) — clash_mmo/game/ai_events/effects.py
- `last_spawn` — 2 reference(s) — clash_mmo/game/ai_events/scheduler.py
- `crafting` — 2 reference(s) — clash_mmo/game/crafting/service.py, clash_mmo/game/crafting/upgrade_service.py
- `last_raiduser` — 1 reference(s) — clash_mmo/commands/pvp_commands.py
- `revenge_target` — 1 reference(s) — clash_mmo/commands/pvp_commands.py
- `revenge_until` — 1 reference(s) — clash_mmo/commands/pvp_commands.py
- `seasons` — 1 reference(s) — clash_mmo/commands/season_commands.py
- `territory_cooldowns` — 1 reference(s) — clash_mmo/commands/territory_commands.py
- `season_points` — 1 reference(s) — clash_mmo/game/territory/season.py

## Player Profile Keys

- `players[user_id]["gold"]` — 49 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/market_commands.py
- `players[user_id]["raid_medals"]` — 29 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["town_hall"]` — 28 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/gear_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["gems"]` — 28 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["active_hero"]` — 27 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/gear_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["cooldowns"]` — 27 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/pvp_commands.py, clash_mmo/commands/raid_commands.py
- `players[user_id]["clan_xp"]` — 26 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["stats"]` — 23 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/pvp_commands.py
- `players[user_id]["inventory"]` — 18 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/gear_commands.py, clash_mmo/commands/market_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["dark_elixir"]` — 17 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["heroes"]` — 15 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/gear_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/pvp_commands.py
- `players[user_id]["elixir"]` — 15 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/raid_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["boosts"]` — 14 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/raid_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["shiny_ore"]` — 13 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/raid_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["glowy_ore"]` — 13 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/raid_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["starry_ore"]` — 13 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/raid_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["name"]` — 12 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/season_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["achievements"]` — 11 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/raid_commands.py
- `players[user_id]["pvp"]` — 11 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pvp_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["daily_streak"]` — 10 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/pve_commands.py
- `players[user_id]["identity"]` — 10 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/clan_economy_commands.py, clash_mmo/commands/heroes_commands.py, clash_mmo/commands/pve_commands.py, clash_mmo/commands/season_commands.py
- `players[user_id]["shop_inventory"]` — 9 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/pvp_commands.py, clash_mmo/commands/shop_commands.py
- `players[user_id]["daily_counters"]` — 5 reference(s) — clash_mmo/commands/core_economy_commands.py
- `players[user_id]["streak"]` — 4 reference(s) — clash_mmo/game/core/matchmaking.py
- `players[user_id]["matchmaking"]` — 4 reference(s) — clash_mmo/game/matchmaking/formatting.py, clash_mmo/game/matchmaking/service.py
- `players[user_id]["last_daily_key"]` — 3 reference(s) — clash_mmo/commands/pve_commands.py
- `players[user_id]["cosmetics"]` — 3 reference(s) — clash_mmo/commands/season_commands.py, clash_mmo/game/cosmetics/formatting.py, clash_mmo/game/cosmetics/service.py
- `players[user_id]["wins"]` — 2 reference(s) — clash_mmo/game/core/matchmaking.py
- `players[user_id]["losses"]` — 2 reference(s) — clash_mmo/game/core/matchmaking.py
- `players[user_id]["rating"]` — 2 reference(s) — clash_mmo/game/core/matchmaking.py
- `players[user_id]["highest_rating"]` — 2 reference(s) — clash_mmo/game/core/matchmaking.py

## Core Resource Keys

- `clan_xp` — profile resource field
- `dark_elixir` — profile resource field
- `elixir` — profile resource field
- `gems` — profile resource field
- `glowy_ore` — profile resource field
- `gold` — profile resource field
- `raid_medals` — profile resource field
- `shiny_ore` — profile resource field
- `starry_ore` — profile resource field
