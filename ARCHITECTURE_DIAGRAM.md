# ARCHITECTURE DIAGRAM

```text
Discord Slash Commands
        |
        v
clash_mmo/commands/
        |
        +--> core_economy_commands.py      (/village, /daily-style economy helpers, /cooldowns, /gems)
        +--> village_commands.py           (/daily, /farm, /train, /raidvillage, /upgradehall)
        +--> pvp_commands.py               (/raiduser)
        +--> raid_commands.py              (/bossattack and raid boss loop)
        +--> shop_commands.py              (/shop, /buy, /inventory, /useitem)
        +--> market_commands.py            (/market, /blackmarket, /blackmarketbuy, trades)
        +--> territory_commands.py         (/territorymap, /claimterritory, /attackterritory, /territoryincome)
        +--> cosmetic_commands.py          (/cosmetics, /equipcosmetic, /grantcosmetic)
        +--> systems_guide_commands.py     (/systemguide, /glossary)
        |
        v
Shared Game Logic
        |
        +--> clash_mmo/game/core/           profiles, resources, cooldowns, inventory, admin helpers
        +--> clash_mmo/game/raids/          boss/raid/chest/reward mechanics
        +--> clash_mmo/game/heroes/         hero unlocks/loadouts/progression
        +--> clash_mmo/game/equipment/      gear catalog/equip/effective stats
        +--> clash_mmo/game/marketplace/    listings, trades, black market, tax/gold sinks
        +--> clash_mmo/game/territory/      regions, conquest, income
        +--> clash_mmo/game/cosmetics/      catalog, grant/equip, formatting/perks
        |
        v
Persistence
        |
        +--> mmo_state.json                 primary player/source-of-truth state
        +--> legacy compatibility paths     kept only where needed during migration
```
