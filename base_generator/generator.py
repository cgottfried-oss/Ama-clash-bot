from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from .footprints import footprint_for, label_for
from .rules import get_buildings, get_meta_rule, get_style_rules, normalize_choice
from .tilemap import GRID_SIZE, CENTER_INDEX, offset_text, to_center_offset

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
    placements: list[dict]
    walls: list[dict]
    compartments: list[dict]
    placement_guide: list[str]
    rules: list[str]
    style_rules: list[str]
    trap_plan: list[str]
    build_order: list[str]
    strengths: list[str]
    weaknesses: list[str]
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_grid(size: int = GRID_SIZE) -> list[list[str]]:
    return [["" for _ in range(size)] for _ in range(size)]


def _place(grid: list[list[str]], label: str, row: int, col: int):
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        grid[row][col] = label


def _layout_coordinates(symmetry: str, anti_meta: str) -> dict[str, tuple[int, int]]:
    if symmetry == "random":
        symmetry = random.choice(["box", "diamond", "ring"])

    coords = {
        "Town Hall": (6, 6), "Clan Castle": (6, 5), "Monolith": (5, 7), "Eagle": (7, 5),
        "Scattershot A": (4, 4), "Scattershot B": (8, 8), "Inferno A": (4, 8), "Inferno B": (8, 4),
        "Inferno C": (6, 9), "Spell Tower A": (5, 4), "Spell Tower B": (7, 8), "Firespitters": (3, 6),
        "Hero Hall": (9, 6), "Air Defenses": (3, 3), "X-Bows": (9, 9), "Bomb Towers": (6, 3),
        "Builder Huts": (3, 9), "Merged Defenses": (9, 3), "Ricochet Cannons": (2, 6), "Multi-Archer Towers": (10, 6),
    }

    if symmetry == "diamond":
        coords.update({"Town Hall": (5, 6), "Clan Castle": (6, 6), "Monolith": (7, 6), "Eagle": (6, 4), "Scattershot A": (4, 6), "Scattershot B": (8, 6), "Inferno A": (6, 8), "Inferno B": (5, 4)})
    elif symmetry == "ring":
        coords.update({"Town Hall": (4, 7), "Clan Castle": (6, 6), "Monolith": (7, 7), "Eagle": (8, 4), "Scattershot A": (4, 4), "Scattershot B": (8, 8), "Inferno A": (3, 8), "Inferno B": (9, 4)})

    if anti_meta == "root_rider":
        coords.update({"Town Hall": (5, 7), "Monolith": (7, 5), "Clan Castle": (6, 6)})
    elif anti_meta == "fireball":
        coords.update({"Town Hall": (6, 7), "Monolith": (4, 4), "Scattershot A": (8, 4), "Scattershot B": (4, 9)})
    elif anti_meta == "blimp":
        coords.update({"Town Hall": (6, 8), "Spell Tower A": (6, 7), "Clan Castle": (7, 6)})
    return coords


def _expand_buildings(buildings: list[str]) -> list[str]:
    expanded = []
    for building in buildings:
        if building == "Scattershots":
            expanded.extend(["Scattershot A", "Scattershot B"])
        elif building == "Infernos":
            expanded.extend(["Inferno A", "Inferno B", "Inferno C"])
        elif building == "Spell Towers":
            expanded.extend(["Spell Tower A", "Spell Tower B"])
        else:
            expanded.append(building)
    return expanded


def _build_placements(buildings: list[str], coords: dict[str, tuple[int, int]]) -> list[dict]:
    placements = []
    used = set()
    for building in _expand_buildings(buildings):
        row, col = coords.get(building, (random.randint(2, 10), random.randint(2, 10)))
        while (row, col) in used:
            row = min(10, max(2, row + random.choice([-1, 1])))
            col = min(10, max(2, col + random.choice([-1, 1])))
        used.add((row, col))
        width, height = footprint_for(building)
        x, y = to_center_offset(row, col)
        placements.append({"building": building, "label": label_for(building), "row": row, "col": col, "x": x, "y": y, "width": width, "height": height, "offset": offset_text(row, col)})
    return placements


