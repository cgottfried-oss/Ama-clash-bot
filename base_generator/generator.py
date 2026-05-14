from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from .rules import get_buildings, get_meta_rule, get_style_rules, normalize_choice

ALLOWED_META = {"root_rider", "fireball", "blimp", "air_spam", "hybrid"}
ALLOWED_STYLE = {"war", "cwl", "legend", "farming"}
ALLOWED_SYMMETRY = {"box", "diamond", "ring", "random"}

@dataclass
class BasePlan:
    townhall: int
    style: str
    anti_meta: str
    symmetry: str
    title: str
    score_seed: int
    created_at: str
    buildings: list[str]
    grid: list[list[str]]
    rules: list[str]
    style_rules: list[str]
    trap_plan: list[str]
    build_order: list[str]
    strengths: list[str]
    weaknesses: list[str]
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_grid(size: int = 13) -> list[list[str]]:
    return [["" for _ in range(size)] for _ in range(size)]


def _place(grid: list[list[str]], label: str, row: int, col: int):
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        grid[row][col] = label


def _layout_coordinates(symmetry: str, anti_meta: str) -> dict[str, tuple[int, int]]:
    if symmetry == "random":
        symmetry = random.choice(["box", "diamond", "ring"])

    coords = {
        "Town Hall": (6, 6),
        "Clan Castle": (6, 5),
        "Monolith": (5, 7),
        "Eagle": (7, 5),
        "Scattershot A": (4, 4),
        "Scattershot B": (8, 8),
        "Inferno A": (4, 8),
        "Inferno B": (8, 4),
        "Inferno C": (6, 9),
        "Spell Tower A": (5, 4),
        "Spell Tower B": (7, 8),
        "Firespitters": (3, 6),
        "Hero Hall": (9, 6),
        "Air Defenses": (3, 3),
        "X-Bows": (9, 9),
        "Bomb Towers": (6, 3),
        "Builder Huts": (3, 9),
        "Merged Defenses": (9, 3),
        "Ricochet Cannons": (2, 6),
        "Multi-Archer Towers": (10, 6),
    }

    if symmetry == "diamond":
        coords["Town Hall"] = (5, 6)
        coords["Clan Castle"] = (6, 6)
        coords["Monolith"] = (7, 6)
        coords["Eagle"] = (6, 4)
        coords["Scattershot A"] = (4, 6)
        coords["Scattershot B"] = (8, 6)
        coords["Inferno A"] = (6, 8)
        coords["Inferno B"] = (5, 4)
    elif symmetry == "ring":
        coords["Town Hall"] = (4, 7)
        coords["Clan Castle"] = (6, 6)
        coords["Monolith"] = (7, 7)
        coords["Eagle"] = (8, 4)
        coords["Scattershot A"] = (4, 4)
        coords["Scattershot B"] = (8, 8)
        coords["Inferno A"] = (3, 8)
        coords["Inferno B"] = (9, 4)

    if anti_meta == "root_rider":
        coords["Town Hall"] = (5, 7)
        coords["Monolith"] = (7, 5)
        coords["Clan Castle"] = (6, 6)
    elif anti_meta == "fireball":
        coords["Town Hall"] = (6, 7)
        coords["Monolith"] = (4, 4)
        coords["Scattershot A"] = (8, 4)
        coords["Scattershot B"] = (4, 9)
    elif anti_meta == "blimp":
        coords["Town Hall"] = (6, 8)
        coords["Spell Tower A"] = (6, 7)
        coords["Clan Castle"] = (7, 6)
    return coords


def _label_for(building: str) -> str:
    mapping = {
        "Town Hall": "TH", "Clan Castle": "CC", "Monolith": "MO", "Eagle": "EA",
        "Scattershot A": "S1", "Scattershot B": "S2", "Inferno A": "I1", "Inferno B": "I2",
        "Inferno C": "I3", "Spell Tower A": "ST", "Spell Tower B": "ST", "Firespitters": "FS",
        "Hero Hall": "HH", "Air Defenses": "AD", "X-Bows": "XB", "Bomb Towers": "BT",
        "Builder Huts": "BH", "Merged Defenses": "MD", "Ricochet Cannons": "RC", "Multi-Archer Towers": "MA",
    }
    return mapping.get(building, building[:2].upper())


