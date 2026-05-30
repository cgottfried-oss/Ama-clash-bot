# PATCH 58 AUDIT REPORT

## Actual code changes

- Added chance-based battle pass rewards for new resources:
  - Elixir
  - Dark Elixir
  - Shiny Ore
  - Glowy Ore
  - Starry Ore
- Added `roll_battle_pass_reward()`
- Updated battle pass reward formatter to display chance rewards.
- Updated `/claimpass` so chance rewards actually roll and are granted.
- Fixed cosmetics reward storage to use `cosmetics["owned"]["titles"]` and `cosmetics["owned"]["borders"]`.

## Why this patch matters

The battle pass existed before newer resources were fully meaningful. Patch 58 makes the battle pass participate in the newer economy by adding guaranteed and chance-based rewards for the expanded resource set.

## Current battle pass bonus philosophy

- Common resources like Elixir can be guaranteed.
- Dark Elixir and Shiny Ore appear as moderate bonus chances.
- Glowy Ore is rarer.
- Starry Ore is very rare.
