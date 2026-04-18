# th_caps.py

# Baseline Town Hall cap table for Upgrade Advisor
# Phase 1: Heroes only

TH_CAPS = {
    9: {
        "heroes": {
            "Barbarian King": 30,
            "Archer Queen": 30,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 250, "max_level": 10},
    },
    10: {
        "heroes": {
            "Barbarian King": 40,
            "Archer Queen": 40,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 275, "max_level": 11},
    },
    11: {
        "heroes": {
            "Barbarian King": 50,
            "Archer Queen": 50,
            "Grand Warden": 20,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 300, "max_level": 12},
    },
    12: {
        "heroes": {
            "Barbarian King": 65,
            "Archer Queen": 65,
            "Grand Warden": 40,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 300, "max_level": 13},
    },
    13: {
        "heroes": {
            "Barbarian King": 75,
            "Archer Queen": 75,
            "Grand Warden": 50,
            "Royal Champion": 25,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 300, "max_level": 14},
    },
    14: {
        "heroes": {
            "Barbarian King": 85,
            "Archer Queen": 85,
            "Grand Warden": 55,
            "Royal Champion": 30,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 325, "max_level": 15},
    },
    15: {
        "heroes": {
            "Barbarian King": 90,
            "Archer Queen": 90,
            "Grand Warden": 60,
            "Royal Champion": 35,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 325, "max_level": 16},
    },
    16: {
        "heroes": {
            "Barbarian King": 95,
            "Archer Queen": 95,
            "Grand Warden": 65,
            "Royal Champion": 40,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 325, "max_level": 17},
    },
    17: {
        "heroes": {
            "Barbarian King": 100,
            "Archer Queen": 100,
            "Grand Warden": 70,
            "Royal Champion": 45,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 350, "max_level": 18},
    },
    18: {
        "heroes": {
            "Barbarian King": 105,
            "Archer Queen": 105,
            "Grand Warden": 80,
            "Royal Champion": 55,
        },
        "pets": {},
        "troops": {},
        "spells": {},
        "siege_machines": {},
        "offense_buildings": {},
        "defenses": {},
        "traps": {},
        "resource_buildings": {},
        "army_buildings": {},
        "core_buildings": {},
        "walls": {"count": 350, "max_level": 19},
    },
}


def get_th_caps(th_level: int) -> dict:
    return TH_CAPS.get(th_level, {})


def get_category_caps(th_level: int, category: str) -> dict:
    return TH_CAPS.get(th_level, {}).get(category, {})


def get_item_cap(th_level: int, category: str, item_name: str, default=None):
    return TH_CAPS.get(th_level, {}).get(category, {}).get(item_name, default)


def normalize_cap_entry(entry):
    if isinstance(entry, dict):
        return {
            "count": entry.get("count", 1),
            "max_level": entry.get("max_level", 0),
        }
    return {
        "count": 1,
        "max_level": int(entry or 0),
    }
