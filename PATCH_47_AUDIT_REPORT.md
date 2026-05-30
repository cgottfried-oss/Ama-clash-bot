# PATCH 47 AUDIT REPORT

## Why territories exist

Territories are intended to be a clan-level map-control loop:
- `/territorymap` shows the regions and owners.
- `/claimterritory` claims an unowned/target region for the guild.
- `/attackterritory` contests a region and can flip ownership.
- `/territoryincome` turns owned territory into Gold income.

Patch 47 made this clearer in the map embed and added a 6-hour income cooldown so territory income cannot be spammed endlessly.

## Why clan war exists

Clan war is separate from the MMO territory map. Clan war is tied to real/seasonal clan performance and MVP-style rewards:
- war status/start/end/attack commands track clan-war activity.
- war rewards feed Gold and MVP systems.
- territory is map ownership; clan war is match/event performance.

## Cosmetics before Patch 47

Cosmetics were mostly visual and `/grantcosmetic` could fail because the service returned True/False while the command expected a result dict.

## Cosmetics after Patch 47

- `/grantcosmetic` now receives a consistent result dict.
- Cosmetics now expose small perk metadata.
- `/cosmetics` shows active cosmetic perks when equipped.

Cosmetics remain mostly identity/flex rewards, but now they can communicate small gameplay-flavored utility.

## Black Market before Patch 47

`/blackmarket` only displayed randomly rotated item IDs. There was no buy path, so it was not meaningfully usable.

## Black Market after Patch 47

- Black market stock now includes prices and item types.
- `/blackmarket` shows item IDs and Gold prices.
- New `/blackmarketbuy item:<id>` command lets players buy gear from the black market.
- Purchases sink Gold into marketplace `gold_sunk`.

## Files changed

- `clash_mmo/game/cosmetics/catalog.py`
- `clash_mmo/game/cosmetics/service.py`
- `clash_mmo/game/cosmetics/formatting.py`
- `clash_mmo/game/cosmetics/__init__.py`
- `clash_mmo/commands/cosmetic_commands.py`
- `clash_mmo/game/marketplace/black_market.py`
- `clash_mmo/game/marketplace/formatting.py`
- `clash_mmo/game/marketplace/__init__.py`
- `clash_mmo/commands/market_commands.py`
- `clash_mmo/commands/territory_commands.py`
