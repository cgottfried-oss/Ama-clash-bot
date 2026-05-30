# BALANCE TABLES GENERATED

Generated from literal Python balance tables where available.

# clash_mmo/game/progression/costs.py

# clash_mmo/game/raids/chests.py

# clash_mmo/config/economy_config.py

## SHOP_ITEMS

### training_potion
```json
{'name': 'Training Potion', 'cost': 450, 'description': 'Use /useitem training_potion to empower your next PvE or raid attack: +15% Gold, +15% Clan XP, and +10% Elixir.', 'type': 'combat_boost_charges', 'charges': 1, 'gold_multiplier': 1.15, 'xp_multiplier': 1.15, 'elixir_multiplier': 1.1, 'required_th': 3}
```

### resource_potion
```json
{'name': 'Resource Potion', 'cost': 400, 'description': 'Use /useitem resource_potion to empower your next farm run: +20% Gold, +20% Elixir, and a small chance at Dark Elixir.', 'type': 'farm_boost_charges', 'charges': 1, 'gold_multiplier': 1.2, 'elixir_multiplier': 1.2, 'dark_elixir_bonus_chance': 0.15, 'required_th': 3}
```

### builder_potion
```json
{'name': 'Builder Potion', 'cost': 1500, 'description': 'Use /useitem builder_potion to clear your Farm, Train, RaidVillage,RaidUser and BossAttack cooldowns once. Has a 30-minute use cooldown.', 'type': 'cooldown_clear', 'use_cooldown_seconds': 1800, 'required_th': 4}
```

### guard_shield
```json
{'name': 'Guard Shield', 'cost': 500, 'description': 'Passive item. Automatically blocks the next successful /raiduser attack against your village, then breaks.', 'type': 'raiduser_defense', 'required_th': 4}
```

### builder_crate
```json
{'name': 'Builder Crate', 'cost': 600, 'description': 'Use /useitem builder_crate to gain bonus Gold and Clan XP toward Town Hall progression.', 'type': 'progression_bundle', 'gold': 350, 'clan_xp': 75, 'required_th': 3}
```

### raid_medal_pack
```json
{'name': 'Raid Medal Pack', 'cost': 700, 'description': 'Use /useitem raid_medal_pack to gain 10 Raid Medals.', 'type': 'raid_medals', 'raid_medals': 10, 'required_th': 5}
```

### hero_tome
```json
{'name': 'Hero Tome', 'cost': 750, 'description': 'Use /useitem hero_tome to grant your active hero bonus XP.', 'type': 'hero_xp', 'hero_xp': 100, 'required_th': 4}
```

### dark_elixir_flask
```json
{'name': 'Dark Elixir Flask', 'cost': 800, 'description': 'Use /useitem dark_elixir_flask to gain 100 Dark Elixir.', 'type': 'dark_elixir', 'dark_elixir': 100, 'required_th': 7}
```

### ore_pouch
```json
{'name': 'Ore Pouch', 'cost': 900, 'description': 'Use /useitem ore_pouch to receive 3-7 Shiny Ore, with a small chance for 1 Glowy Ore.', 'type': 'ore_bundle', 'shiny_ore_min': 3, 'shiny_ore_max': 7, 'glowy_ore_chance': 0.12, 'glowy_ore_amount': 1, 'required_th': 8}
```

### chest_key
```json
{'name': 'Chest Key', 'cost': 1000, 'description': 'Use /useitem chest_key to receive one bonus chest roll.', 'type': 'chest_key', 'required_th': 5}
```
