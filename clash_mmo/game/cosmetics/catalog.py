COSMETIC_TYPES = [
    "banner",
    "border",
    "title",
    "effect",
]


COSMETIC_CATALOG = {
    "starter_banner": {
        "name": "Starter Banner",
        "type": "banner",
        "rarity": "common",
        "bonuses": {"profile_flex": 1},
    },
    "bronze_border": {
        "name": "Bronze Border",
        "type": "border",
        "rarity": "common",
        "bonuses": {"profile_flex": 1},
    },
    "season_grinder": {
        "name": "Season Grinder",
        "type": "title",
        "rarity": "rare",
        "animated": False,
        "bonuses": {"daily_gold_bonus_pct": 1},
    },
    "legend_flames": {
        "name": "Legend Flames",
        "type": "effect",
        "rarity": "legendary",
        "animated": True,
        "bonuses": {"profile_flex": 5, "boss_gold_bonus_pct": 2},
    },
    "warborn_border": {
        "name": "Warborn Border",
        "type": "border",
        "rarity": "epic",
        "animated": True,
        "bonuses": {"war_flex": 3},
    },
}
