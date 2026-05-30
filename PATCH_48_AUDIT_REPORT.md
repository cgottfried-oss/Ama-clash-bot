# PATCH 48 AUDIT REPORT

## Actual code changes
- Added `clash_mmo/commands/systems_guide_commands.py`
- Registered `/systemguide`
- Improved `/blackmarket` embed with buying instructions
- Hardened `/blackmarketbuy` to use `ensure_player_profile()` instead of creating a partial profile dict
- Updated command reference/map docs if present

## Why this patch matters
Patch 47 made territories, cosmetics, and black market usable. Patch 48 makes those systems understandable inside Discord.

## System purposes
- Territories: persistent clan map-control and timed Gold income.
- Clan War: war/match performance, MVP, seasonal war rewards, and war attack tracking.
- Cosmetics: non-inflationary flex/identity rewards with small visible perks.
- Black Market: rotating rare-gear shop and Gold sink.