def _generate_walls(symmetry: str, anti_meta: str) -> list[dict]:
    walls = []
    # Core box/ring around center.
    for c in range(3, 10):
        walls.append({"row": 3, "col": c, "kind": "core"})
        walls.append({"row": 9, "col": c, "kind": "core"})
    for r in range(3, 10):
        walls.append({"row": r, "col": 3, "kind": "core"})
        walls.append({"row": r, "col": 9, "kind": "core"})
    # Offset breaker walls to discourage straight Root Rider lanes.
    if anti_meta == "root_rider":
        for pos in [(4, 6), (5, 6), (7, 6), (8, 6), (6, 4), (6, 8)]:
            walls.append({"row": pos[0], "col": pos[1], "kind": "breaker"})
    if symmetry == "diamond":
        for pos in [(2, 6), (6, 2), (10, 6), (6, 10)]:
            walls.append({"row": pos[0], "col": pos[1], "kind": "diamond"})
    return walls


def _generate_compartments(anti_meta: str) -> list[dict]:
    return [
        {"name": "Core", "purpose": "Protect TH/CC while forcing awkward spell value.", "bounds": [3, 3, 9, 9]},
        {"name": "Entry Bait", "purpose": "Looks valuable but is meant to split the first push.", "bounds": [2, 4, 5, 8]},
        {"name": "Backend Punish", "purpose": f"Holds splash/traps for late {anti_meta.replace('_', ' ')} pathing.", "bounds": [7, 4, 10, 9]},
    ]


def _placement_guide(placements: list[dict]) -> list[str]:
    priority = ["Town Hall", "Clan Castle", "Monolith", "Spell Tower A", "Spell Tower B", "Scattershot A", "Scattershot B", "Inferno A", "Inferno B", "Inferno C", "Firespitters", "Hero Hall"]
    order = {name: idx for idx, name in enumerate(priority)}
    sorted_places = sorted(placements, key=lambda p: order.get(p["building"], 99))
    return [f"{p['label']} {p['building']}: {p['offset']} from center ({p['width']}x{p['height']})" for p in sorted_places[:12]]


def generate_base_plan(townhall: int = 16, style: str = "war", anti_meta: str = "root_rider", symmetry: str = "ring") -> BasePlan:
    townhall = int(townhall or 16)
    if townhall < 14 or townhall > 17:
        townhall = 16
    style = normalize_choice(style, "war", ALLOWED_STYLE)
    anti_meta = normalize_choice(anti_meta, "root_rider", ALLOWED_META)
    symmetry = normalize_choice(symmetry, "ring", ALLOWED_SYMMETRY)

    meta = get_meta_rule(anti_meta)
    buildings = get_buildings(townhall)
    coords = _layout_coordinates(symmetry, anti_meta)
    placements = _build_placements(buildings, coords)
    walls = _generate_walls(symmetry, anti_meta)
    compartments = _generate_compartments(anti_meta)
    grid = _empty_grid()
    grid[CENTER_INDEX][CENTER_INDEX] = "C"
    for wall in walls:
        if not grid[wall["row"]][wall["col"]]:
            grid[wall["row"]][wall["col"]] = "W"
    for p in placements:
        _place(grid, p["label"], p["row"], p["col"])

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
        "Mark the center tile first, then place each major building using the offset guide.",
        "Place Town Hall and core anchor first.",
        "Place Clan Castle, Monolith, Spell Towers, and Scattershots with spacing in mind.",
        "Build compartments around pathing goals instead of drawing walls first.",
        "Add traps last after deciding likely entry lanes.",
        "Test with friendly challenges and adjust the first thing attackers exploit.",
    ]

    return BasePlan(
        townhall=townhall, style=style, anti_meta=anti_meta, symmetry=symmetry,
        title=f"TH{townhall} {meta['label']} {style.title()} Blueprint",
        score_seed=random.randint(1000, 9999), created_at=datetime.now(timezone.utc).isoformat(),
        buildings=buildings, grid=grid, placements=placements, walls=walls, compartments=compartments,
        placement_guide=_placement_guide(placements), rules=meta["rules"], style_rules=get_style_rules(style),
        trap_plan=trap_plan, build_order=build_order,
        strengths=[f"Built specifically around {meta['label']} pressure.", "Major defenses are intentionally separated to reduce single-spell value.", "Core is offset enough to create awkward hero/troop pathing."],
        weaknesses=meta["weaknesses"],
        notes=["This is a tile-aware strategic blueprint, not an official Clash layout import link.", "After building it in game, use Clash's Share Layout button and save that copy link with /savebase.", "Friendly challenge testing matters; tune traps based on how your clan attacks it."],
    )
