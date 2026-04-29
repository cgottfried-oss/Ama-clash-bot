from __future__ import annotations

from th_caps import get_cap_category_group

TH_CAP_NAME_MAP: dict[str, tuple[str, str]] = {
    # Heroes
    "barbarian_king": ("heroes", "Barbarian King"),
    "archer_queen": ("heroes", "Archer Queen"),
    "grand_warden": ("heroes", "Grand Warden"),
    "royal_champion": ("heroes", "Royal Champion"),
    "minion_prince": ("heroes", "Minion Prince"),
    "dragon_duke": ("heroes", "Dragon Duke"),
    # Troops
    "healers": ("troops", "Healer"),
    "balloons": ("troops", "Balloon"),
    "dragons": ("troops", "Dragon"),
    "electro_dragon": ("troops", "Electro Dragon"),
    "hog_rider": ("troops", "Hog Rider"),
    "miners": ("troops", "Miner"),
    "root_rider": ("troops", "Root Rider"),
    "apprentice_warden": ("troops", "Apprentice Warden"),
    # Spells
    "rage_spell": ("spells", "Rage Spell"),
    "freeze_spell": ("spells", "Freeze Spell"),
    "invisibility_spell": ("spells", "Invisibility Spell"),
    "recall_spell": ("spells", "Recall Spell"),
    # Pets
    "lassi": ("pets", "L.A.S.S.I"),
    "mighty_yak": ("pets", "Mighty Yak"),
    "electro_owl": ("pets", "Electro Owl"),
    "unicorn": ("pets", "Unicorn"),
    "phoenix": ("pets", "Phoenix"),
    "diggy": ("pets", "Diggy"),
    "poison_lizard": ("pets", "Poison Lizard"),
    "frosty": ("pets", "Frosty"),
    "spirit_fox": ("pets", "Spirit Fox"),
    "angry_jelly": ("pets", "Angry Jelly"),
    "sneezy": ("pets", "Sneezy"),
    "greedy_raven": ("pets", "Greedy Raven"),
    # Siege machines
    "wall_wrecker": ("siege_machines", "Wall Wrecker"),
    "battle_blimp": ("siege_machines", "Battle Blimp"),
    "stone_slammer": ("siege_machines", "Stone Slammer"),
    "siege_barracks": ("siege_machines", "Siege Barracks"),
    "log_launcher": ("siege_machines", "Log Launcher"),
    "flame_flinger": ("siege_machines", "Flame Flinger"),
    "battle_drill": ("siege_machines", "Battle Drill"),
    "troop_launcher": ("siege_machines", "Troop Launcher"),
    # Offense / core buildings
    "army_camp": ("offense_buildings", "Army Camp"),
    "clan_castle": ("core_buildings", "Clan Castle"),
    "laboratory": ("core_buildings", "Laboratory"),
    "spell_factory": ("offense_buildings", "Spell Factory"),
    "pet_house": ("offense_buildings", "Pet House"),
    "blacksmith": ("core_buildings", "Blacksmith"),
    "hero_hall": ("core_buildings", "Hero Hall"),
    # Economy / defenses
    "gold_mine": ("resource_buildings", "Gold Mine"),
    "elixir_collector": ("resource_buildings", "Elixir Collector"),
    "dark_elixir_drill": ("resource_buildings", "Dark Elixir Drill"),
    "gold_storage": ("resource_buildings", "Gold Storage"),
    "elixir_storage": ("resource_buildings", "Elixir Storage"),
    "air_defense": ("defenses", "Air Defense"),
    "inferno_tower": ("defenses", "Inferno Tower"),
    "x_bow": ("defenses", "X-Bow"),
    "scattershot": ("defenses", "Scattershot"),
    "air_sweeper": ("defenses", "Air Sweeper"),
    "hidden_tesla": ("defenses", "Hidden Tesla"),
    "bomb_tower": ("defenses", "Bomb Tower"),
    "spell_tower": ("defenses", "Spell Tower"),
    "monolith": ("defenses", "Monolith"),
    "multi_archer_tower": ("defenses", "Multi-Archer Tower"),
    "ricochet_cannon": ("defenses", "Ricochet Cannon"),
    "multi_gear_tower": ("defenses", "Multi-Gear Tower"),
    "firespitter": ("defenses", "Firespitter"),
    "super_wizard_tower": ("defenses", "Super Wizard Tower"),
    "revenge_tower": ("defenses", "Revenge Tower"),
    # Traps
    "bomb": ("traps", "Bomb"),
    "giant_bomb": ("traps", "Giant Bomb"),
    "air_bomb": ("traps", "Air Bomb"),
    "seeking_air_mine": ("traps", "Seeking Air Mine"),
    "spring_trap": ("traps", "Spring Trap"),
    "skeleton_trap": ("traps", "Skeleton Trap"),
    "tornado_trap": ("traps", "Tornado Trap"),
    "giga_bomb": ("traps", "Giga Bomb"),
}



