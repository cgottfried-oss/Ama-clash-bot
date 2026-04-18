# th_caps.py
# Baseline Town Hall cap table for Upgrade Advisor
# Start with TH 9-18 and fill categories in phases.

TH_CAPS = {
    9: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    10: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    11: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    12: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    13: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    14: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    15: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    16: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    17: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
    18: {
        "heroes": {},
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
        "walls": {"count": 0, "max_level": 0},
    },
}

def get_th_caps(th_level: int) -> dict:
    return TH_CAPS.get(th_level, {})


def get_category_caps(th_level: int, category: str) -> dict:
    return TH_CAPS.get(th_level, {}).get(category, {})


def get_item_cap(th_level: int, category: str, item_name: str, default=None):
    return TH_CAPS.get(th_level, {}).get(category, {}).get(item_name, default)
    
"Air Defense": {"count": 4, "max_level": 13},
"Cannon": {"count": 7, "max_level": 21},
"Bomb": {"count": 8, "max_level": 11},

"Barbarian King": 75,
"Archer Queen": 75,
"Balloon": 10,
"Freeze Spell": 7,
"L.A.S.S.I": 10,

"Laboratory": 12,
"Clan Castle": 9,
"Army Camp": {"count": 4, "max_level": 11},
"Barracks": {"count": 1, "max_level": 16},
"Dark Barracks": {"count": 1, "max_level": 10},
"Workshop": 5,
"Pet House": 4,
"Blacksmith": 6,

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