def generate_base_plan(townhall: int = 16, style: str = "war", anti_meta: str = "root_rider", symmetry: str = "ring") -> BasePlan:
    townhall = int(townhall or 16)
    if townhall < 14 or townhall > 17:
        townhall = 16
    style = normalize_choice(style, "war", ALLOWED_STYLE)
    anti_meta = normalize_choice(anti_meta, "root_rider", ALLOWED_META)
    symmetry = normalize_choice(symmetry, "ring", ALLOWED_SYMMETRY)

    meta = get_meta_rule(anti_meta)
    buildings = get_buildings(townhall)
    grid = _empty_grid()
    coords = _layout_coordinates(symmetry, anti_meta)

    for building in buildings:
        base_name = building
        if building == "Scattershots":
            for b in ["Scattershot A", "Scattershot B"]:
                _place(grid, _label_for(b), *coords[b])
            continue
        if building == "Infernos":
            for b in ["Inferno A", "Inferno B", "Inferno C"]:
                _place(grid, _label_for(b), *coords[b])
            continue
        if building == "Spell Towers":
            for b in ["Spell Tower A", "Spell Tower B"]:
                _place(grid, _label_for(b), *coords[b])
            continue
        _place(grid, _label_for(base_name), *coords.get(base_name, (random.randint(2, 10), random.randint(2, 10))))

    trap_plan = [
        "Tornado Trap: place near the highest-value entry/drop zone, not dead center unless Town Hall is offset.",
        "Seeking Air Mines: layer on likely Blimp/Warden/Healer approach paths.",
        "Spring Traps: place in narrow ground lanes between compartments.",
        "Giant Bombs: pair with Bomb Towers or expected Hybrid/Root Rider convergence spots.",
        "Skeleton Traps: set ground for Root Rider/Hybrid, air for Blimp/Lalo-heavy metas.",
    ]
    if anti_meta == "blimp":
        trap_plan.insert(0, "Blimp-specific: Tornado + black mines should punish the cleanest Town Hall flight line.")
    if anti_meta == "fireball":
        trap_plan.insert(0, "Fireball-specific: use traps to punish Warden angle setup, not just the core.")

    build_order = [
        "Place Town Hall and core anchor first.",
        "Place Clan Castle, Monolith, Spell Towers, and Scattershots with spacing in mind.",
        "Build compartments around pathing goals instead of drawing walls first.",
        "Place splash and point defenses to punish the target meta.",
        "Add traps last after deciding likely entry lanes.",
        "Test with friendly challenges and adjust the first thing attackers exploit.",
    ]

    strengths = [
        f"Built specifically around {meta['label']} pressure.",
        "Major defenses are intentionally separated to reduce single-spell value.",
        "Core is offset enough to create awkward hero/troop pathing.",
    ]

    notes = [
        "This is a strategic blueprint, not an official Clash layout import link.",
        "After building it in game, use Clash's Share Layout button and save that copy link with /savebase.",
        "Friendly challenge testing matters; tune traps based on how your clan attacks it.",
    ]

    return BasePlan(
        townhall=townhall,
        style=style,
        anti_meta=anti_meta,
        symmetry=symmetry,
        title=f"TH{townhall} {meta['label']} {style.title()} Blueprint",
        score_seed=random.randint(1000, 9999),
        created_at=datetime.now(timezone.utc).isoformat(),
        buildings=buildings,
        grid=grid,
        rules=meta["rules"],
        style_rules=get_style_rules(style),
        trap_plan=trap_plan,
        build_order=build_order,
        strengths=strengths,
        weaknesses=meta["weaknesses"],
        notes=notes,
    )
