EQUIPMENT_SLOTS = [
    "weapon",
    "armor",
    "relic",
]


HERO_IDS = [
    "king",
    "queen",
    "warden",
]


GEAR_CATALOG = {
    # ============================================================
    # KING WEAPONS
    # ============================================================
    "king_iron_cleaver": {
        "name": "Iron Cleaver",
        "hero": "king",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 5},
    },
    "king_raider_axe": {
        "name": "Raider Axe",
        "hero": "king",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 4, "crit": 0.01},
    },
    "king_warborn_blade": {
        "name": "Warborn Blade",
        "hero": "king",
        "slot": "weapon",
        "rarity": "rare",
        "stats": {"attack": 8, "crit": 0.03},
    },
    "king_titan_maul": {
        "name": "Titan Maul",
        "hero": "king",
        "slot": "weapon",
        "rarity": "epic",
        "stats": {"attack": 13, "crit": 0.05},
    },
    "king_crownbreaker": {
        "name": "Crownbreaker",
        "hero": "king",
        "slot": "weapon",
        "rarity": "legendary",
        "stats": {"attack": 21, "crit": 0.10, "health": 40},
    },

    # ============================================================
    # KING ARMOR
    # ============================================================
    "king_leather_guard": {
        "name": "Leather Guard",
        "hero": "king",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 3, "health": 15},
    },
    "king_raider_plate": {
        "name": "Raider Plate",
        "hero": "king",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 4, "health": 10},
    },
    "king_warborn_armor": {
        "name": "Warborn Armor",
        "hero": "king",
        "slot": "armor",
        "rarity": "rare",
        "stats": {"defense": 7, "health": 35},
    },
    "king_guardian_plate": {
        "name": "Guardian Plate",
        "hero": "king",
        "slot": "armor",
        "rarity": "epic",
        "stats": {"defense": 12, "health": 70},
    },
    "king_immortal_bulwark": {
        "name": "Immortal Bulwark",
        "hero": "king",
        "slot": "armor",
        "rarity": "legendary",
        "stats": {"defense": 20, "health": 150},
    },

    # ============================================================
    # KING RELICS
    # ============================================================
    "king_training_charm": {
        "name": "Training Charm",
        "hero": "king",
        "slot": "relic",
        "rarity": "common",
        "stats": {"speed": 1},
    },
    "king_battle_totem": {
        "name": "Battle Totem",
        "hero": "king",
        "slot": "relic",
        "rarity": "common",
        "stats": {"attack": 2},
    },
    "king_berserker_idol": {
        "name": "Berserker Idol",
        "hero": "king",
        "slot": "relic",
        "rarity": "rare",
        "stats": {"attack": 4, "crit": 0.03},
    },
    "king_ancient_warhorn": {
        "name": "Ancient Warhorn",
        "hero": "king",
        "slot": "relic",
        "rarity": "epic",
        "stats": {"attack": 7, "health": 30},
    },
    "king_eternal_crown": {
        "name": "Eternal Crown",
        "hero": "king",
        "slot": "relic",
        "rarity": "legendary",
        "stats": {"attack": 10, "crit": 0.07, "health": 80},
    },

    # ============================================================
    # QUEEN WEAPONS
    # ============================================================
    "queen_hunter_bow": {
        "name": "Hunter Bow",
        "hero": "queen",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 5},
    },
    "queen_ash_shortbow": {
        "name": "Ash Shortbow",
        "hero": "queen",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 4, "speed": 1},
    },
    "queen_warborn_crossbow": {
        "name": "Warborn Crossbow",
        "hero": "queen",
        "slot": "weapon",
        "rarity": "rare",
        "stats": {"attack": 8, "crit": 0.04},
    },
    "queen_moonpiercer": {
        "name": "Moonpiercer",
        "hero": "queen",
        "slot": "weapon",
        "rarity": "epic",
        "stats": {"attack": 12, "crit": 0.08},
    },
    "queen_starfall_bow": {
        "name": "Starfall Bow",
        "hero": "queen",
        "slot": "weapon",
        "rarity": "legendary",
        "stats": {"attack": 19, "crit": 0.14, "speed": 2},
    },

    # ============================================================
    # QUEEN ARMOR
    # ============================================================
    "queen_scout_leathers": {
        "name": "Scout Leathers",
        "hero": "queen",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 2, "health": 10, "speed": 1},
    },
    "queen_ranger_cloak": {
        "name": "Ranger Cloak",
        "hero": "queen",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 3, "health": 12},
    },
    "queen_shadow_armor": {
        "name": "Shadow Armor",
        "hero": "queen",
        "slot": "armor",
        "rarity": "rare",
        "stats": {"defense": 6, "health": 25, "speed": 1},
    },
    "queen_moonveil": {
        "name": "Moonveil",
        "hero": "queen",
        "slot": "armor",
        "rarity": "epic",
        "stats": {"defense": 10, "health": 45, "crit": 0.03},
    },
    "queen_celestial_raiment": {
        "name": "Celestial Raiment",
        "hero": "queen",
        "slot": "armor",
        "rarity": "legendary",
        "stats": {"defense": 16, "health": 90, "crit": 0.06, "speed": 2},
    },

    # ============================================================
    # QUEEN RELICS
    # ============================================================
    "queen_focus_charm": {
        "name": "Focus Charm",
        "hero": "queen",
        "slot": "relic",
        "rarity": "common",
        "stats": {"crit": 0.02},
    },
    "queen_hawk_feather": {
        "name": "Hawk Feather",
        "hero": "queen",
        "slot": "relic",
        "rarity": "common",
        "stats": {"speed": 1},
    },
    "queen_eagle_eye": {
        "name": "Eagle Eye",
        "hero": "queen",
        "slot": "relic",
        "rarity": "rare",
        "stats": {"crit": 0.05},
    },
    "queen_shadow_orb": {
        "name": "Shadow Orb",
        "hero": "queen",
        "slot": "relic",
        "rarity": "epic",
        "stats": {"attack": 5, "crit": 0.07},
    },
    "queen_starseeker_gem": {
        "name": "Starseeker Gem",
        "hero": "queen",
        "slot": "relic",
        "rarity": "legendary",
        "stats": {"attack": 8, "crit": 0.12, "speed": 2},
    },

    # ============================================================
    # WARDEN WEAPONS
    # ============================================================
    "warden_oak_staff": {
        "name": "Oak Staff",
        "hero": "warden",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 4, "health": 10},
    },
    "warden_apprentice_wand": {
        "name": "Apprentice Wand",
        "hero": "warden",
        "slot": "weapon",
        "rarity": "common",
        "stats": {"attack": 5},
    },
    "warden_arcane_staff": {
        "name": "Arcane Staff",
        "hero": "warden",
        "slot": "weapon",
        "rarity": "rare",
        "stats": {"attack": 8, "health": 20},
    },
    "warden_void_scepter": {
        "name": "Void Scepter",
        "hero": "warden",
        "slot": "weapon",
        "rarity": "epic",
        "stats": {"attack": 11, "crit": 0.06, "health": 30},
    },
    "warden_eternal_staff": {
        "name": "Eternal Staff",
        "hero": "warden",
        "slot": "weapon",
        "rarity": "legendary",
        "stats": {"attack": 18, "crit": 0.08, "health": 100},
    },

    # ============================================================
    # WARDEN ARMOR
    # ============================================================
    "warden_robed_guard": {
        "name": "Robed Guard",
        "hero": "warden",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 2, "health": 20},
    },
    "warden_apprentice_robes": {
        "name": "Apprentice Robes",
        "hero": "warden",
        "slot": "armor",
        "rarity": "common",
        "stats": {"defense": 3, "health": 15},
    },
    "warden_arcane_robes": {
        "name": "Arcane Robes",
        "hero": "warden",
        "slot": "armor",
        "rarity": "rare",
        "stats": {"defense": 6, "health": 40},
    },
    "warden_guardian_mantle": {
        "name": "Guardian Mantle",
        "hero": "warden",
        "slot": "armor",
        "rarity": "epic",
        "stats": {"defense": 10, "health": 75},
    },
    "warden_celestial_mantle": {
        "name": "Celestial Mantle",
        "hero": "warden",
        "slot": "armor",
        "rarity": "legendary",
        "stats": {"defense": 16, "health": 150, "speed": 1},
    },

    # ============================================================
    # WARDEN RELICS
    # ============================================================
    "warden_mana_charm": {
        "name": "Mana Charm",
        "hero": "warden",
        "slot": "relic",
        "rarity": "common",
        "stats": {"health": 20},
    },
    "warden_lesser_orb": {
        "name": "Lesser Orb",
        "hero": "warden",
        "slot": "relic",
        "rarity": "common",
        "stats": {"attack": 2, "health": 10},
    },
    "warden_arcane_orb": {
        "name": "Arcane Orb",
        "hero": "warden",
        "slot": "relic",
        "rarity": "rare",
        "stats": {"attack": 4, "health": 35},
    },
    "warden_void_crystal": {
        "name": "Void Crystal",
        "hero": "warden",
        "slot": "relic",
        "rarity": "epic",
        "stats": {"attack": 6, "crit": 0.04, "health": 50},
    },
    "warden_eternal_core": {
        "name": "Eternal Core",
        "hero": "warden",
        "slot": "relic",
        "rarity": "legendary",
        "stats": {"attack": 9, "crit": 0.08, "health": 120},
    },
}