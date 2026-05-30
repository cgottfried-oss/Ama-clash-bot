# CLASH MMO DEVELOPER GUIDE

This guide is generated from the current repository documentation and source-audit outputs.

## Core rule

`mmo_state.json` is the primary source of truth for player progression. New player-facing systems should read/write MMO profile state, not legacy wallet/shop JSON files.

## Command registration

Slash commands are registered from `clash_mmo/commands/__init__.py` through `register_clash_mmo_commands(bot, ctx)`.

## Important generated references

- `COMMAND_REFERENCE.md` — generated command inventory
- `COMMAND_FILE_MAP.md` — command-to-file map
- `ARCHITECTURE_AUDIT.md` — large files, import hotspots, MMO-state pattern counts
- `MMO_STATE_SCHEMA_GENERATED.md` — generated state/profile key inventory
- `RESOURCE_FLOW_GENERATED.md` — generated resource key flow map
- `BALANCE_TABLES_GENERATED.md` — extracted literal balance tables

## High-value maintenance rules

1. Prefer shared helpers under `clash_mmo/game/core/` over copy-pasted profile parsing.
2. Keep player-facing command names stable unless intentionally migrating commands.
3. Preserve compatibility aliases only when they protect existing state or imports.
4. Do not reintroduce `/steal`; `/raiduser` is the PvP loot command.
5. Use generated docs after any command/schema/balance change.

## Current command count

Total commands discovered: 82

## Current architecture snapshot

# ARCHITECTURE AUDIT

## Large Files

- `clash_mmo/commands/core_economy_commands.py` — 1120 lines
- `clash_mmo/commands/pve_commands.py` — 811 lines
- `clash_mmo/commands/admin_commands.py` — 668 lines
- `clash_mmo/services/economy.py` — 632 lines
- `clash_mmo/commands/shop_commands.py` — 532 lines
- `clash_mmo/commands/market_commands.py` — 531 lines
- `clash_mmo/game/marketplace/service.py` — 515 lines
- `clash_mmo/commands/pvp_commands.py` — 476 lines
- `clan_bot/commands/linking_commands.py` — 457 lines
- `clash_mmo/commands/raid_commands.py` — 446 lines
- `clan_bot/war/images.py` — 378 lines
- `clash_mmo/game/equipment/gear_catalog.py` — 366 lines
- `clan_bot/renderers/emoji_icons.py` — 363 lines
- `clash_mmo/commands/gear_commands.py` — 332 lines
- `clash_mmo/commands/clan_economy_commands.py` — 318 lines
- `clash_mmo/commands/heroes_commands.py` — 288 lines
- `clan_bot/war/summaries.py` — 255 lines

## MMO State / Domain Pattern Counts

- `inventory` — 207
- `profile.get` — 188
- `heroes` — 133
- `cooldowns` — 114
- `update_mmo_state` — 109
- `profile[` — 107
- `ensure_player_profile` — 76
- `cosmetics` — 68
- `load_mmo_state` — 60
- `boosts` — 60
- `marketplace` — 42
- `territories` — 38

## Internal Dependency Hotspots

- `clash_mmo.game.state` imported by 18 module(s)
- `clash_mmo.game.core.profiles` imported by 15 module(s)
- `clash_mmo.game.heroes` imported by 7 module(s)
- `clash_mmo.game.equipment.gear_catalog` imported by 6 module(s)
- `clash_mmo.game.equipment.service` imported by 5 module(s)
- `clan_bot.renderers.html_renderer` imported by 5 module(s)
- `clash_mmo.game.core.inventory` imported by 4 module(s)
- `clash_mmo.game.heroes.catalog` imported by 4 module(s)
- `clash_mmo.game.heroes.loadouts` imported by 3 module(s)
- `clash_mmo.game.seasonal_system` imported by 2 module(s)
- `clash_mmo.game.pve.chests` imported by 2 module(s)

## Suggested Next Refactor Targets

1. Continue reducing high-line-count command modules.
2. Keep moving direct `profile[...]` parsing into shared helpers.
3. Keep all player-facing docs generated from source with `tools/generate_clash_mmo_docs.py`.
4. Keep black market, territory, cosmetics, and system guide documented together.


## Current schema snapshot

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
- `players[user_id]["inventory"]` — 18 reference(s) — clash_mmo/commands/admin_commands.py, clash_mmo/commands/core_economy_commands.py, clash_mmo/commands/gear_commands.py, clash_mmo/commands/market_commands.py, clash_mmo/commands/pve_commands
