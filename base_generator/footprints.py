from __future__ import annotations

# Practical tile-footprint approximations for blueprint rendering.
# These are for manual build guidance, not official Supercell layout serialization.
BUILDING_FOOTPRINTS = {
    "Town Hall": (4, 4),
    "Clan Castle": (3, 3),
    "Monolith": (2, 2),
    "Eagle": (4, 4),
    "Scattershot A": (3, 3),
    "Scattershot B": (3, 3),
    "Inferno A": (2, 2),
    "Inferno B": (2, 2),
    "Inferno C": (2, 2),
    "Spell Tower A": (2, 2),
    "Spell Tower B": (2, 2),
    "Firespitters": (3, 3),
    "Hero Hall": (4, 4),
    "Air Defenses": (3, 3),
    "X-Bows": (3, 3),
    "Bomb Towers": (2, 2),
    "Builder Huts": (2, 2),
    "Merged Defenses": (3, 3),
    "Ricochet Cannons": (3, 3),
    "Multi-Archer Towers": (3, 3),
}

LABELS = {
    "Town Hall": "TH",
    "Clan Castle": "CC",
    "Monolith": "MO",
    "Eagle": "EA",
    "Scattershot A": "S1",
    "Scattershot B": "S2",
    "Inferno A": "I1",
    "Inferno B": "I2",
    "Inferno C": "I3",
    "Spell Tower A": "ST",
    "Spell Tower B": "ST",
    "Firespitters": "FS",
    "Hero Hall": "HH",
    "Air Defenses": "AD",
    "X-Bows": "XB",
    "Bomb Towers": "BT",
    "Builder Huts": "BH",
    "Merged Defenses": "MD",
    "Ricochet Cannons": "RC",
    "Multi-Archer Towers": "MA",
}

def footprint_for(building: str) -> tuple[int, int]:
    return BUILDING_FOOTPRINTS.get(building, (2, 2))

def label_for(building: str) -> str:
    return LABELS.get(building, building[:2].upper())
