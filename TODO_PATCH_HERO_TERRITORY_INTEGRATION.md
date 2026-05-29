# TODO: Hero and Territory Integration

Flagged during Batch 3 Patch 68 upload while reviewing `clash_mmo/commands/heroes_commands.py` and `clash_mmo/commands/territory_commands.py`.

Observation:

- Hero system already exposes `get_total_hero_power(profile)`.
- Territory battles currently use static values:
  - `attacker_power=120`
  - `defender_power=100`

Future patch:

- Use the player's actual hero power for territory battles.
- Consider active hero, hero levels, hero gear, Town Hall, clan bonuses, league/ranked progression, and cosmetic perks.

Goal:

Connect hero progression to territory combat so upgrading heroes has a clear gameplay purpose beyond profile display and gear drops.
