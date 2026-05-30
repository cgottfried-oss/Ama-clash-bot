# TODO ROADMAP

## Highest priority

1. Add integration tests around command registration.
2. Add a smoke-test script that imports every command module and validates `register_clash_mmo_commands`.
3. Finish replacing direct profile parsing in large command files with shared helpers.
4. Keep `/raiduser` as the PvP loot path and do not restore `/steal`.

## Gameplay systems

### Territories
- Add better territory battle scaling using real clan/player power.
- Add region-specific rewards beyond flat Gold.
- Add admin reset/season rotation tooling.

### Clan War
- Keep clan war as the war-performance/MVP loop.
- Document how war rewards connect to MMO Gold and cosmetics.
- Add war-season rewards if not already active.

### Cosmetics
- Expand cosmetic catalog.
- Keep perks small so cosmetics do not become mandatory power items.
- Add event/season cosmetic rewards.

### Black Market
- Add rotating stock persistence instead of pure random stock every command call.
- Add stock refresh timer.
- Add limited quantity purchases.

## Documentation

- Regenerate command docs after every command patch.
- Regenerate schema docs after every state-model patch.
- Regenerate balance docs after every reward/cost patch.
- Rebuild the player PDF from generated docs after major system changes.

## Technical debt

- Reduce large command files.
- Move more admin view rendering into helper modules.
- Add explicit migrations for old compatibility fields.
- Remove old compatibility aliases only after deployment is verified.
