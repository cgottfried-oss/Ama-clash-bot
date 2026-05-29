# TODO: Territory Power Scaling

Flagged during Batch 3 Patch 68 upload while reviewing `clash_mmo/commands/territory_commands.py`.

Current issue:

- `/attackterritory` uses hardcoded combat values:
  - `attacker_power=120`
  - `defender_power=100`

Future patch should calculate territory power from actual player/clan progression.

Possible inputs:

- Hero levels
- Equipped gear
- Town Hall level
- Clan upgrades / clan bank progress
- Ranked league progress
- Cosmetics perks if applicable
- Territory ownership bonuses

Goal:

Make territory battles feel connected to the rest of the Clash MMO progression loop instead of being static dice rolls.
