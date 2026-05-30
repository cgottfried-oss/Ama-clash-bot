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