ACCOUNT_COMPLETION_CATEGORIES = get_cap_category_group("account_completion")

ACCOUNT_COMPLETION_CATEGORY_LABELS = {
    "heroes": "Heroes",
    "pets": "Pets",
    "troops": "Troops",
    "spells": "Spells",
    "siege_machines": "Siege",
    "offense_buildings": "Offense Buildings",
    "core_buildings": "Core Buildings",
    "defenses": "Defenses",
    "traps": "Traps",
    "resource_buildings": "Resources",
    "army_buildings": "Army Buildings",
    "walls": "Walls",
}

RECOMMENDATION_PRIORITIES = {
    "hero": 0,
    "pet": 1,
    "troop": 2,
    "spell": 3,
    "siege": 4,
    "building": 5,
    "defense": 6,
    "economy": 7,
    "trap": 8,
}

TH_CAP_LOOKUP_TO_KEY = {value: key for key, value in TH_CAP_NAME_MAP.items()}

ARMY_BUILDING_CAP_NAME_ALIASES: dict[str, str] = {
    "Army Camp": "army_camp",
    "Barracks": "barracks",
    "Clan Castle": "clan_castle",
    "Laboratory": "laboratory",
    "Spell Factory": "spell_factory",
    "Hero Hall": "hero_hall",
    "Dark Barracks": "dark_barracks",
    "Dark Spell Factory": "dark_spell_factory",
    "Blacksmith": "blacksmith",
    "Workshop": "workshop",
    "Pet House": "pet_house",
}


def rebuild_th_cap_lookup() -> dict[tuple[str, str], str]:
    lookup = {value: key for key, value in TH_CAP_NAME_MAP.items()}
    for item_name, item_key in ARMY_BUILDING_CAP_NAME_ALIASES.items():
        lookup.setdefault(("army_buildings", item_name), item_key)
    return lookup


TH_CAP_LOOKUP_TO_KEY = rebuild_th_cap_lookup()
OFFENSE_CORE_KEYS = {
    "army_camp",
    "clan_castle",
    "laboratory",
    "healers",
    "balloons",
    "dragons",
    "hog_rider",
    "rage_spell",
    "freeze_spell",
}

BUILDER_CORE_KEYS = {
    "army_camp",
    "clan_castle",
    "laboratory",
    "spell_factory",
    "pet_house",
    "blacksmith",
    "hero_hall",
}

# Last-resort fallback only. /trackcopies now resolves copy counts dynamically from TH_CAPS
# first, then scans other Town Halls before touching this table.
MIN_COPY_FALLBACK_COUNTS: dict[str, int] = {
    "air_defense": 4,
    "x_bow": 4,
    "inferno_tower": 2,
    "scattershot": 2,
    "air_sweeper": 2,
    "hidden_tesla": 2,
    "bomb_tower": 2,
    "spell_tower": 2,
    "multi_archer_tower": 2,
    "ricochet_cannon": 2,
    "firespitter": 2,
    "super_wizard_tower": 2,
    "bomb": 2,
    "giant_bomb": 2,
    "air_bomb": 2,
    "seeking_air_mine": 2,
    "spring_trap": 2,
    "skeleton_trap": 2,
}