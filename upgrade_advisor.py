from __future__ import annotations

import os
import io
import html
import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from th_caps import TH_CAPS, get_item_cap, get_category_caps, normalize_cap_entry, get_all_cap_items

import discord
from playwright.async_api import async_playwright
from discord import app_commands

CHECK = "\u2705"        # ✅
BRAIN = "\U0001F9E0"    # 🧠
CHART = "\U0001F4CA"    # 📊
FULL = "\u2588"         # █
EMPTY = "\u2591"        # ░


LANE_EMOJIS = {
    "hero": "👑",
    "lab": "🧪",
    "builder": "🛠️",
}
CATEGORY_EMOJIS = {
    "hero": "👑",
    "troop": "⚔️",
    "spell": "✨",
    "siege": "🚀",
    "pet": "🐾",
    "building": "🏰",
    "economy": "💰",
    "defense": "🛡️",
    "trap": "💣",
}
TIMING_EMOJIS = {
    "now": "🔥",
    "soon": "⚡",
    "save_for": "🪙",
    "wait": "⏳",
}
MODE_EMOJIS = {
    "war": "⚔️",
    "farm": "🌾",
    "auto": "🧠",
}


@dataclass(frozen=True)
class ItemMeta:
    key: str
    label: str
    category: str
    offense: float
    farming: float
    defense: float
    utility: float
    time_weight: float
    cost_weight: float = 1.0
    lane: str = "builder" # builder | lab | hero
    blocks_progress: float = 0.0
    foundational: bool = False
    role_bonus: dict[str, float] = field(default_factory=dict)
    breakpoints: set[int] = field(default_factory=set)
    source: str = "manual"  # manual | hero | troop | spell | pet


ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "attacker": {"offense": 1.55, "farming": 0.35, "defense": 0.25, "utility": 1.00},
    "hybrid":   {"offense": 1.15, "farming": 0.70, "defense": 0.60, "utility": 1.00},
    "farmer":   {"offense": 0.45, "farming": 1.50, "defense": 0.70, "utility": 0.85},
}

DEFAULT_ROLE = "hybrid"
LANE_WEIGHTS: dict[str, float] = {
    "builder": 1.00,
    "lab": 0.92,
    "hero": 1.08,
}

MILESTONE_PROGRESS_MARKS = (25, 50, 75, 100)


def mark_reward(mark: int) -> int:
    return {25: 50, 50: 100, 75: 200, 100: 500}.get(int(mark), 0)

HERO_KEYS = {
    "barbarian_king",
    "archer_queen",
    "grand_warden",
    "royal_champion",
    "minion_prince",
    "dragon_duke",
}

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



ACCOUNT_COMPLETION_CATEGORIES = (
    "heroes",
    "pets",
    "troops",
    "spells",
    "siege_machines",
    "offense_buildings",
    "core_buildings",
    "defenses",
    "traps",
    "resource_buildings",
)

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


# These are advisor targets, not hard game max levels.
# Tune them whenever your clan meta changes.
RECOMMENDED_TARGETS_BY_TH: dict[int, dict[str, int]] = {
    10: {
        "barbarian_king": 35,
        "archer_queen": 35,
        "healers": 4,
        "balloons": 7,
        "dragons": 7,
        "hog_rider": 7,
        "rage_spell": 5,
        "freeze_spell": 5,
        "army_camp": 8,
        "clan_castle": 7,
        "laboratory": 8,
        "spell_factory": 5,
    },
    11: {
        "barbarian_king": 45,
        "archer_queen": 45,
        "grand_warden": 10,
        "healers": 5,
        "balloons": 8,
        "electro_dragon": 2,
        "dragons": 8,
        "hog_rider": 8,
        "rage_spell": 5,
        "freeze_spell": 6,
        "army_camp": 9,
        "clan_castle": 8,
        "laboratory": 9,
        "spell_factory": 6,
    },
    12: {
        "barbarian_king": 60,
        "archer_queen": 60,
        "grand_warden": 35,
        "healers": 6,
        "balloons": 9,
        "electro_dragon": 3,
        "hog_rider": 9,
        "miners": 6,
        "rage_spell": 6,
        "freeze_spell": 6,
        "invisibility_spell": 2,
        "wall_wrecker": 3,
        "battle_blimp": 3,
        "stone_slammer": 3,
        "army_camp": 10,
        "clan_castle": 9,
        "laboratory": 10,
        "spell_factory": 7,
    },
    13: {
        "barbarian_king": 70,
        "archer_queen": 70,
        "grand_warden": 40,
        "royal_champion": 20,
        "healers": 7,
        "balloons": 10,
        "dragons": 9,
        "hog_rider": 10,
        "miners": 7,
        "freeze_spell": 7,
        "rage_spell": 6,
        "invisibility_spell": 3,
        "wall_wrecker": 4,
        "battle_blimp": 4,
        "stone_slammer": 4,
        "siege_barracks": 4,
        "log_launcher": 4,
        "army_camp": 11,
        "clan_castle": 10,
        "laboratory": 11,
        "blacksmith": 2,
    },
    14: {
        "barbarian_king": 80,
        "archer_queen": 80,
        "grand_warden": 50,
        "royal_champion": 25,
        "healers": 8,
        "balloons": 10,
        "dragons": 10,
        "hog_rider": 11,
        "miners": 8,
        "electro_dragon": 4,
        "freeze_spell": 7,
        "rage_spell": 6,
        "invisibility_spell": 4,
        "unicorn": 5,
        "wall_wrecker": 4,
        "battle_blimp": 4,
        "stone_slammer": 4,
        "siege_barracks": 4,
        "log_launcher": 4,
        "flame_flinger": 4,
        "battle_drill": 4,
        "army_camp": 11,
        "clan_castle": 10,
        "laboratory": 12,
        "pet_house": 4,
        "blacksmith": 4,
    },
    15: {
        "barbarian_king": 85,
        "archer_queen": 85,
        "grand_warden": 60,
        "royal_champion": 35,
        "healers": 9,
        "balloons": 11,
        "dragons": 11,
        "hog_rider": 12,
        "electro_dragon": 5,
        "root_rider": 2,
        "freeze_spell": 8,
        "rage_spell": 6,
        "invisibility_spell": 4,
        "unicorn": 10,
        "phoenix": 8,
        "diggy": 8,
        "frosty": 5,
        "wall_wrecker": 5,
        "battle_blimp": 5,
        "stone_slammer": 5,
        "siege_barracks": 5,
        "log_launcher": 5,
        "flame_flinger": 4,
        "battle_drill": 4,
        "troop_launcher": 3,
        "army_camp": 12,
        "clan_castle": 11,
        "laboratory": 13,
        "pet_house": 8,
        "blacksmith": 6,
    },
    16: {
        "barbarian_king": 90,
        "archer_queen": 90,
        "grand_warden": 65,
        "royal_champion": 40,
        "minion_prince": 50,
        "healers": 10,
        "balloons": 12,
        "dragons": 12,
        "electro_dragon": 6,
        "root_rider": 3,
        "apprentice_warden": 4,
        "freeze_spell": 8,
        "rage_spell": 7,
        "invisibility_spell": 4,
        "recall_spell": 4,
        "unicorn": 10,
        "phoenix": 10,
        "diggy": 10,
        "spirit_fox": 8,
        "wall_wrecker": 5,
        "battle_blimp": 5,
        "stone_slammer": 5,
        "siege_barracks": 5,
        "log_launcher": 5,
        "flame_flinger": 5,
        "battle_drill": 4,
        "troop_launcher": 4,
        "army_camp": 12,
        "clan_castle": 11,
        "laboratory": 14,
        "pet_house": 10,
        "blacksmith": 8,
        "hero_hall": 9,
    },
    17: {
        "barbarian_king": 95,
        "archer_queen": 95,
        "grand_warden": 70,
        "royal_champion": 45,
        "minion_prince": 70,
        "dragon_duke": 20,
        "healers": 10,
        "balloons": 12,
        "dragons": 12,
        "electro_dragon": 7,
        "root_rider": 4,
        "apprentice_warden": 5,
        "freeze_spell": 9,
        "rage_spell": 7,
        "invisibility_spell": 5,
        "recall_spell": 5,
        "unicorn": 10,
        "phoenix": 10,
        "diggy": 10,
        "spirit_fox": 10,
        "wall_wrecker": 5,
        "battle_blimp": 5,
        "stone_slammer": 5,
        "siege_barracks": 5,
        "log_launcher": 5,
        "flame_flinger": 5,
        "battle_drill": 5,
        "troop_launcher": 4,
        "army_camp": 12,
        "clan_castle": 12,
        "laboratory": 15,
        "pet_house": 10,
        "blacksmith": 10,
        "hero_hall": 10,
    },
    18: {
        "barbarian_king": 100,
        "archer_queen": 100,
        "grand_warden": 75,
        "royal_champion": 50,
        "minion_prince": 80,
        "dragon_duke": 40,
        "healers": 11,
        "balloons": 13,
        "dragons": 13,
        "electro_dragon": 8,
        "root_rider": 5,
        "apprentice_warden": 6,
        "freeze_spell": 10,
        "rage_spell": 7,
        "invisibility_spell": 6,
        "recall_spell": 6,
        "unicorn": 10,
        "phoenix": 10,
        "diggy": 10,
        "spirit_fox": 10,
        "wall_wrecker": 6,
        "battle_blimp": 5,
        "stone_slammer": 6,
        "siege_barracks": 5,
        "log_launcher": 5,
        "flame_flinger": 5,
        "battle_drill": 5,
        "troop_launcher": 4,
        "army_camp": 13,
        "clan_castle": 12,
        "laboratory": 16,
        "pet_house": 10,
        "blacksmith": 12,
        "hero_hall": 11,
    },
}

ITEMS: dict[str, ItemMeta] = {
    # Heroes
    "barbarian_king": ItemMeta("barbarian_king", "Barbarian King", "hero", 9.0, 3.0, 2.0, 4.0, 5.0, cost_weight=4.8, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="hero"),
    "archer_queen": ItemMeta("archer_queen", "Archer Queen", "hero", 10.0, 4.0, 2.0, 5.0, 5.0, cost_weight=5.0, lane="hero", blocks_progress=1.4, role_bonus={"attacker": 7, "hybrid": 4, "farmer": 0}, source="hero"),
    "grand_warden": ItemMeta("grand_warden", "Grand Warden", "hero", 10.0, 2.0, 2.0, 7.0, 5.0, cost_weight=4.6, lane="hero", blocks_progress=1.5, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={10, 20, 30, 40, 50, 60, 70}, source="hero"),
    "royal_champion": ItemMeta("royal_champion", "Royal Champion", "hero", 9.5, 2.0, 2.5, 4.5, 5.0, cost_weight=4.7, lane="hero", blocks_progress=1.3, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 10, 20, 25, 35, 45}, source="hero"),
    "minion_prince": ItemMeta("minion_prince", "Minion Prince", "hero", 8.5, 2.0, 2.0, 4.0, 5.0, cost_weight=4.5, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="hero"),
    "dragon_duke": ItemMeta("dragon_duke", "Dragon Duke", "hero", 9.0, 2.0, 2.0, 4.0, 5.5, cost_weight=4.9, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -2}, source="hero"),

    # Buildings / structure priorities
    "army_camp": ItemMeta("army_camp", "Army Camp", "building", 10.0, 5.0, 0.0, 8.0, 4.0, cost_weight=3.8, lane="builder", blocks_progress=1.6, foundational=True, role_bonus={"attacker": 8, "hybrid": 7, "farmer": 2}, breakpoints={8, 9, 10, 11, 12, 13}),
    "clan_castle": ItemMeta("clan_castle", "Clan Castle", "building", 9.0, 2.0, 2.0, 8.0, 4.0, cost_weight=3.7, lane="builder", blocks_progress=1.4, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": 0}, breakpoints={7, 8, 9, 10, 11, 12}),
    "laboratory": ItemMeta("laboratory", "Laboratory", "building", 8.0, 3.0, 0.0, 10.0, 4.0, cost_weight=4.0, lane="builder", blocks_progress=1.8, foundational=True, role_bonus={"attacker": 8, "hybrid": 6, "farmer": 0}, breakpoints={8, 9, 10, 11, 12, 13, 14, 15, 16}),
    "spell_factory": ItemMeta("spell_factory", "Spell Factory", "building", 7.0, 1.0, 0.0, 7.0, 4.0, cost_weight=3.0, lane="builder", blocks_progress=1.0, foundational=True, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 6, 7}),
    "pet_house": ItemMeta("pet_house", "Pet House", "building", 8.0, 1.0, 0.0, 7.0, 4.5, cost_weight=4.4, lane="builder", blocks_progress=1.4, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={4, 8, 10}),
    "blacksmith": ItemMeta("blacksmith", "Blacksmith", "building", 8.0, 1.0, 0.0, 8.0, 4.5, cost_weight=4.3, lane="builder", blocks_progress=1.5, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={2, 4, 6, 8, 10}),
    "hero_hall": ItemMeta("hero_hall", "Hero Hall", "building", 9.0, 1.0, 0.0, 9.0, 5.0, cost_weight=4.5, lane="builder", blocks_progress=1.7, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={9, 10, 11}),

    # Troops
    "healers": ItemMeta("healers", "Healers", "troop", 9.0, 3.0, 0.0, 5.0, 3.0, cost_weight=2.8, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 3, "farmer": 0}, source="troop"),
    "balloons": ItemMeta("balloons", "Balloons", "troop", 9.0, 2.0, 0.0, 4.0, 3.0, cost_weight=2.8, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -1}, source="troop"),
    "dragons": ItemMeta("dragons", "Dragons", "troop", 8.0, 2.0, 0.0, 4.0, 3.5, cost_weight=3.0, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "electro_dragon": ItemMeta("electro_dragon", "Electro Dragon", "troop", 8.5, 2.0, 0.0, 4.0, 3.8, cost_weight=3.4, lane="lab", blocks_progress=0.8, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "hog_rider": ItemMeta("hog_rider", "Hog Rider", "troop", 8.5, 2.0, 0.0, 4.0, 3.0, cost_weight=2.9, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "miners": ItemMeta("miners", "Miners", "troop", 8.0, 3.0, 0.0, 4.0, 3.0, cost_weight=3.0, lane="lab", blocks_progress=0.8),
    "root_rider": ItemMeta("root_rider", "Root Rider", "troop", 9.0, 1.0, 0.0, 4.0, 4.0, cost_weight=3.8, lane="lab", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),
    "apprentice_warden": ItemMeta("apprentice_warden", "Apprentice Warden", "troop", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.6, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),

    # Siege machines
    "wall_wrecker": ItemMeta("wall_wrecker", "Wall Wrecker", "siege", 8.5, 1.0, 0.0, 5.0, 3.8, cost_weight=3.3, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={3, 4, 5, 6}, source="troop"),
    "battle_blimp": ItemMeta("battle_blimp", "Battle Blimp", "siege", 8.5, 1.0, 0.0, 5.5, 3.8, cost_weight=3.3, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={3, 4, 5}, source="troop"),
    "stone_slammer": ItemMeta("stone_slammer", "Stone Slammer", "siege", 9.0, 1.0, 0.0, 5.0, 3.8, cost_weight=3.4, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={3, 4, 5, 6}, source="troop"),
    "siege_barracks": ItemMeta("siege_barracks", "Siege Barracks", "siege", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "log_launcher": ItemMeta("log_launcher", "Log Launcher", "siege", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "flame_flinger": ItemMeta("flame_flinger", "Flame Flinger", "siege", 8.5, 1.0, 0.0, 5.5, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "battle_drill": ItemMeta("battle_drill", "Battle Drill", "siege", 8.5, 1.0, 0.0, 5.5, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "troop_launcher": ItemMeta("troop_launcher", "Troop Launcher", "siege", 8.0, 1.0, 0.0, 5.0, 4.0, cost_weight=3.4, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={3, 4}, source="troop"),

    # Spells
    "rage_spell": ItemMeta("rage_spell", "Rage Spell", "spell", 8.0, 1.0, 0.0, 5.0, 2.5, cost_weight=2.2, lane="lab", blocks_progress=0.8, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="spell"),
    "freeze_spell": ItemMeta("freeze_spell", "Freeze Spell", "spell", 9.0, 1.0, 0.0, 6.0, 2.5, cost_weight=2.4, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="spell"),
    "invisibility_spell": ItemMeta("invisibility_spell", "Invisibility Spell", "spell", 8.5, 1.0, 0.0, 6.0, 3.0, cost_weight=2.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="spell"),
    "recall_spell": ItemMeta("recall_spell", "Recall Spell", "spell", 7.0, 1.0, 0.0, 6.0, 3.0, cost_weight=2.6, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -2}, source="spell"),
    
    # Pets
    "lassi": ItemMeta("lassi", "L.A.S.S.I", "pet", 7.5, 1.0, 0.0, 4.0, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "mighty_yak": ItemMeta("mighty_yak", "Mighty Yak", "pet", 8.0, 1.0, 0.0, 4.5, 3.0, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "electro_owl": ItemMeta("electro_owl", "Electro Owl", "pet", 8.0, 1.0, 0.0, 4.5, 3.0, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "unicorn": ItemMeta("unicorn", "Unicorn", "pet", 9.0, 1.0, 0.0, 5.0, 3.2, cost_weight=3.3, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),
    "phoenix": ItemMeta("phoenix", "Phoenix", "pet", 8.5, 1.0, 0.0, 5.0, 3.2, cost_weight=3.2, lane="hero", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, source="pet"),
    "diggy": ItemMeta("diggy", "Diggy", "pet", 8.5, 1.0, 0.0, 5.5, 3.2, cost_weight=3.3, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 5, "hybrid": 4, "farmer": -2}, source="pet"),
    "poison_lizard": ItemMeta("poison_lizard", "Poison Lizard", "pet", 8.0, 1.0, 0.0, 5.0, 3.1, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "frosty": ItemMeta("frosty", "Frosty", "pet", 7.5, 1.0, 0.0, 5.0, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "spirit_fox": ItemMeta("spirit_fox", "Spirit Fox", "pet", 9.0, 1.0, 0.0, 6.0, 3.2, cost_weight=3.5, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),
    "angry_jelly": ItemMeta("angry_jelly", "Angry Jelly", "pet", 7.5, 1.0, 0.0, 4.8, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "sneezy": ItemMeta("sneezy", "Sneezy", "pet", 7.5, 1.0, 0.0, 4.8, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "greedy_raven": ItemMeta("greedy_raven", "Greedy Raven", "pet", 8.5, 2.0, 0.0, 5.0, 3.1, cost_weight=3.2, lane="hero", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": 0}, source="pet"),
    
    # Economy / defensive options for farmer or hybrid preference
    "gold_mine": ItemMeta("gold_mine", "Gold Mine", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "elixir_collector": ItemMeta("elixir_collector", "Elixir Collector", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "dark_elixir_drill": ItemMeta("dark_elixir_drill", "Dark Elixir Drill", "economy", 0.0, 8.5, 0.0, 2.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 7}),
    "gold_storage": ItemMeta("gold_storage", "Gold Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "elixir_storage": ItemMeta("elixir_storage", "Elixir Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "air_defense": ItemMeta("air_defense", "Air Defense", "defense", 0.0, 1.0, 8.0, 2.0, 3.5, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
    "inferno_tower": ItemMeta("inferno_tower", "Inferno Tower", "defense", 0.0, 1.0, 8.5, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "x_bow": ItemMeta("x_bow", "X-Bow", "defense", 0.0, 1.0, 7.0, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
    "scattershot": ItemMeta("scattershot", "Scattershot", "defense", 0.0, 1.0, 8.7, 2.2, 4.5, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "air_sweeper": ItemMeta("air_sweeper", "Air Sweeper", "defense", 0.0, 1.0, 6.8, 2.0, 3.0, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "hidden_tesla": ItemMeta("hidden_tesla", "Hidden Tesla", "defense", 0.0, 1.0, 6.5, 1.8, 3.2, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "bomb_tower": ItemMeta("bomb_tower", "Bomb Tower", "defense", 0.0, 1.0, 6.9, 1.8, 3.4, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "spell_tower": ItemMeta("spell_tower", "Spell Tower", "defense", 0.0, 1.0, 8.0, 2.2, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "monolith": ItemMeta("monolith", "Monolith", "defense", 0.0, 1.0, 9.0, 2.2, 4.8, role_bonus={"attacker": -4, "hybrid": 5, "farmer": 2}),
    "multi_archer_tower": ItemMeta("multi_archer_tower", "Multi-Archer Tower", "defense", 0.0, 1.0, 8.4, 2.0, 4.2, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "ricochet_cannon": ItemMeta("ricochet_cannon", "Ricochet Cannon", "defense", 0.0, 1.0, 8.6, 2.0, 4.2, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "multi_gear_tower": ItemMeta("multi_gear_tower", "Multi-Gear Tower", "defense", 0.0, 1.0, 8.3, 2.0, 4.3, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "firespitter": ItemMeta("firespitter", "Firespitter", "defense", 0.0, 1.0, 8.1, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "super_wizard_tower": ItemMeta("super_wizard_tower", "Super Wizard Tower", "defense", 0.0, 1.0, 8.8, 2.2, 4.5, role_bonus={"attacker": -3, "hybrid": 5, "farmer": 2}),
    "revenge_tower": ItemMeta("revenge_tower", "Revenge Tower", "defense", 0.0, 1.0, 8.9, 2.2, 4.6, role_bonus={"attacker": -3, "hybrid": 5, "farmer": 2}),
    # Traps
    "bomb": ItemMeta("bomb", "Bomb", "trap", 0.0, 0.5, 5.0, 1.0, 2.0, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "giant_bomb": ItemMeta("giant_bomb", "Giant Bomb", "trap", 0.0, 0.5, 7.0, 1.2, 2.5, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "air_bomb": ItemMeta("air_bomb", "Air Bomb", "trap", 0.0, 0.5, 6.0, 1.0, 2.2, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "seeking_air_mine": ItemMeta("seeking_air_mine", "Seeking Air Mine", "trap", 0.0, 0.5, 6.5, 1.0, 2.3, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "spring_trap": ItemMeta("spring_trap", "Spring Trap", "trap", 0.0, 0.5, 4.5, 0.8, 2.0, role_bonus={"attacker": -1, "hybrid": 2, "farmer": 1}),
    "skeleton_trap": ItemMeta("skeleton_trap", "Skeleton Trap", "trap", 0.0, 0.5, 5.0, 1.0, 2.1, role_bonus={"attacker": -1, "hybrid": 2, "farmer": 1}),
    "tornado_trap": ItemMeta("tornado_trap", "Tornado Trap", "trap", 0.0, 0.5, 7.5, 1.2, 2.8, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "giga_bomb": ItemMeta("giga_bomb", "Giga Bomb", "trap", 0.0, 0.5, 8.0, 1.5, 3.0, role_bonus={"attacker": -2, "hybrid": 4, "farmer": 1}),
}

AUTOSYNC_NAME_MAP = {
    # Heroes
    "Barbarian King": "barbarian_king",
    "Archer Queen": "archer_queen",
    "Grand Warden": "grand_warden",
    "Royal Champion": "royal_champion",
    "Minion Prince": "minion_prince",
    "Dragon Duke": "dragon_duke",
    # Troops
    "Healer": "healers",
    "Balloon": "balloons",
    "Dragon": "dragons",
    "Electro Dragon": "electro_dragon",
    "Hog Rider": "hog_rider",
    "Miner": "miners",
    "Root Rider": "root_rider",
    "Apprentice Warden": "apprentice_warden",
    # Spells
    "Rage Spell": "rage_spell",
    "Freeze Spell": "freeze_spell",
    "Invisibility Spell": "invisibility_spell",
    "Recall Spell": "recall_spell",
    # Pets
    "Unicorn": "unicorn",
    "Phoenix": "phoenix",
    "Diggy": "diggy",
    "Frosty": "frosty",
    "Spirit Fox": "spirit_fox",
    # Siege machines
    "Wall Wrecker": "wall_wrecker",
    "Battle Blimp": "battle_blimp",
    "Stone Slammer": "stone_slammer",
    "Siege Barracks": "siege_barracks",
    "Log Launcher": "log_launcher",
    "Flame Flinger": "flame_flinger",
    "Battle Drill": "battle_drill",
    "Troop Launcher": "troop_launcher",
}

TRACKABLE_CHOICES = [
    app_commands.Choice(name=f"{meta.label} ({key})", value=key)
    for key, meta in sorted(ITEMS.items(), key=lambda kv: kv[1].label.lower())
]


class UpgradeAdvisor:
    def __init__(self, tree: app_commands.CommandTree, deps: dict[str, Any]):
        self.tree = tree
        self.safe_load_json: Callable = deps["safe_load_json"]
        self.safe_save_json: Callable = deps["safe_save_json"]
        self.update_json_file: Callable = deps["update_json_file"]
        self.normalize_tag: Callable = deps["normalize_tag"]
        self.get_cached_or_fetch: Callable = deps["get_cached_or_fetch"]
        self.linked_file: str = deps["linked_file"]
        data_dir: str = deps["data_dir"]
        self.store_path = os.path.join(data_dir, "upgrade_advisor.json")
        self.clash_api_base = deps.get("clash_api_base", "https://api.clashofclans.com/v1")

    def default_user_root(self) -> dict[str, Any]:
        return {
            "role": DEFAULT_ROLE,
            "active_player_tag": None,
            "accounts": {},
        }

    def default_account_store(self) -> dict[str, Any]:
        return {
            "manual_levels": {},
            "manual_copy_levels": {},
            "targets": {},
            "synced_levels": {},
            "synced_max_levels": {},
            "player_tag": None,
            "player_name": None,
            "town_hall": None,
            "town_hall_started_at": None,
            "last_synced_at": None,
            "progress_history": [],
            "advisor_economy": {
                "coins": 0,
                "efficiency_score": 0,
                "followed_paths": 0,
                "missed_paths": 0,
                "last_recommendations": [],
                "last_award_at": None,
            },
        }

    def migrate_user_root(self, user: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(user, dict):
            user = {}

        if "accounts" in user and isinstance(user.get("accounts"), dict):
            user.setdefault("role", DEFAULT_ROLE)
            user.setdefault("active_player_tag", None)
            return user

        legacy_account = self.default_account_store()
        legacy_account["manual_levels"] = dict(user.get("manual_levels", {}) or {})
        legacy_account["manual_copy_levels"] = dict(user.get("manual_copy_levels", {}) or {})
        legacy_account["targets"] = dict(user.get("targets", {}) or {})
        legacy_account["synced_levels"] = dict(user.get("synced_levels", {}) or {})
        legacy_account["synced_max_levels"] = dict(user.get("synced_max_levels", {}) or {})
        legacy_account["player_tag"] = user.get("player_tag")
        legacy_account["player_name"] = user.get("player_name")
        legacy_account["town_hall"] = user.get("town_hall")
        legacy_account["town_hall_started_at"] = user.get("town_hall_started_at")
        legacy_account["last_synced_at"] = user.get("last_synced_at")
        legacy_account["progress_history"] = list(user.get("progress_history", []) or [])

        root = self.default_user_root()
        root["role"] = user.get("role", DEFAULT_ROLE)

        player_tag = legacy_account.get("player_tag")
        has_legacy_data = any(
            [
                legacy_account["manual_levels"],
                legacy_account["manual_copy_levels"],
                legacy_account["targets"],
                legacy_account["synced_levels"],
                legacy_account["synced_max_levels"],
                legacy_account["player_name"],
                legacy_account["town_hall"],
                legacy_account["town_hall_started_at"],
                legacy_account["last_synced_at"],
                legacy_account["progress_history"],
            ]
        )
        if has_legacy_data:
            key = self.normalize_tag(player_tag) if player_tag else "legacy"
            legacy_account["player_tag"] = self.normalize_tag(player_tag) if player_tag else None
            root["accounts"][key] = legacy_account
            root["active_player_tag"] = key

        return root

    async def load_store(self) -> dict[str, Any]:
        store = await self.safe_load_json(self.store_path)
        if not isinstance(store, dict):
            store = {}
        store.setdefault("users", {})
        return store

    async def get_user_root(self, user_id: str) -> dict[str, Any]:
        store = await self.load_store()
        users = store.setdefault("users", {})
        user = users.setdefault(str(user_id), self.default_user_root())
        migrated = self.migrate_user_root(user)
        users[str(user_id)] = migrated
        return migrated

    def get_account_from_root(self, user_root: dict[str, Any], player_tag: str | None = None) -> dict[str, Any]:
        accounts = user_root.setdefault("accounts", {})
        target_tag = self.normalize_tag(player_tag) if player_tag else user_root.get("active_player_tag")
        if not target_tag or target_tag not in accounts:
            return self.default_account_store()
        account = accounts.get(target_tag) or self.default_account_store()
        return account

    async def get_user_store(self, user_id: str, player_tag: str | None = None) -> dict[str, Any]:
        root = await self.get_user_root(user_id)
        account = dict(self.get_account_from_root(root, player_tag))
        account["role"] = root.get("role", DEFAULT_ROLE)
        account["active_player_tag"] = root.get("active_player_tag")
        return account

    async def save_user_patch(self, user_id: str, patch_fn: Callable[[dict[str, Any]], None], player_tag: str | None = None) -> dict[str, Any]:
        normalized_player_tag = self.normalize_tag(player_tag) if player_tag else None

        def _update(store: dict[str, Any]):
            if not isinstance(store, dict):
                store = {}
            users = store.setdefault("users", {})
            existing = users.setdefault(str(user_id), self.default_user_root())
            root = self.migrate_user_root(existing)
            accounts = root.setdefault("accounts", {})
            target_tag = normalized_player_tag or root.get("active_player_tag") or "legacy"
            account = accounts.setdefault(target_tag, self.default_account_store())
            account.setdefault("player_tag", None)
            if account.get("player_tag") is None and target_tag != "legacy":
                account["player_tag"] = target_tag
            patch_fn(root, account)
            users[str(user_id)] = root
            return store

        return await self.update_json_file(self.store_path, _update)

    async def get_linked_accounts(self, discord_user_id: str) -> list[dict[str, str]]:
        linked_raw = await self.safe_load_json(self.linked_file)
        entries = linked_raw.get(str(discord_user_id), []) if isinstance(linked_raw, dict) else []
        results: list[dict[str, str]] = []
        seen: set[str] = set()

        for entry in entries:
            tag = None
            name = "Unknown"
            if isinstance(entry, str):
                tag = self.normalize_tag(entry)
            elif isinstance(entry, dict) and entry.get("tag"):
                tag = self.normalize_tag(entry["tag"])
                name = entry.get("name", "Unknown")
            if not tag or tag in seen:
                continue
            seen.add(tag)
            results.append({"tag": tag, "name": name})

        return results

    async def resolve_linked_account(self, discord_user_id: str, account_hint: str | None = None) -> dict[str, str] | None:
        linked_accounts = await self.get_linked_accounts(discord_user_id)
        if not linked_accounts:
            return None

        if account_hint:
            hint = account_hint.strip().lower()
            normalized_hint = self.normalize_tag(account_hint) if "#" in account_hint or account_hint.upper().startswith("P") else None
            for account in linked_accounts:
                if normalized_hint and account["tag"] == normalized_hint:
                    return account
                if hint == account["name"].lower() or hint in account["name"].lower() or hint in account["tag"].lower():
                    return account

        root = await self.get_user_root(discord_user_id)
        active_tag = root.get("active_player_tag")
        if active_tag:
            for account in linked_accounts:
                if account["tag"] == active_tag:
                    return account

        return linked_accounts[0]

    async def fetch_player_data(self, tag: str) -> dict[str, Any] | None:
        normalized_tag = self.normalize_tag(tag)
        encoded_tag = normalized_tag.replace("#", "%23")
        url = f"{self.clash_api_base}/players/{encoded_tag}"
        return await self.get_cached_or_fetch(f"player_{normalized_tag}", url, ttl=300)

    def get_th_cap_target(self, town_hall: int | None, item_key: str) -> int | None:
        if not town_hall or item_key not in ITEMS:
            return None
        category_and_name = TH_CAP_NAME_MAP.get(item_key)
        if not category_and_name:
            return None
        category, cap_name = category_and_name
        cap = get_item_cap(int(town_hall), category, cap_name, None)
        if cap is None:
            return None
        if isinstance(cap, dict):
            try:
                return int(normalize_cap_entry(cap).get("max_level", 0))
            except (TypeError, ValueError):
                return None
        try:
            return int(cap)
        except (TypeError, ValueError):
            return None

    def infer_default_targets(self, town_hall: int | None, role: str) -> dict[str, int]:
        if not town_hall:
            return {}
        baseline = RECOMMENDED_TARGETS_BY_TH.get(int(town_hall), {})
        targets = dict(baseline)

        if role == "attacker":
            for item in ("army_camp", "laboratory", "clan_castle"):
                if item in targets:
                    targets[item] += 1
        elif role == "farmer":
            for item in ("gold_mine", "elixir_collector", "dark_elixir_drill", "gold_storage", "elixir_storage"):
                targets[item] = max(targets.get(item, 0), 1)

        for item_key in TH_CAP_NAME_MAP:
            cap_target = self.get_th_cap_target(town_hall, item_key)
            if cap_target is not None:
                targets[item_key] = cap_target

        return targets

    def parse_player_levels(self, player: dict[str, Any]) -> tuple[int | None, str, str, dict[str, int], dict[str, int]]:
        th = player.get("townHallLevel")
        player_tag = self.normalize_tag(player.get("tag", "")) if player.get("tag") else ""
        player_name = player.get("name", "Unknown")
        levels: dict[str, int] = {}
        max_levels: dict[str, int] = {}

        for section in ("heroes", "troops", "spells", "heroPets"):
            for entry in player.get(section, []) or []:
                item_key = AUTOSYNC_NAME_MAP.get(entry.get("name"))
                if not item_key:
                    continue
                try:
                    levels[item_key] = int(entry.get("level", 0))
                except (TypeError, ValueError):
                    continue
                try:
                    max_level = int(entry.get("maxLevel", 0))
                except (TypeError, ValueError):
                    max_level = 0
                if max_level > 0:
                    max_levels[item_key] = max_level

        return th, player_tag, player_name, levels, max_levels

    async def sync_player(self, discord_user_id: str, account_hint: str | None = None) -> dict[str, Any]:
        link = await self.resolve_linked_account(discord_user_id, account_hint)
        if not link:
            raise ValueError("You need to link a Clash account first with /link.")

        player = await self.fetch_player_data(link["tag"])
        if not player:
            raise ValueError("Could not fetch your Clash player data right now.")

        th, player_tag, player_name, synced_levels, synced_max_levels = self.parse_player_levels(player)

        sync_now = datetime.now(timezone.utc).isoformat()

        def patch(root: dict[str, Any], account: dict[str, Any]):
            role = root.get("role", DEFAULT_ROLE)
            root["active_player_tag"] = player_tag
            previous_th = account.get("town_hall")
            if account.get("town_hall_started_at") is None or (th and previous_th and int(previous_th) != int(th)) or (th and previous_th is None):
                account["town_hall_started_at"] = sync_now
            account["town_hall"] = th
            account["player_tag"] = player_tag
            account["player_name"] = player_name
            account["synced_levels"] = synced_levels
            account["synced_max_levels"] = synced_max_levels
            account["last_synced_at"] = sync_now
            account.setdefault("targets", {})
            account.setdefault("progress_history", [])
            inferred = self.infer_default_targets(th, role)
            for key, value in inferred.items():
                account["targets"].setdefault(key, value)

        await self.save_user_patch(discord_user_id, patch, player_tag=player_tag)
        user = await self.get_user_store(discord_user_id, player_tag=player_tag)
        await self.record_progress_snapshot(discord_user_id, player_tag, user)
        return await self.get_user_store(discord_user_id, player_tag=player_tag)


    def _parse_iso_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = datetime.fromisoformat(str(value))
            except Exception:
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _format_duration_short(self, delta_seconds: float) -> str:
        seconds = max(0, int(delta_seconds))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days >= 1:
            return f"{days}d {hours}h"
        if hours >= 1:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def get_town_hall_age_text(self, user: dict[str, Any]) -> str:
        started_at = self._parse_iso_datetime(user.get("town_hall_started_at"))
        if not started_at:
            return "Unknown"
        return self._format_duration_short((datetime.now(timezone.utc) - started_at).total_seconds())

    def _trim_progress_history(self, history: list[dict[str, Any]], limit: int = 90) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            ts = self._parse_iso_datetime(entry.get("timestamp"))
            if not ts:
                continue
            cleaned.append({
                "timestamp": ts.isoformat(),
                "done": int(entry.get("done", 0) or 0),
                "tracked": int(entry.get("tracked", 0) or 0),
                "percent": int(entry.get("percent", 0) or 0),
            })
        cleaned.sort(key=lambda row: row["timestamp"])
        return cleaned[-limit:]

    async def record_progress_snapshot(self, user_id: str, player_tag: str | None, user: dict[str, Any] | None = None) -> None:
        user = user or await self.get_user_store(str(user_id), player_tag=player_tag)
        progress = self.build_progress_snapshot(user)
        timestamp = self._parse_iso_datetime(user.get("last_synced_at")) or datetime.now(timezone.utc)
        new_entry = {
            "timestamp": timestamp.isoformat(),
            "done": int(progress.get("done", 0) or 0),
            "tracked": int(progress.get("tracked", 0) or 0),
            "percent": int(progress.get("percent", 0) or 0),
        }

        def patch(root: dict[str, Any], account: dict[str, Any]):
            history = self._trim_progress_history(list(account.get("progress_history", []) or []), limit=90)
            if history:
                last = history[-1]
                last_ts = self._parse_iso_datetime(last.get("timestamp"))
                same_values = (
                    int(last.get("done", -1)) == new_entry["done"]
                    and int(last.get("tracked", -1)) == new_entry["tracked"]
                    and int(last.get("percent", -1)) == new_entry["percent"]
                )
                if same_values and last_ts and abs((timestamp - last_ts).total_seconds()) < 43200:
                    return
            history.append(new_entry)
            account["progress_history"] = self._trim_progress_history(history, limit=90)

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)

    def get_progress_velocity(self, user: dict[str, Any]) -> dict[str, Any]:
        history = self._trim_progress_history(list(user.get("progress_history", []) or []), limit=90)
        if len(history) < 2:
            return {"points_per_day": 0.0, "percent_per_day": 0.0, "days_to_target": None, "rating": "Unrated"}
        first = history[0]
        last = history[-1]
        first_ts = self._parse_iso_datetime(first.get("timestamp"))
        last_ts = self._parse_iso_datetime(last.get("timestamp"))
        if not first_ts or not last_ts or last_ts <= first_ts:
            return {"points_per_day": 0.0, "percent_per_day": 0.0, "days_to_target": None, "rating": "Unrated"}
        elapsed_days = max((last_ts - first_ts).total_seconds() / 86400.0, 1 / 24)
        done_gain = max(0, int(last.get("done", 0) or 0) - int(first.get("done", 0) or 0))
        percent_gain = max(0.0, float(last.get("percent", 0) or 0) - float(first.get("percent", 0) or 0))
        points_per_day = done_gain / elapsed_days
        percent_per_day = percent_gain / elapsed_days
        remaining_points = max(0, int(last.get("tracked", 0) or 0) - int(last.get("done", 0) or 0))
        days_to_target = (remaining_points / points_per_day) if points_per_day > 0 else None

        if points_per_day >= 2.0 or percent_per_day >= 1.25:
            rating = "Elite"
        elif points_per_day >= 1.0 or percent_per_day >= 0.75:
            rating = "Strong"
        elif points_per_day >= 0.35 or percent_per_day >= 0.25:
            rating = "Steady"
        elif done_gain > 0:
            rating = "Slow burn"
        else:
            rating = "Idle"

        return {
            "points_per_day": round(points_per_day, 2),
            "percent_per_day": round(percent_per_day, 2),
            "days_to_target": round(days_to_target, 1) if days_to_target is not None else None,
            "rating": rating,
            "samples": len(history),
        }

    def build_velocity_summary(self, user: dict[str, Any]) -> str:
        velocity = self.get_progress_velocity(user)
        eta = velocity.get("days_to_target")
        eta_text = f"~{eta} days to finish targets" if eta is not None else "ETA needs more sync history"
        return (
            f"📈 **Progress/day:** {velocity.get('points_per_day', 0):.2f} goals · {velocity.get('percent_per_day', 0):.2f}%\n"
            f"🏁 **ETA to target:** {eta_text}\n"
            f"⭐ **Player efficiency rating:** {velocity.get('rating', 'Unrated')}"
        )

    def get_effective_levels(self, user: dict[str, Any]) -> dict[str, int]:
        effective = {}
        effective.update(user.get("synced_levels", {}))
        effective.update(user.get("manual_levels", {}))
        return {k: int(v) for k, v in effective.items() if k in ITEMS}

    def get_manual_copy_levels(self, user: dict[str, Any]) -> dict[str, list[int]]:
        raw = user.get("manual_copy_levels") or {}
        out: dict[str, list[int]] = {}
        if not isinstance(raw, dict):
            return out
        for key, value in raw.items():
            if key not in ITEMS:
                continue
            if isinstance(value, list):
                levels: list[int] = []
                for entry in value:
                    try:
                        levels.append(max(0, int(entry)))
                    except (TypeError, ValueError):
                        continue
                out[key] = levels
        return out

    def _normalize_cap_lookup_key(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        for char in ("-", ".", "'", "’", "&", "/"):
            text = text.replace(char, " ")
        return " ".join(text.split())

    def _extract_copy_count_from_cap(self, cap: Any) -> int | None:
        if cap is None:
            return None
        try:
            normalized = normalize_cap_entry(cap)
        except Exception:
            normalized = cap

        candidates: list[Any] = []
        if isinstance(normalized, dict):
            for field in ("count", "copies", "copy_count", "instance_count", "instances", "quantity", "qty"):
                if field in normalized:
                    candidates.append(normalized.get(field))
            for field in ("levels", "copy_levels", "instances"):
                value = normalized.get(field)
                if isinstance(value, (list, tuple)):
                    candidates.append(len(value))
        elif isinstance(normalized, (list, tuple)):
            candidates.append(len(normalized))

        for value in candidates:
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            if count > 0:
                return count
        return None

    def _find_cap_from_category_caps(self, town_hall: int, category: str, cap_name: str) -> Any:
        try:
            category_caps = get_category_caps(int(town_hall), category)
        except Exception:
            return None
        if not category_caps:
            return None

        target = self._normalize_cap_lookup_key(cap_name)
        if isinstance(category_caps, dict):
            for key, value in category_caps.items():
                if self._normalize_cap_lookup_key(key) == target:
                    return value
                if isinstance(value, dict):
                    for name_field in ("name", "label", "title"):
                        if self._normalize_cap_lookup_key(value.get(name_field)) == target:
                            return value
        elif isinstance(category_caps, list):
            for value in category_caps:
                if isinstance(value, dict):
                    for name_field in ("name", "label", "title"):
                        if self._normalize_cap_lookup_key(value.get(name_field)) == target:
                            return value
        return None

    def _resolve_item_copy_cap_from_caps(self, town_hall: int, item_key: str) -> int | None:
        mapping = TH_CAP_NAME_MAP.get(item_key)
        if not mapping:
            return None
        category, cap_name = mapping

        entry = None
        try:
            entry = get_item_cap(int(town_hall), category, cap_name, None)
        except Exception:
            entry = None
        copy_count = self._extract_copy_count_from_cap(entry)
        if copy_count is not None:
            return max(1, copy_count)

        entry = self._find_cap_from_category_caps(int(town_hall), category, cap_name)
        copy_count = self._extract_copy_count_from_cap(entry)
        if copy_count is not None:
            return max(1, copy_count)
        return None

    def get_item_copy_cap(self, town_hall: int | None, item_key: str) -> int:
        if item_key not in TH_CAP_NAME_MAP:
            return max(1, int(MIN_COPY_FALLBACK_COUNTS.get(item_key, 1)))

        if town_hall:
            direct = self._resolve_item_copy_cap_from_caps(int(town_hall), item_key)
            if direct is not None:
                return direct

        resolved_counts: list[int] = []
        for th in sorted(TH_CAPS.keys()):
            count = self._resolve_item_copy_cap_from_caps(int(th), item_key)
            if count is not None:
                resolved_counts.append(int(count))
        if resolved_counts:
            return max(1, max(resolved_counts))

        return max(1, int(MIN_COPY_FALLBACK_COUNTS.get(item_key, 1)))

    def is_multi_copy_item(self, town_hall: int | None, item_key: str) -> bool:
        return self.get_item_copy_cap(town_hall, item_key) > 1

    def get_item_status(self, user: dict[str, Any], item_key: str, targets: dict[str, int] | None = None, levels: dict[str, int] | None = None) -> dict[str, Any]:
        if targets is None:
            targets = self.get_effective_targets(user)
        if levels is None:
            levels = self.get_effective_levels(user)
        target = int(targets.get(item_key, 0) or 0)
        town_hall = user.get("town_hall")
        copy_cap = self.get_item_copy_cap(town_hall, item_key)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user).get(item_key, [])

        if copy_cap > 1:
            if manual_copy_levels:
                confirmed = [max(0, int(v)) for v in manual_copy_levels[:copy_cap]]
            elif item_key in manual_levels:
                # Treat a plain /trackupgrade on a multi-copy manual item as
                # "all copies are at this same level". Users can still use
                # /trackcopies for mixed-level buildings and traps.
                inferred_level = max(0, int(manual_levels.get(item_key, 0) or 0))
                confirmed = [inferred_level] * copy_cap
            else:
                confirmed = []

            if confirmed:
                tracked_copies = len(confirmed)
                padded = confirmed + [0] * max(0, copy_cap - tracked_copies)
                done = sum(1 for lvl in padded if lvl >= target)
                lowest = min(padded) if padded else 0
                highest = max(padded) if padded else 0
                return {
                    "multi_copy": True,
                    "copy_cap": copy_cap,
                    "tracked": copy_cap,
                    "done": done,
                    "target": target,
                    "current": lowest,
                    "highest": highest,
                    "next_level": min(lowest + 1, target) if target > 0 else lowest + 1,
                    "gap": max(target - lowest, 0),
                    "remaining_copies": max(copy_cap - done, 0),
                    "tracked_copies": tracked_copies,
                    "untracked_copies": max(copy_cap - tracked_copies, 0),
                    "fully_confirmed": tracked_copies >= copy_cap,
                    "copy_levels": padded,
                }

        current = int(levels.get(item_key, 0) or 0)
        done = 1 if current >= target and target > 0 else 0
        return {
            "multi_copy": False,
            "copy_cap": 1,
            "tracked": 1,
            "done": done,
            "target": target,
            "current": current,
            "highest": current,
            "next_level": min(current + 1, target) if target > 0 else current + 1,
            "gap": max(target - current, 0),
            "remaining_copies": 0 if done else 1,
            "tracked_copies": 1 if item_key in levels or item_key in manual_levels else 0,
            "untracked_copies": 0,
            "fully_confirmed": True,
            "copy_levels": [current],
        }

    def get_synced_max_levels(self, user: dict[str, Any]) -> dict[str, int]:
        return {
            k: int(v)
            for k, v in (user.get("synced_max_levels") or {}).items()
            if k in ITEMS
        }

    def sanitize_target(self, item_key: str, current: int, target: int, town_hall: int | None = None, synced_max_levels: dict[str, int] | None = None) -> int:
        target = max(int(target), int(current))
        th_cap = self.get_th_cap_target(town_hall, item_key)
        if th_cap and th_cap > 0:
            target = min(target, int(th_cap))
            target = max(target, int(current))
        if synced_max_levels:
            hard_cap = int(synced_max_levels.get(item_key, 0) or 0)
            if hard_cap > 0:
                target = min(target, hard_cap)
                target = max(target, int(current))
        return target

    def get_effective_targets(self, user: dict[str, Any]) -> dict[str, int]:
        role = user.get("role", DEFAULT_ROLE)
        town_hall = user.get("town_hall")
        inferred = self.infer_default_targets(town_hall, role)
        targets = dict(inferred)
        targets.update({k: int(v) for k, v in (user.get("targets") or {}).items() if k in ITEMS})

        # TH caps are the source of truth for supported items.
        for item_key in TH_CAP_NAME_MAP:
            cap_target = self.get_th_cap_target(town_hall, item_key)
            if cap_target is not None:
                targets[item_key] = cap_target

        levels = self.get_effective_levels(user)
        synced_max_levels = self.get_synced_max_levels(user)

        sanitized: dict[str, int] = {}
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            current = int(levels.get(item_key, 0))
            sanitized[item_key] = self.sanitize_target(item_key, current, int(target), town_hall, synced_max_levels)

        return sanitized
    
    def clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def lane_weight(self, lane: str) -> float:
        return LANE_WEIGHTS.get(lane, 1.0)

    def compute_weighted_impact(self, meta: ItemMeta, role: str) -> float:
        role_weights = ROLE_WEIGHTS.get(role, ROLE_WEIGHTS[DEFAULT_ROLE])
        return (
            meta.offense * role_weights["offense"]
            + meta.farming * role_weights["farming"]
            + meta.defense * role_weights["defense"]
            + meta.utility * role_weights["utility"]
        )

    def compute_time_efficiency(self, weighted_impact: float, meta: ItemMeta) -> float:
        raw = (weighted_impact / max(meta.time_weight, 1.0)) * 10.0
        return round(self.clamp(raw, 0.0, 20.0), 2)

    def compute_cost_efficiency(self, weighted_impact: float, meta: ItemMeta) -> float:
        raw = (weighted_impact / max(meta.cost_weight, 1.0)) * 8.0
        return round(self.clamp(raw, 0.0, 16.0), 2)

    def compute_urgency(self, gap: int) -> float:
        raw = 3.0 + (gap * 2.4)
        return round(self.clamp(raw, 0.0, 16.0), 2)

    def compute_blocking_bonus(self, meta: ItemMeta) -> float:
        raw = meta.blocks_progress * 4.0 * self.lane_weight(meta.lane)
        return round(self.clamp(raw, 0.0, 10.0), 2)

    def build_lane_snapshot(self, user: dict[str, Any]) -> dict[str, dict[str, float]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        lanes: dict[str, dict[str, float]] = {
            "hero": {"tracked": 0, "done": 0, "percent": 100.0},
            "lab": {"tracked": 0, "done": 0, "percent": 100.0},
            "builder": {"tracked": 0, "done": 0, "percent": 100.0},
        }
        for item_key in targets:
            meta = ITEMS.get(item_key)
            if not meta:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            lane = meta.lane
            lanes.setdefault(lane, {"tracked": 0, "done": 0, "percent": 100.0})
            lanes[lane]["tracked"] += int(status.get("tracked", 0))
            lanes[lane]["done"] += int(status.get("done", 0))
        for lane, row in lanes.items():
            tracked = int(row.get("tracked", 0))
            done = int(row.get("done", 0))
            row["percent"] = round((done / tracked) * 100, 1) if tracked else 100.0
        return lanes

    def resolve_advisor_mode(self, user: dict[str, Any], requested_mode: str | None = None) -> str:
        mode = str(requested_mode or user.get("advisor_mode") or "auto").strip().lower()
        if mode in {"war", "farm"}:
            return mode
        role = str(user.get("role", DEFAULT_ROLE)).lower()
        return "farm" if role == "farmer" else "war"

    def _normalize_pressure_value(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric > 1.0:
                numeric = numeric / 100.0
            return max(0.0, min(1.0, numeric))
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "")
            if not cleaned:
                return 0.0
            try:
                numeric = float(cleaned)
                if numeric > 1.0:
                    numeric = numeric / 100.0
                return max(0.0, min(1.0, numeric))
            except ValueError:
                return 0.0
        return 0.0

    def _extract_resource_pressure(self, user: dict[str, Any]) -> dict[str, float]:
        resources = dict(user.get("resources") or {})
        storages = dict(user.get("storage_pressure") or {})
        return {
            "gold": self._normalize_pressure_value(user.get("gold_pressure", resources.get("gold_pressure", storages.get("gold", user.get("gold_fill"))))),
            "elixir": self._normalize_pressure_value(user.get("elixir_pressure", resources.get("elixir_pressure", storages.get("elixir", user.get("elixir_fill"))))),
            "dark_elixir": self._normalize_pressure_value(user.get("dark_elixir_pressure", resources.get("dark_elixir_pressure", storages.get("dark_elixir", user.get("dark_elixir_fill"))))),
        }

    def _extract_hero_availability(self, user: dict[str, Any]) -> dict[str, Any]:
        hero_keys = {
            "king_up": ("king_up", "barbarian_king_up", "bk_up"),
            "queen_up": ("queen_up", "archer_queen_up", "aq_up"),
            "warden_up": ("warden_up", "grand_warden_up", "gw_up"),
            "rc_up": ("rc_up", "royal_champion_up", "champ_up"),
        }
        availability: dict[str, Any] = {}
        down_count = 0
        any_known = False
        for output_key, candidates in hero_keys.items():
            raw = None
            for key in candidates:
                if key in user:
                    raw = user.get(key)
                    break
            if raw is None:
                availability[output_key] = None
                continue
            is_up = bool(raw)
            any_known = True
            availability[output_key] = is_up
            if not is_up:
                down_count += 1
        availability["down_count"] = down_count if any_known else 0
        availability["known"] = any_known
        return availability

    def _extract_war_state(self, user: dict[str, Any]) -> dict[str, Any]:
        raw = dict(user.get("war_state") or {})
        in_war = bool(
            raw.get("in_war")
            or user.get("in_war")
            or user.get("war_active")
            or user.get("war_day")
            or user.get("war_live")
        )
        war_prepping = bool(
            raw.get("war_prepping")
            or user.get("war_prepping")
            or user.get("prep_day")
            or user.get("war_prep")
        )
        cwl = bool(
            raw.get("cwl")
            or user.get("cwl")
            or user.get("cwl_active")
            or user.get("league_war")
        )
        return {
            "in_war": in_war,
            "war_prepping": war_prepping,
            "cwl": cwl,
            "active": bool(in_war or war_prepping or cwl),
        }

    def get_timing_context(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> dict[str, Any]:
        mode = self.resolve_advisor_mode(user, requested_mode)
        if builder_idle is None:
            builder_idle = bool(user.get("builder_idle") or user.get("builders_idle") or user.get("builder_free"))
        if lab_idle is None:
            lab_idle = bool(user.get("lab_idle") or user.get("laboratory_idle") or user.get("lab_free"))

        lane_snapshot = self.build_lane_snapshot(user)
        resource_pressure = self._extract_resource_pressure(user)
        hero_availability = self._extract_hero_availability(user)
        war_state = self._extract_war_state(user)

        hero_pct = float(lane_snapshot.get("hero", {}).get("percent", 100.0))
        lab_pct = float(lane_snapshot.get("lab", {}).get("percent", 100.0))
        builder_pct = float(lane_snapshot.get("builder", {}).get("percent", 100.0))
        account_pressure = {
            "hero_lane": round(max(0.0, min(1.0, (100.0 - hero_pct) / 100.0)), 3),
            "lab_lane": round(max(0.0, min(1.0, (100.0 - lab_pct) / 100.0)), 3),
            "builder_lane": round(max(0.0, min(1.0, (100.0 - builder_pct) / 100.0)), 3),
            "offense_core": round(
                max(
                    0.0,
                    min(
                        1.0,
                        (
                            resource_pressure["dark_elixir"]
                            + (1.0 if not hero_availability.get("known") else hero_availability.get("down_count", 0) / 4.0)
                        )
                        / 2.0,
                    ),
                ),
                3,
            ),
        }

        if mode == "auto":
            if war_state["active"]:
                resolved_mode = "war"
            elif resource_pressure["gold"] >= 0.85 or resource_pressure["elixir"] >= 0.85 or resource_pressure["dark_elixir"] >= 0.85:
                resolved_mode = "farm"
            elif account_pressure["hero_lane"] >= max(account_pressure["lab_lane"], account_pressure["builder_lane"]) and account_pressure["hero_lane"] >= 0.35:
                resolved_mode = "war"
            else:
                resolved_mode = "farm" if str(user.get("role", DEFAULT_ROLE)).lower() == "farmer" else "war"
        else:
            resolved_mode = mode

        upgrade_window = {
            "short_builders": int(user.get("short_builders") or (1 if builder_idle else 0)),
            "long_builders": int(user.get("long_builders") or 0),
            "lab_finishing_soon": bool(user.get("lab_finishing_soon") or user.get("lab_soon")),
        }

        return {
            "mode": resolved_mode,
            "requested_mode": mode,
            "builder_idle": bool(builder_idle),
            "lab_idle": bool(lab_idle),
            "resource_pressure": resource_pressure,
            "hero_availability": hero_availability,
            "war_state": war_state,
            "account_pressure": account_pressure,
            "upgrade_window": upgrade_window,
        }

    def compute_strategic_bonus(self, *, item_key: str, meta: ItemMeta, current: int, target: int, role: str, user: dict[str, Any] | None = None, lane_snapshot: dict[str, Any] | None = None, milestone_state: dict[str, Any] | None = None, timing_context: dict[str, Any] | None = None) -> tuple[float, list[str]]:
        bonus = 0.0
        reasons: list[str] = []
        gap = max(target - current, 0)
        if not user:
            return bonus, reasons

        milestone_state = milestone_state or self.get_milestone_state(user)
        achieved = milestone_state.get("achieved", {})
        groups = milestone_state.get("group_status", {})
        lane_snapshot = lane_snapshot or self.build_lane_snapshot(user)
        timing_context = timing_context or self.get_timing_context(user)
        mode = str(timing_context.get("mode", "war"))
        builder_idle = bool(timing_context.get("builder_idle", False))
        lab_idle = bool(timing_context.get("lab_idle", False))
        resource_pressure = dict(timing_context.get("resource_pressure") or {})
        war_state = dict(timing_context.get("war_state") or {})
        hero_availability = dict(timing_context.get("hero_availability") or {})
        account_pressure = dict(timing_context.get("account_pressure") or {})
        upgrade_window = dict(timing_context.get("upgrade_window") or {})

        hero_pct = float(lane_snapshot.get("hero", {}).get("percent", 100.0))
        lab_pct = float(lane_snapshot.get("lab", {}).get("percent", 100.0))
        builder_pct = float(lane_snapshot.get("builder", {}).get("percent", 100.0))
        lowest_lane = min(("hero", hero_pct), ("lab", lab_pct), ("builder", builder_pct), key=lambda x: x[1])[0]

        if meta.lane == lowest_lane and lane_snapshot.get(lowest_lane, {}).get("tracked", 0):
            lane_gap = max(hero_pct, lab_pct, builder_pct) - float(lane_snapshot.get(lowest_lane, {}).get("percent", 100.0))
            lane_bonus = min(7.0, round(lane_gap / 9.0, 1))
            if lane_bonus > 0:
                bonus += lane_bonus
                reasons.append(f"{lowest_lane.title()} lane is your most behind right now.")

        if not achieved.get("war_ready"):
            if item_key in HERO_KEYS:
                bonus += 8.0
                reasons.append("Hero progress directly pushes your war-ready checkpoint.")
            elif item_key in OFFENSE_CORE_KEYS:
                bonus += 6.5
                reasons.append("This helps close your core war offense gap.")
            elif role == "attacker" and meta.category in {"defense", "economy", "trap"}:
                bonus -= 6.0
                reasons.append("War value is lagging, so this can wait behind offense.")

        if not achieved.get("heroes_complete") and item_key in HERO_KEYS:
            remaining = max(0, int(groups.get("heroes", {}).get("total", 0)) - int(groups.get("heroes", {}).get("done", 0)))
            bonus += 5.5
            if remaining:
                reasons.append(f"Hero targets are still incomplete ({remaining} remaining).")

        if not achieved.get("offense_core_complete") and item_key in OFFENSE_CORE_KEYS:
            bonus += 5.0
            reasons.append("This is part of your tracked offense core.")

        if not achieved.get("builder_core_complete") and item_key in BUILDER_CORE_KEYS:
            bonus += 4.5
            reasons.append("Builder core is still unfinished, so this unlocks cleaner follow-up choices.")

        if gap == 1:
            bonus += 5.0
            reasons.append("One level finishes this target immediately.")
        elif gap == 2:
            bonus += 2.5
            reasons.append("Only two levels remain to finish this target.")

        if role == "attacker" and meta.category in {"troop", "spell", "hero", "siege", "pet"} and meta.offense >= 8:
            bonus += 3.0
        elif role == "farmer" and meta.category in {"economy", "hero", "building"} and meta.farming >= 4:
            bonus += 2.5

        if mode == "war":
            if meta.category in {"hero", "troop", "spell", "siege", "pet"}:
                war_bonus = 4.5 if meta.offense >= 8 else 2.0
                bonus += war_bonus
                reasons.append("War mode is pushing offense-first value.")
            elif meta.category in {"economy", "defense", "trap"}:
                bonus -= 5.0
                reasons.append("War mode is holding lower-value farm/defense work for later.")
            elif meta.category == "building" and item_key in OFFENSE_CORE_KEYS | BUILDER_CORE_KEYS:
                bonus += 2.5
                reasons.append("War mode still values core unlock buildings.")
        elif mode == "farm":
            if meta.category in {"economy", "building"}:
                farm_bonus = 4.0 if meta.farming >= 4 or meta.utility >= 7 else 2.0
                bonus += farm_bonus
                reasons.append("Farm mode is favoring economy and progression flow.")
            elif meta.category in {"defense", "trap"}:
                bonus += 1.5
            elif meta.category in {"siege", "spell", "troop"} and meta.offense >= 8:
                bonus -= 2.5
                reasons.append("Farm mode is letting pure war offense wait a bit.")

        if builder_idle:
            if meta.lane == "builder":
                bonus += 10.0
                reasons.append("A builder is idle, so builder work gets immediate value.")
            else:
                bonus -= 1.5
        if lab_idle:
            if meta.lane == "lab":
                bonus += 10.0
                reasons.append("Your lab is idle, so lab upgrades jump the queue.")
            else:
                bonus -= 1.5

        if float(resource_pressure.get("dark_elixir", 0.0)) >= 0.85 and meta.category in {"hero", "pet"}:
            bonus += 6.0
            reasons.append("Dark elixir pressure is high, so hero/pet value rises.")
        if float(resource_pressure.get("gold", 0.0)) >= 0.85 and meta.category in {"building", "defense", "trap", "economy"}:
            bonus += 4.0
            reasons.append("Gold is filling up, so builder-side spending becomes more urgent.")
        if float(resource_pressure.get("elixir", 0.0)) >= 0.85 and meta.category in {"troop", "spell", "siege", "building", "economy"}:
            bonus += 4.0
            reasons.append("Elixir pressure is high, so lab/progression work gets a bump.")

        if war_state.get("war_prepping") and meta.category in {"hero", "pet"}:
            bonus -= 4.5
            reasons.append("War prep is active, so extra hero downtime is less attractive.")
        if war_state.get("in_war") and meta.category in {"hero", "pet"}:
            bonus -= 6.0
            reasons.append("You are in war, so hero downtime is being held back.")
        if war_state.get("cwl") and meta.category in {"troop", "spell", "siege"}:
            bonus += 5.0
            reasons.append("CWL pressure boosts immediate army value.")

        if hero_availability.get("known") and hero_availability.get("down_count", 0) >= 2 and meta.category in {"hero", "pet"} and mode == "war":
            bonus -= 3.5
            reasons.append("Multiple heroes are already down, so more war downtime is less ideal.")

        if float(account_pressure.get("hero_lane", 0.0)) >= 0.60 and meta.lane == "hero":
            bonus += 4.0
            reasons.append("Hero lane pressure is high right now.")
        if float(account_pressure.get("lab_lane", 0.0)) >= 0.60 and meta.lane == "lab":
            bonus += 3.5
            reasons.append("Lab lane is lagging behind your other progress.")
        if float(account_pressure.get("builder_lane", 0.0)) >= 0.60 and meta.lane == "builder":
            bonus += 3.5
            reasons.append("Builder lane is your biggest structural backlog.")

        if bool(upgrade_window.get("lab_finishing_soon")) and meta.lane == "lab":
            bonus += 2.5
            reasons.append("Your lab is finishing soon, so planning the next lab step has extra value.")

        return round(bonus, 2), reasons[:3]

    def score_candidate(self, *, item_key: str, current: int, target: int, role: str, user: dict[str, Any] | None = None, lane_snapshot: dict[str, Any] | None = None, milestone_state: dict[str, Any] | None = None, timing_context: dict[str, Any] | None = None) -> dict[str, Any]:
        meta = ITEMS[item_key]
        gap = max(target - current, 0)

        if gap <= 0:
            return {
                "item_key": item_key,
                "label": meta.label,
                "score": 0.0,
                "priority": "Done",
                "current": current,
                "next_level": current,
                "target": target,
                "gap": 0,
                "reasons": ["At or above advisor target."],
                "score_breakdown": {},
            }

        next_level = current + 1

        weighted_impact = self.compute_weighted_impact(meta, role)
        impact_score = round(weighted_impact * 3.8, 2)
        time_efficiency = self.compute_time_efficiency(weighted_impact, meta)
        cost_efficiency = self.compute_cost_efficiency(weighted_impact, meta)
        urgency = self.compute_urgency(gap)
        blocking_bonus = self.compute_blocking_bonus(meta)

        foundational_bonus = 6.0 if meta.foundational else 0.0
        breakpoint_bonus = 5.0 if next_level in meta.breakpoints else 0.0
        role_bonus = float(meta.role_bonus.get(role, 0.0))
        finish_bonus = 4.0 if next_level >= target else 0.0
        strategic_bonus, strategic_reasons = self.compute_strategic_bonus(
            item_key=item_key,
            meta=meta,
            current=current,
            target=target,
            role=role,
            user=user,
            lane_snapshot=lane_snapshot,
            milestone_state=milestone_state,
            timing_context=timing_context,
        )

        score = round(
            impact_score
            + time_efficiency
            + cost_efficiency
            + urgency
            + blocking_bonus
            + foundational_bonus
            + breakpoint_bonus
            + role_bonus
            + finish_bonus
            + strategic_bonus,
            1,
        )

        if score >= 90:
            priority = "High"
        elif score >= 65:
            priority = "Medium"
        else:
            priority = "Low"

        reasons: list[str] = []

        if meta.foundational:
            reasons.append("Unlocks stronger follow-up upgrades.")
        if blocking_bonus >= 7:
            reasons.append("High blocker value, so it is worth clearing early.")
        if time_efficiency >= 14:
            reasons.append("Excellent time-to-value upgrade.")
        elif time_efficiency >= 10:
            reasons.append("Strong value for the time invested.")
        if cost_efficiency >= 11:
            reasons.append("Good value for the resource cost.")
        if gap >= 5:
            reasons.append(f"You are {gap} levels behind target here.")
        elif gap >= 3:
            reasons.append(f"Still {gap} levels away from target.")
        if next_level in meta.breakpoints:
            reasons.append(f"Level {next_level} is a meaningful breakpoint.")
        if role == "attacker" and meta.offense >= 8:
            reasons.append("Very strong for your attacker profile.")
        elif role == "farmer" and meta.farming >= 8:
            reasons.append("Very efficient for a farmer profile.")
        elif role == "hybrid" and (meta.offense + meta.utility) >= 13:
            reasons.append("Strong balanced value for a hybrid profile.")

        for strategic_reason in strategic_reasons:
            if strategic_reason not in reasons:
                reasons.append(strategic_reason)

        if not reasons:
            reasons.append("Solid upgrade with balanced short-term value.")

        return {
            "item_key": item_key,
            "label": meta.label,
            "score": score,
            "priority": priority,
            "current": current,
            "next_level": next_level,
            "target": target,
            "gap": gap,
            "lane": meta.lane,
            "mode": (timing_context or {}).get("mode", "war") if timing_context else "war",
            "builder_idle": bool((timing_context or {}).get("builder_idle", False)) if timing_context else False,
            "lab_idle": bool((timing_context or {}).get("lab_idle", False)) if timing_context else False,
            "reasons": reasons[:3],
            "score_breakdown": {
                "impact": round(impact_score, 1),
                "time": round(time_efficiency, 1),
                "cost": round(cost_efficiency, 1),
                "urgency": round(urgency, 1),
                "blocking": round(blocking_bonus, 1),
                "foundational": round(foundational_bonus, 1),
                "breakpoint": round(breakpoint_bonus, 1),
                "role": round(role_bonus, 1),
                "finish": round(finish_bonus, 1),
                "strategy": round(strategic_bonus, 1),
            },
        }
    
    def classify_recommendation_timing(self, rec: dict[str, Any]) -> str:
        breakdown = rec.get("score_breakdown", {})
        time_score = float(breakdown.get("time", 0.0))
        cost_score = float(breakdown.get("cost", 0.0))
        blocking_score = float(breakdown.get("blocking", 0.0))
        urgency_score = float(breakdown.get("urgency", 0.0))
        total_score = float(rec.get("score", 0.0))

        if total_score >= 95 and (time_score >= 11 or blocking_score >= 7):
            return "do_now"

        if blocking_score >= 8:
            return "do_now"

        if urgency_score >= 12 and time_score >= 9:
            return "do_now"

        if total_score >= 78:
            return "good_next"

        if cost_score < 7 and time_score < 8:
            return "wait"

        if blocking_score >= 5 and (time_score < 8 or cost_score < 8):
            return "save_for"

        return "good_next"

    def build_decision_summary(self, rec: dict[str, Any]) -> str:
        decision = self.classify_recommendation_timing(rec)

        if decision == "do_now":
            return "Do this now"
        if decision == "good_next":
            return "Good next move"
        if decision == "wait":
            return "Wait on this"
        if decision == "save_for":
            return "Save for this"

        return "Recommended"

    def build_decision_reason(self, rec: dict[str, Any], role: str) -> str:
        breakdown = rec.get("score_breakdown", {})
        time_score = float(breakdown.get("time", 0.0))
        cost_score = float(breakdown.get("cost", 0.0))
        blocking_score = float(breakdown.get("blocking", 0.0))
        urgency_score = float(breakdown.get("urgency", 0.0))
        impact_score = float(breakdown.get("impact", 0.0))
        strategy_score = float(breakdown.get("strategy", 0.0))
        gap = int(rec.get("gap", 0))
        lane = str(rec.get("lane", "builder"))

        reasons: list[str] = []

        if impact_score >= 28:
            if role == "attacker":
                reasons.append("strong war value")
            elif role == "farmer":
                reasons.append("strong farming value")
            else:
                reasons.append("strong all-around value")

        if time_score >= 14:
            reasons.append("fast payoff")
        elif time_score >= 10:
            reasons.append("good time efficiency")

        if cost_score >= 11:
            reasons.append("good resource value")
        elif cost_score <= 6:
            reasons.append("resource heavy")

        if blocking_score >= 7:
            reasons.append("clears a progression bottleneck")

        if strategy_score >= 8:
            reasons.append("fits your current account checkpoint")
        elif strategy_score >= 4:
            reasons.append("lines up with your current progression pressure")

        if urgency_score >= 12 or gap >= 5:
            reasons.append("you are far behind target")
        elif gap >= 3:
            reasons.append("you are still behind target")

        if lane == "hero":
            reasons.append("uses your hero lane")
        elif lane == "lab":
            reasons.append("fits your lab lane")
        elif lane == "builder":
            reasons.append("fits your builder lane")

        if not reasons:
            reasons.append("solid upgrade value")

        return ", ".join(reasons[:3]).capitalize() + "."

    def build_decision_block(self, recs: list[dict[str, Any]], role: str) -> str:
        lines: list[str] = []

        for idx, rec in enumerate(recs, start=1):
            summary = self.build_decision_summary(rec)
            reason = self.build_decision_reason(rec, role)

            lines.append(
                f"**{idx}. {rec['label']} → {rec['next_level']}**\n"
                f"{summary} — {reason}"
            )

        return "\n\n".join(lines)

    def build_waitlist(self, recs: list[dict[str, Any]], role: str, limit: int = 2) -> str:
        if not recs:
            return "Nothing to hold for later right now."

        ranked = sorted(
            recs,
            key=lambda row: (
                self.classify_recommendation_timing(row) not in {"wait", "save_for"},
                -float(row.get("score", 0.0)),
            ),
        )

        wait_items = [r for r in ranked if self.classify_recommendation_timing(r) in {"wait", "save_for"}][:limit]

        if not wait_items:
            return "Top options are all immediately solid right now."

        parts = []
        for rec in wait_items:
            summary = self.build_decision_summary(rec)
            reason = self.build_decision_reason(rec, role)
            parts.append(f"**{rec['label']}** — {summary.lower()} because {reason[:-1].lower()}")

        return "\n".join(parts)

    def build_recommendations(self, user: dict[str, Any], count: int = 5, requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> list[dict[str, Any]]:
        role = user.get("role", DEFAULT_ROLE)
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        candidates: list[dict[str, Any]] = []
        lane_snapshot = self.build_lane_snapshot(user)
        milestone_state = self.get_milestone_state(user)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            current = int(status.get("current", 0))
            if bool(status.get("multi_copy")):
                if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                    continue
                if int(status.get("untracked_copies", 0)) > 0 and current >= int(target):
                    continue
                rec = self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context)
                rec["multi_copy"] = True
                rec["copy_cap"] = int(status.get("copy_cap", 1))
                rec["done_copies"] = int(status.get("done", 0))
                rec["tracked_copies"] = int(status.get("tracked_copies", 0))
                rec["remaining_copies"] = int(status.get("remaining_copies", 0))
                rec["untracked_copies"] = int(status.get("untracked_copies", 0))
                rec["copy_levels"] = list(status.get("copy_levels", []))
                if rec["untracked_copies"] > 0:
                    rec.setdefault("reasons", []).append(f"Track the remaining {rec['untracked_copies']} copy/copies manually to unlock full count progress.")
                elif rec["remaining_copies"] > 1:
                    rec.setdefault("reasons", []).append(f"{rec['done_copies']}/{rec['copy_cap']} copies are already at target.")
                candidates.append(rec)
                continue
            if current >= target:
                continue
            candidates.append(self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context))

        candidates.sort(key=lambda row: (-row["score"], row["label"].lower()))
        return candidates[: max(1, min(count, 10))]

    def build_recommendation_pool(self, user: dict[str, Any], count: int = 5, pool_size: int = 8, requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        role = user.get("role", DEFAULT_ROLE)
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        candidates: list[dict[str, Any]] = []
        lane_snapshot = self.build_lane_snapshot(user)
        milestone_state = self.get_milestone_state(user)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            current = int(status.get("current", 0))
            if bool(status.get("multi_copy")):
                if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                    continue
                if int(status.get("untracked_copies", 0)) > 0 and current >= int(target):
                    continue
                rec = self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context)
                rec["multi_copy"] = True
                rec["copy_cap"] = int(status.get("copy_cap", 1))
                rec["done_copies"] = int(status.get("done", 0))
                rec["tracked_copies"] = int(status.get("tracked_copies", 0))
                rec["remaining_copies"] = int(status.get("remaining_copies", 0))
                rec["untracked_copies"] = int(status.get("untracked_copies", 0))
                rec["copy_levels"] = list(status.get("copy_levels", []))
                if rec["untracked_copies"] > 0:
                    rec.setdefault("reasons", []).append(f"Track the remaining {rec['untracked_copies']} copy/copies manually to unlock full count progress.")
                elif rec["remaining_copies"] > 1:
                    rec.setdefault("reasons", []).append(f"{rec['done_copies']}/{rec['copy_cap']} copies are already at target.")
                candidates.append(rec)
                continue
            if current >= target:
                continue
            candidates.append(self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context))

        candidates.sort(key=lambda row: (-row["score"], row["label"].lower()))

        top = candidates[: max(1, min(count, 10))]
        pool = candidates[: max(len(top), min(pool_size, 12))]
        return top, pool

    def build_progress_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        if not targets:
            return {"tracked": 0, "done": 0, "percent": 0, "bar": "░░░░░░░░░░"}

        tracked = 0
        done = 0
        for item_key in targets:
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            tracked += int(status.get("tracked", 0))
            done += int(status.get("done", 0))

        percent = round((done / tracked) * 100) if tracked else 0
        filled = max(0, min(10, round(percent / 10)))
        bar = FULL * filled + EMPTY * (10 - filled)
        return {"tracked": tracked, "done": done, "percent": percent, "bar": bar}

    def build_tracking_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        targets = self.get_effective_targets(user)
        levels = self.get_effective_levels(user)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user)

        if not targets:
            return {"tracked": 0, "total": 0, "percent": 0, "bar": "░░░░░░░░░░"}

        tracked = 0
        total = 0
        for item_key in targets:
            meta = ITEMS.get(item_key)
            if not meta:
                continue

            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            slot_total = int(status.get("tracked", 0))
            total += slot_total

            if meta.source != "manual":
                tracked += slot_total
                continue

            if int(status.get("copy_cap", 1)) > 1:
                if item_key in manual_levels and item_key not in manual_copy_levels:
                    tracked += slot_total
                else:
                    tracked += min(int(status.get("tracked_copies", 0)), slot_total)
            elif item_key in manual_levels or item_key in manual_copy_levels:
                tracked += 1

        percent = round((tracked / total) * 100) if total else 0
        filled = max(0, min(10, round(percent / 10)))
        bar = FULL * filled + EMPTY * (10 - filled)
        return {"tracked": tracked, "total": total, "percent": percent, "bar": bar}

    def _counts_for_confirmed_milestones(self, user: dict[str, Any], key: str) -> bool:
        if key not in ITEMS:
            return False
        meta = ITEMS[key]
        if meta.source != "manual":
            return True
        if self.is_multi_copy_item(user.get("town_hall"), key):
            copy_levels = self.get_manual_copy_levels(user).get(key, [])
            return len(copy_levels) >= self.get_item_copy_cap(user.get("town_hall"), key)
        return key in (user.get("manual_levels") or {})

    def _milestone_group_complete(self, user: dict[str, Any], keys: set[str]) -> tuple[bool, int, int]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        relevant = [
            key for key in keys
            if key in ITEMS and key in targets and self._counts_for_confirmed_milestones(user, key)
        ]
        if not relevant:
            return False, 0, 0

        done = 0
        for key in relevant:
            status = self.get_item_status(user, key, targets=targets, levels=levels)
            if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                done += 1

        return done == len(relevant), done, len(relevant)

        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        relevant = [
            key for key in keys
            if key in ITEMS and key in targets and self._counts_for_confirmed_milestones(user, key)
        ]
        if not relevant:
            return False, 0, 0

        done = 0
        for key in relevant:
            current = int(levels.get(key, 0))
            target = int(targets.get(key, 0))
            if current >= target:
                done += 1

        return done == len(relevant), done, len(relevant)

    def get_milestone_state(self, user: dict[str, Any]) -> dict[str, Any]:
        progress = self.build_progress_snapshot(user)
        percent = int(progress.get("percent", 0))

        progress_hits = [mark for mark in MILESTONE_PROGRESS_MARKS if percent >= mark]

        heroes_complete, heroes_done, heroes_total = self._milestone_group_complete(user, HERO_KEYS)
        offense_complete, offense_done, offense_total = self._milestone_group_complete(user, OFFENSE_CORE_KEYS)
        builder_complete, builder_done, builder_total = self._milestone_group_complete(user, BUILDER_CORE_KEYS)

        role = user.get("role", DEFAULT_ROLE)
        war_ready = heroes_complete and offense_complete and percent >= 60
        if role == "farmer":
            war_ready = heroes_complete and percent >= 60

        achieved = {
            "progress_marks": progress_hits,
            "heroes_complete": heroes_complete,
            "offense_core_complete": offense_complete,
            "builder_core_complete": builder_complete,
            "war_ready": war_ready,
        }

        return {
            "progress": progress,
            "achieved": achieved,
            "group_status": {
                "heroes": {"done": heroes_done, "total": heroes_total},
                "offense": {"done": offense_done, "total": offense_total},
                "builder": {"done": builder_done, "total": builder_total},
            },
        }

    def get_new_milestones(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> list[str]:
        before_state = self.get_milestone_state(before_user)
        after_state = self.get_milestone_state(after_user)

        before_achieved = before_state["achieved"]
        after_achieved = after_state["achieved"]

        new_hits: list[str] = []

        before_marks = set(before_achieved.get("progress_marks", []))
        after_marks = set(after_achieved.get("progress_marks", []))
        for mark in sorted(after_marks - before_marks):
            new_hits.append(f"Reached **{mark}%** tracked progress.")

        if after_achieved.get("heroes_complete") and not before_achieved.get("heroes_complete"):
            new_hits.append("Completed all tracked **hero targets**.")

        if after_achieved.get("offense_core_complete") and not before_achieved.get("offense_core_complete"):
            new_hits.append("Confirmed all tracked **offense-core** targets.")

        if after_achieved.get("builder_core_complete") and not before_achieved.get("builder_core_complete"):
            new_hits.append("Confirmed all tracked **builder-core** targets.")

        if after_achieved.get("war_ready") and not before_achieved.get("war_ready"):
            new_hits.append("Unlocked your **war-ready checkpoint**.")

        return new_hits

    def build_milestone_summary(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]

        badges: list[str] = []

        progress_marks = achieved.get("progress_marks", [])
        if progress_marks:
            badges.append(f"Progress: **{max(progress_marks)}%**")
        else:
            badges.append("Progress: **0%**")

        if achieved.get("heroes_complete"):
            badges.append("Heroes: **Complete**")
        else:
            badges.append(f"Heroes: **{groups['heroes']['done']}/{groups['heroes']['total']}**")

        if achieved.get("offense_core_complete"):
            badges.append("Offense Core Confirmed: **Complete**")
        elif groups["offense"]["total"] > 0:
            badges.append(f"Offense Core Confirmed: **{groups['offense']['done']}/{groups['offense']['total']}**")

        if achieved.get("builder_core_complete"):
            badges.append("Builder Core Confirmed: **Complete**")
        elif groups["builder"]["total"] > 0:
            badges.append(f"Builder Core Confirmed: **{groups['builder']['done']}/{groups['builder']['total']}**")

        badges.append("War Ready: **Yes**" if achieved.get("war_ready") else "War Ready: **Not yet**")
        return " | ".join(badges)

    def build_milestone_celebration(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> str:
        new_hits = self.get_new_milestones(before_user, after_user)
        if not new_hits:
            return "No new milestone unlocked this sync."

        return "\n".join(f"• {hit}" for hit in new_hits[:4])

    def build_milestone_hint(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]

        if not achieved.get("heroes_complete") and groups["heroes"]["total"] > 0:
            remaining = groups["heroes"]["total"] - groups["heroes"]["done"]
            return f"Closest confirmed milestone: finish your **hero targets** ({remaining} remaining)."

        if not achieved.get("offense_core_complete") and groups["offense"]["total"] > 0:
            remaining = groups["offense"]["total"] - groups["offense"]["done"]
            return f"Closest confirmed milestone: finish your **offense core** ({remaining} remaining)."

        if not achieved.get("builder_core_complete") and groups["builder"]["total"] > 0:
            remaining = groups["builder"]["total"] - groups["builder"]["done"]
            return f"Closest confirmed milestone: finish your **builder core** ({remaining} remaining)."

        if not achieved.get("war_ready"):
            return "Closest confirmed milestone: push overall tracked progress high enough for **war-ready**."

        return "Major milestones complete. Time to raise targets and keep climbing."

    def build_mini_progress_bar(self, current: int, target: int, width: int = 8) -> str:
        target = max(1, int(target or 1))
        current = max(0, min(int(current or 0), target))
        filled = round((current / target) * width)
        filled = max(0, min(width, filled))
        return FULL * filled + EMPTY * (width - filled)

    def format_recommendation_card(self, rec: dict[str, Any], idx: int) -> str:
        meta = ITEMS.get(rec["key"])
        lane_emoji = LANE_EMOJIS.get(rec.get("lane", ""), "📌")
        category_emoji = CATEGORY_EMOJIS.get(getattr(meta, "category", ""), "📌")
        timing = self.classify_recommendation_timing(rec)
        timing_emoji = TIMING_EMOJIS.get(timing, "📌")
        progress_bar = self.build_mini_progress_bar(int(rec.get("current", 0)), int(rec.get("target", 1)))
        gap = max(0, int(rec.get("target", 0)) - int(rec.get("current", 0)))
        reason = (rec.get("reasons") or ["Good overall value right now."])[0]
        return (
            f"{timing_emoji} **#{idx} {rec['label']}** {lane_emoji}{category_emoji}\n"
            f"Lvl **{rec['current']} → {rec['next_level']}** of **{rec['target']}**  `{progress_bar}`\n"
            f"Gap: **{gap}** | Score: **{rec['score']}** | {reason}"
        )

    def build_upgrade_dashboard(self, recs: list[dict[str, Any]]) -> str:
        if not recs:
            return "Nothing urgent right now."
        return "\n\n".join(self.format_recommendation_card(rec, idx) for idx, rec in enumerate(recs, start=1))

    def build_lane_summary(self, recs: list[dict[str, Any]]) -> str:
        if not recs:
            return "No lane pressure detected."

        lane_rows: dict[str, list[dict[str, Any]]] = {"hero": [], "lab": [], "builder": []}
        for rec in recs:
            lane_rows.setdefault(rec.get("lane", "builder"), []).append(rec)

        lines: list[str] = []
        for lane in ("hero", "lab", "builder"):
            items = lane_rows.get(lane) or []
            if not items:
                continue
            best = items[0]
            lines.append(f"{LANE_EMOJIS.get(lane, '📌')} **{lane.title()} lane:** {best['label']} → **{best['next_level']}**")
        return "\n".join(lines[:3]) if lines else "No lane pressure detected."

    def build_quick_status_block(self, user: dict[str, Any], recs: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        role = user.get("role", DEFAULT_ROLE).title()
        state = self.get_milestone_state(user)
        war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"
        lane_snapshot = self.build_lane_snapshot(user)
        pressure_lane = min((lane, float(data.get("percent", 100.0))) for lane, data in lane_snapshot.items()) if lane_snapshot else ("none", 100.0)
        top_lane = pressure_lane[0].title() if recs else "None"
        timing_context = timing_context or self.get_timing_context(user)
        mode = str(timing_context.get("mode", "war")).title()
        builder_state = "Idle" if timing_context.get("builder_idle") else "Busy/Unknown"
        lab_state = "Idle" if timing_context.get("lab_idle") else "Busy/Unknown"
        war_state = dict(timing_context.get("war_state") or {})
        resource_pressure = dict(timing_context.get("resource_pressure") or {})
        war_state_label = "CWL" if war_state.get("cwl") else ("In War" if war_state.get("in_war") else ("Prep" if war_state.get("war_prepping") else "None"))
        hottest_resource = max(resource_pressure.items(), key=lambda kv: kv[1])[0] if resource_pressure else "none"
        hottest_value = int(round(float(resource_pressure.get(hottest_resource, 0.0)) * 100)) if resource_pressure else 0
        return (
            f"🎯 **Role:** {role}\n"
            f"🏠 **Town Hall:** {user.get('town_hall') or '?'}\n"
            f"📈 **Progress:** {progress['percent']}% ({progress['done']}/{progress['tracked']})\n"
            f"🔥 **War Ready:** {war_ready}\n"
            f"🧭 **Top pressure lane:** {top_lane}\n"
            f"⚙️ **Mode:** {mode}\n"
            f"🪖 **War state:** {war_state_label}\n"
            f"💰 **Top resource pressure:** {hottest_resource.replace('_', ' ').title()} ({hottest_value}%)\n"
            f"🛠️ **Builders:** {builder_state}\n"
            f"🧪 **Lab:** {lab_state}"
        )

    def _get_economy(self, user: dict[str, Any]) -> dict[str, Any]:
        econ = dict(user.get("advisor_economy") or {})
        econ.setdefault("coins", 0)
        econ.setdefault("efficiency_score", 0)
        econ.setdefault("followed_paths", 0)
        econ.setdefault("missed_paths", 0)
        econ.setdefault("last_recommendations", [])
        econ.setdefault("last_award_at", None)
        return econ

    def build_economy_summary(self, user: dict[str, Any]) -> str:
        econ = self._get_economy(user)
        velocity = self.get_progress_velocity(user)
        return (
            f"🪙 **Coins:** {int(econ.get('coins', 0))}\n"
            f"📈 **Efficiency:** {int(econ.get('efficiency_score', 0))}\n"
            f"✅ **Paths followed:** {int(econ.get('followed_paths', 0))}\n"
            f"🚀 **Progress/day:** {velocity.get('points_per_day', 0):.2f} goals\n"
            f"⭐ **Rating:** {velocity.get('rating', 'Unrated')}"
        )

    def _recommendation_signature(self, rec: dict[str, Any], idx: int) -> dict[str, Any]:
        meta = ITEMS.get(rec.get("key") or rec.get("item_key"))
        return {
            "rank": idx,
            "key": rec.get("key") or rec.get("item_key"),
            "label": rec.get("label"),
            "lane": rec.get("lane"),
            "category": rec.get("category") or (meta.category if meta else None),
            "target": int(rec.get("target", 0) or 0),
            "current": int(rec.get("current", 0) or 0),
            "next_level": int(rec.get("next_level", 0) or 0),
            "score": float(rec.get("score", 0) or 0),
        }

    async def save_active_recommendations(self, user_id: str, player_tag: str | None, recs: list[dict[str, Any]]) -> None:
        payload = [self._recommendation_signature(rec, idx) for idx, rec in enumerate(recs[:3], start=1)]
        timestamp = datetime.now(timezone.utc).isoformat()

        def patch(root: dict[str, Any], account: dict[str, Any]):
            econ = account.setdefault("advisor_economy", {})
            econ.setdefault("coins", 0)
            econ.setdefault("efficiency_score", 0)
            econ.setdefault("followed_paths", 0)
            econ.setdefault("missed_paths", 0)
            econ["last_recommendations"] = payload
            econ["last_award_at"] = econ.get("last_award_at")
            account["advisor_last_mode"] = account.get("advisor_last_mode")
            account["advisor_path_saved_at"] = timestamp

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)

    def evaluate_path_rewards(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> dict[str, Any]:
        econ = self._get_economy(before_user)
        saved = list(econ.get("last_recommendations") or [])
        if not saved:
            return {"coins": 0, "efficiency": 0, "matches": []}

        before_levels = self.get_effective_levels(before_user)
        after_levels = self.get_effective_levels(after_user)
        matches: list[dict[str, Any]] = []
        total_coins = 0
        total_eff = 0

        base_by_rank = {1: 25, 2: 15, 3: 10}
        bonus_cats = {"hero": 8, "troop": 6, "spell": 6, "siege": 6, "pet": 6, "building": 3, "economy": 2, "defense": 2, "trap": 1}

        for rec in saved[:3]:
            key = rec.get("key")
            if not key or key not in ITEMS:
                continue
            before_status = self.get_item_status(before_user, key, targets=self.get_effective_targets(before_user), levels=before_levels)
            after_status = self.get_item_status(after_user, key, targets=self.get_effective_targets(after_user), levels=after_levels)
            before_cur = int(before_status.get("current", before_levels.get(key, 0)) or 0)
            after_cur = int(after_status.get("current", after_levels.get(key, 0)) or 0)
            before_done = int(before_status.get("done", 0) or 0)
            after_done = int(after_status.get("done", 0) or 0)
            progressed = (after_cur > before_cur) or (after_done > before_done)
            if not progressed:
                continue
            rank = int(rec.get("rank", 99) or 99)
            cat = str(rec.get("category") or ITEMS[key].category)
            coins = base_by_rank.get(rank, 5) + bonus_cats.get(cat, 0)
            eff = max(4, 14 - (rank - 1) * 3) + (3 if cat in {"hero", "troop", "spell", "siege", "pet"} else 1)
            total_coins += coins
            total_eff += eff
            matches.append({
                "rank": rank,
                "key": key,
                "label": rec.get("label") or ITEMS[key].label,
                "coins": coins,
                "efficiency": eff,
                "category": cat,
            })

        return {"coins": total_coins, "efficiency": total_eff, "matches": matches}

    async def apply_path_rewards(self, user_id: str, player_tag: str | None, reward_state: dict[str, Any]) -> dict[str, Any]:
        coins = int(reward_state.get("coins", 0) or 0)
        efficiency = int(reward_state.get("efficiency", 0) or 0)
        matches = list(reward_state.get("matches") or [])
        if coins <= 0 and efficiency <= 0 and not matches:
            return await self.get_user_store(str(user_id), player_tag=player_tag)

        def patch(root: dict[str, Any], account: dict[str, Any]):
            econ = account.setdefault("advisor_economy", {})
            econ["coins"] = int(econ.get("coins", 0) or 0) + coins
            econ["efficiency_score"] = int(econ.get("efficiency_score", 0) or 0) + efficiency
            econ["followed_paths"] = int(econ.get("followed_paths", 0) or 0) + len(matches)
            econ["last_award_at"] = datetime.now(timezone.utc).isoformat()

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)
        return await self.get_user_store(str(user_id), player_tag=player_tag)

    def build_reward_result_block(self, reward_state: dict[str, Any]) -> str:
        matches = list(reward_state.get("matches") or [])
        if not matches:
            return "No active path rewards earned this time."
        lines = [f"🪙 **+{int(reward_state.get('coins', 0))} coins** · 📈 **+{int(reward_state.get('efficiency', 0))} efficiency**"]
        for match in matches[:3]:
            lines.append(f"#{match['rank']} {match['label']} → +{match['coins']} coins / +{match['efficiency']} eff")
        return "\n".join(lines)

    def build_next_reward_block(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]
        percent = int(state["progress"].get("percent", 0))

        progress_lines: list[str] = []
        for mark in MILESTONE_PROGRESS_MARKS:
            if percent < mark:
                remaining = mark - percent
                progress_lines.append(f"📈 **{mark}% progress** → +{mark_reward(mark)} coins (**{remaining}%** more)")
                break

        milestone_lines: list[str] = []
        if not achieved.get("heroes_complete") and groups["heroes"]["total"] > 0:
            remaining = groups["heroes"]["total"] - groups["heroes"]["done"]
            milestone_lines.append(f"🏆 **Heroes Complete** → +75 coins (**{remaining}** left)")
        if not achieved.get("offense_core_complete") and groups["offense"]["total"] > 0:
            remaining = groups["offense"]["total"] - groups["offense"]["done"]
            milestone_lines.append(f"⚔️ **Offense Core Complete** → +100 coins (**{remaining}** left)")
        if not achieved.get("builder_core_complete") and groups["builder"]["total"] > 0:
            remaining = groups["builder"]["total"] - groups["builder"]["done"]
            milestone_lines.append(f"🧱 **Builder Core Complete** → +100 coins (**{remaining}** left)")
        if not achieved.get("war_ready"):
            milestone_lines.append("🔥 **War Ready** → +150 coins (heroes + offense core + **60%** progress)")

        lines = progress_lines + milestone_lines[:2]
        if not lines:
            return "✅ All current advisor rewards are unlocked. Raise your targets to create the next milestone."
        return "\n".join(lines[:3])


    def get_untracked_goals(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user)
        goals: list[dict[str, Any]] = []

        for key in sorted(targets):
            meta = ITEMS.get(key)
            if not meta:
                continue
            target = int(targets.get(key, 0) or 0)
            current = int(levels.get(key, 0) or 0)
            category = str(meta.category or "other")
            copy_cap = self.get_item_copy_cap(user.get("town_hall"), key)
            status = self.get_item_status(user, key, targets=targets, levels=levels)

            if meta.source == "manual":
                if copy_cap > 1:
                    # A plain /trackupgrade on a multi-copy manual item is treated as
                    # all copies being at the same level. /trackcopies remains the
                    # detailed path for mixed-level copies.
                    tracked_copies = copy_cap if key in manual_levels and key not in manual_copy_levels else int(status.get("tracked_copies", 0))
                    if tracked_copies < copy_cap:
                        goals.append({
                            "key": key,
                            "label": meta.label,
                            "category": category,
                            "lane": meta.lane,
                            "target": target,
                            "current": current,
                            "copy_cap": copy_cap,
                            "tracked_copies": tracked_copies,
                            "remaining": copy_cap - tracked_copies,
                            "reason": f"{tracked_copies}/{copy_cap} copies tracked",
                            "kind": "partial_multi_copy",
                        })
                elif key not in manual_levels and key not in manual_copy_levels:
                    goals.append({
                        "key": key,
                        "label": meta.label,
                        "category": category,
                        "lane": meta.lane,
                        "target": target,
                        "current": current,
                        "copy_cap": 1,
                        "tracked_copies": 0,
                        "remaining": 1,
                        "reason": f"Current target {target}",
                        "kind": "missing_manual",
                    })

        def _sort_key(goal: dict[str, Any]):
            priority = 0 if goal.get("lane") == "hero" else (1 if goal.get("lane") == "lab" else 2)
            remaining = int(goal.get("remaining", 0) or 0)
            return (priority, -remaining, str(goal.get("label", "")))

        goals.sort(key=_sort_key)
        return goals

    def build_untracked_goal_summary(self, user: dict[str, Any]) -> str:
        goals = self.get_untracked_goals(user)
        if not goals:
            return "✅ All current advisor goals are tracked."

        category_counts: dict[str, int] = {}
        for goal in goals:
            category_counts[goal["category"]] = category_counts.get(goal["category"], 0) + 1

        parts: list[str] = []
        for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {count}")
        return f"{len(goals)} missing · " + " · ".join(parts)

    def build_untracked_goals_block(self, user: dict[str, Any], limit: int = 8) -> str:
        goals = self.get_untracked_goals(user)
        if not goals:
            return "✅ All current advisor goals are already tracked."

        grouped: dict[str, list[dict[str, Any]]] = {}
        for goal in goals:
            grouped.setdefault(goal["category"], []).append(goal)

        ordered_groups = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        lines: list[str] = [f"Still missing **{len(goals)}** advisor tracking goal(s):"]
        used = 0
        for category, items in ordered_groups:
            if used >= limit:
                continue
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            lines.append(f"{emoji} **{category.replace('_', ' ').title()}** ({len(items)})")
            for goal in items:
                if used >= limit:
                    break
                if goal.get("kind") == "partial_multi_copy":
                    lines.append(
                        f"• {goal['label']} — **{goal['tracked_copies']}/{goal['copy_cap']}** copies tracked (target **{goal['target']}**)"
                    )
                else:
                    lines.append(
                        f"• {goal['label']} — not tracked yet (target **{goal['target']}**)"
                    )
                used += 1
        if len(goals) > used:
            lines.append(f"…and **{len(goals) - used}** more advisor tracking goal(s).")
        return "\n".join(lines)


    def build_untracked_goal_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        goals = self.get_untracked_goals(user)
        grouped: dict[str, list[dict[str, Any]]] = {}
        missing_items = 0
        partial_items = 0
        missing_slots = 0

        for goal in goals:
            category = str(goal.get("category") or "other")
            grouped.setdefault(category, []).append(goal)
            remaining = max(1, int(goal.get("remaining", 1) or 1))
            missing_slots += remaining
            if goal.get("kind") == "partial_multi_copy":
                partial_items += 1
            else:
                missing_items += 1

        ordered_groups = dict(sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])))
        return {
            "items": len(goals),
            "missing_items": missing_items,
            "partial_items": partial_items,
            "missing_slots": missing_slots,
            "groups": ordered_groups,
        }

    def build_untracked_goal_callout(self, user: dict[str, Any]) -> str:
        snapshot = self.build_untracked_goal_snapshot(user)
        total_items = int(snapshot.get("items", 0) or 0)
        if total_items <= 0:
            return "✅ Missing input: none."

        parts: list[str] = [f"Missing input: {total_items} item(s)"]
        missing_slots = int(snapshot.get("missing_slots", 0) or 0)
        if missing_slots > total_items:
            parts.append(f"{missing_slots} tracking slot(s)")
        partial_items = int(snapshot.get("partial_items", 0) or 0)
        if partial_items:
            parts.append(f"{partial_items} partial multi-copy")
        top_groups = list((snapshot.get("groups") or {}).items())[:2]
        for category, items in top_groups:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {len(items)}")
        parts.append("Use /missinggoals")
        return " · ".join(parts)

    def _format_untracked_goal_line(self, goal: dict[str, Any]) -> str:
        if goal.get("kind") == "partial_multi_copy":
            tracked_copies = int(goal.get("tracked_copies", 0) or 0)
            copy_cap = int(goal.get("copy_cap", 1) or 1)
            target = int(goal.get("target", 0) or 0)
            return f"• {goal['label']} — {tracked_copies}/{copy_cap} copies tracked (target {target})"
        target = int(goal.get("target", 0) or 0)
        return f"• {goal['label']} — not tracked yet (target {target})"

    def build_untracked_goals_export_text(self, user: dict[str, Any]) -> str:
        snapshot = self.build_untracked_goal_snapshot(user)
        total_items = int(snapshot.get("items", 0) or 0)
        player_name = user.get("player_name") or "Unknown"
        tag = user.get("player_tag") or ""
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()

        lines: list[str] = [
            f"Missing Goal Input Report",
            f"Account: {player_name} ({tag})",
            f"Town Hall: {th}",
            f"Role: {role}",
            "",
        ]

        if total_items <= 0:
            lines.append("All current advisor goals are already tracked.")
            return "\n".join(lines)

        missing_items = int(snapshot.get("missing_items", 0) or 0)
        partial_items = int(snapshot.get("partial_items", 0) or 0)
        missing_slots = int(snapshot.get("missing_slots", 0) or 0)
        lines.extend([
            f"Missing input items: {total_items}",
            f"Fully missing items: {missing_items}",
            f"Partial multi-copy items: {partial_items}",
            f"Missing tracking slots: {missing_slots}",
            "",
            "Items grouped by category:",
        ])

        for category, items in (snapshot.get("groups") or {}).items():
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            lines.append(f"")
            lines.append(f"{emoji} {category.replace('_', ' ').title()} ({len(items)})")
            for goal in items:
                lines.append(self._format_untracked_goal_line(goal))

        lines.extend([
            "",
            "Tips:",
            "- Use /trackupgrade for single-level manual items and manual overrides.",
            "- Use /trackcopies for multi-copy buildings/traps when copies are not all the same level.",
            "- Auto-synced troop/spell/hero/pet data still counts toward progress when available, but manual-only items must be entered by hand.",
        ])
        return "\n".join(lines)

    def get_remaining_goals(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        goals: list[dict[str, Any]] = []

        for key in sorted(targets):
            meta = ITEMS.get(key)
            if not meta:
                continue
            status = self.get_item_status(user, key, targets=targets, levels=levels)
            tracked = int(status.get("tracked", 0) or 0)
            done = int(status.get("done", 0) or 0)
            remaining = max(tracked - done, 0)
            if remaining <= 0:
                continue

            target = int(targets.get(key, 0) or 0)
            current = int(status.get("current", 0) or 0)
            category = str(meta.category or "other")
            entry = {
                "key": key,
                "label": meta.label,
                "category": category,
                "lane": meta.lane,
                "target": target,
                "current": current,
                "tracked": tracked,
                "done": done,
                "remaining": remaining,
                "multi_copy": bool(status.get("multi_copy")),
                "copy_cap": int(status.get("copy_cap", 1) or 1),
                "tracked_copies": int(status.get("tracked_copies", 0) or 0),
                "fully_confirmed": bool(status.get("fully_confirmed", False)),
                "copy_levels": list(status.get("copy_levels") or []),
            }
            if entry["multi_copy"]:
                entry["highest"] = int(status.get("highest", current) or current)
                entry["lowest"] = current
            goals.append(entry)

        def _sort_key(goal: dict[str, Any]):
            lane_priority = 0 if goal.get("lane") == "hero" else (1 if goal.get("lane") == "lab" else 2)
            remaining = int(goal.get("remaining", 0) or 0)
            gap = max(int(goal.get("target", 0) or 0) - int(goal.get("current", 0) or 0), 0)
            return (lane_priority, -remaining, -gap, str(goal.get("label", "")))

        goals.sort(key=_sort_key)
        return goals

    def build_remaining_goal_summary(self, user: dict[str, Any]) -> str:
        goals = self.get_remaining_goals(user)
        if not goals:
            return "✅ All tracked goals are complete."

        category_counts: dict[str, int] = {}
        for goal in goals:
            category_counts[goal["category"]] = category_counts.get(goal["category"], 0) + int(goal.get("remaining", 1) or 1)

        parts: list[str] = []
        for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {count}")
        return f"{sum(int(goal.get('remaining', 0) or 0) for goal in goals)} remaining · " + " · ".join(parts)

    def build_remaining_goals_block(self, user: dict[str, Any], limit: int = 8) -> str:
        goals = self.get_remaining_goals(user)
        if not goals:
            return "✅ All tracked goals are complete."

        lines: list[str] = [f"Still need to finish **{sum(int(goal.get('remaining', 0) or 0) for goal in goals)}** tracked goal(s):"]
        used = 0
        shown_remaining = 0
        for goal in goals:
            if used >= limit:
                break
            shown_remaining += int(goal.get("remaining", 0) or 0)
            if goal.get("multi_copy"):
                current_best = int(goal.get("highest", goal.get("current", 0)) or 0)
                tracked_copies = int(goal.get("tracked_copies", 0) or 0)
                copy_cap = int(goal.get("copy_cap", 1) or 1)
                if tracked_copies < copy_cap:
                    lines.append(
                        f"• {goal['label']} — **{goal['done']}/{goal['tracked']}** copies at target **{goal['target']}** ({tracked_copies}/{copy_cap} copies tracked)"
                    )
                else:
                    lines.append(
                        f"• {goal['label']} — **{goal['done']}/{goal['tracked']}** copies at target **{goal['target']}** (best tracked level **{current_best}**)"
                    )
            else:
                lines.append(
                    f"• {goal['label']} — level **{goal['current']} → {goal['target']}**"
                )
            used += 1
        total_remaining = sum(int(goal.get('remaining', 0) or 0) for goal in goals)
        hidden_remaining = max(total_remaining - shown_remaining, 0)
        if hidden_remaining > 0:
            lines.append(f"…and **{hidden_remaining}** more tracked goal(s) still to finish.")
        return "\n".join(lines)

    def get_missing_core_items(self, user: dict[str, Any]) -> list[dict[str, str]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        issues: list[dict[str, str]] = []
        seen: set[str] = set()

        def add_issue(issue_key: str, text: str):
            if issue_key in seen:
                return
            seen.add(issue_key)
            issues.append({"key": issue_key, "text": text})

        core_keys = HERO_KEYS | OFFENSE_CORE_KEYS | BUILDER_CORE_KEYS
        for key in sorted(core_keys):
            if key not in ITEMS or key not in targets:
                continue
            meta = ITEMS[key]
            target = int(targets.get(key, 0))
            current = int(levels.get(key, 0))
            if meta.source == "manual":
                if self.is_multi_copy_item(user.get("town_hall"), key):
                    status = self.get_item_status(user, key, targets=targets, levels=levels)
                    if int(status.get("tracked_copies", 0)) < int(status.get("copy_cap", 1)):
                        add_issue(key, f"Track all **{meta.label}** copies manually (**{status.get('tracked_copies', 0)}/{status.get('copy_cap', 1)}** entered) to confirm full progress.")
                        continue
                    if int(status.get("done", 0)) < int(status.get("tracked", 0)):
                        add_issue(key, f"{meta.label} has **{status.get('done', 0)}/{status.get('tracked', 0)}** copies at target **{target}**.")
                        continue
                elif key not in (user.get("manual_levels") or {}):
                    add_issue(key, f"Track **{meta.label}** manually (target **{target}**) to confirm core progress.")
                    continue
            if current < target:
                add_issue(key, f"{meta.label} is **{current}/{target}** (**{target - current}** away).")

        return issues

    def get_rewardable_sync_summary(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> dict[str, Any]:
        before_state = self.get_milestone_state(before_user)
        after_state = self.get_milestone_state(after_user)

        before_achieved = before_state["achieved"]
        after_achieved = after_state["achieved"]

        new_progress_marks = sorted(
            set(after_achieved.get("progress_marks", [])) - set(before_achieved.get("progress_marks", []))
        )

        ordered_group_keys = [
            "heroes_complete",
            "offense_core_complete",
            "builder_core_complete",
            "war_ready",
        ]
        new_group_milestones = [
            key for key in ordered_group_keys
            if after_achieved.get(key) and not before_achieved.get(key)
        ]

        sync_day = None
        synced_at = after_user.get("last_synced_at")
        if synced_at:
            try:
                sync_day = datetime.fromisoformat(synced_at).astimezone(timezone.utc).date().isoformat()
            except Exception:
                sync_day = None

        return {
            "player_tag": after_user.get("player_tag"),
            "player_name": after_user.get("player_name", "Unknown"),
            "new_progress_marks": new_progress_marks,
            "new_group_milestones": new_group_milestones,
            "new_missing_core_fixes": max(0, len(self.get_missing_core_items(before_user)) - len(self.get_missing_core_items(after_user))),
            "should_reward_sync": bool(after_user.get("last_synced_at")),
            "sync_day": sync_day,
        }



    def _resolve_cap_item_key(self, category: str, item_name: str) -> str | None:
        return TH_CAP_LOOKUP_TO_KEY.get((str(category), str(item_name)))

    def build_account_completion_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        town_hall = int(user.get("town_hall") or 0)
        if town_hall <= 0:
            return {
                "town_hall": town_hall,
                "total_slots": 0,
                "supported_slots": 0,
                "supported_complete": 0,
                "supported_known": 0,
                "unsupported_slots": 0,
                "percent_complete": 0,
                "coverage_percent": 0,
                "completion_bar": "░░░░░░░░░░",
                "coverage_bar": "░░░░░░░░░░",
                "group_breakdown": {},
            }

        levels = self.get_effective_levels(user)
        groups: dict[str, dict[str, Any]] = {}
        total_slots = 0
        supported_slots = 0
        supported_complete = 0
        supported_known = 0
        unsupported_slots = 0

        for row in get_all_cap_items(town_hall, categories=list(ACCOUNT_COMPLETION_CATEGORIES)):
            category = str(row.get("category") or "other")
            item_name = str(row.get("item_name") or "Unknown")
            count = max(1, int(row.get("count", 1) or 1))
            max_level = max(0, int(row.get("max_level", 0) or 0))
            total_slots += count
            bucket = groups.setdefault(category, {
                "label": ACCOUNT_COMPLETION_CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
                "total": 0,
                "supported": 0,
                "known": 0,
                "complete": 0,
                "unsupported": 0,
            })
            bucket["total"] += count

            item_key = self._resolve_cap_item_key(category, item_name)
            if not item_key or item_key not in ITEMS:
                unsupported_slots += count
                bucket["unsupported"] += count
                continue

            supported_slots += count
            bucket["supported"] += count
            status = self.get_item_status(user, item_key, levels=levels)
            copy_cap = max(1, int(status.get("copy_cap", 1) or 1))

            if bool(status.get("multi_copy")):
                tracked_copies = min(count, int(status.get("tracked_copies", 0) or 0), copy_cap)
                done_copies = min(count, int(status.get("done", 0) or 0), copy_cap)
                supported_known += tracked_copies
                supported_complete += done_copies
                bucket["known"] += tracked_copies
                bucket["complete"] += done_copies
            else:
                current = int(levels.get(item_key, 0) or 0)
                if current > 0 or item_key in (user.get("manual_levels") or {}) or item_key in (user.get("synced_levels") or {}):
                    supported_known += count
                    bucket["known"] += count
                if max_level > 0 and current >= max_level:
                    supported_complete += count
                    bucket["complete"] += count

        percent_complete = round((supported_complete / supported_slots) * 100) if supported_slots else 0
        coverage_percent = round((supported_known / supported_slots) * 100) if supported_slots else 0
        completion_bar = self.progress_bar(percent_complete)
        coverage_bar = self.progress_bar(coverage_percent)
        return {
            "town_hall": town_hall,
            "total_slots": total_slots,
            "supported_slots": supported_slots,
            "supported_complete": supported_complete,
            "supported_known": supported_known,
            "unsupported_slots": unsupported_slots,
            "unknown_supported": max(supported_slots - supported_known, 0),
            "remaining_supported": max(supported_slots - supported_complete, 0),
            "percent_complete": percent_complete,
            "coverage_percent": coverage_percent,
            "completion_bar": completion_bar,
            "coverage_bar": coverage_bar,
            "group_breakdown": groups,
        }

    def build_account_completion_summary(self, user: dict[str, Any]) -> str:
        snap = self.build_account_completion_snapshot(user)
        if int(snap.get("supported_slots", 0) or 0) <= 0:
            return "No TH account-completion scope is available yet for this account."
        parts = [
            f"{snap['completion_bar']} {snap['percent_complete']}% (**{snap['supported_complete']} / {snap['supported_slots']}** supported slots maxed)",
            f"Coverage: {snap['coverage_bar']} {snap['coverage_percent']}% (**{snap['supported_known']} / {snap['supported_slots']}** supported slots have known data)",
        ]
        unsupported = int(snap.get("unsupported_slots", 0) or 0)
        if unsupported:
            parts.append(f"Outside current model: **{unsupported}** TH slot(s) are not yet part of the bot's full-account data model.")
        return "\n".join(parts)

    def build_recommendation_pool_snapshot(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> dict[str, Any]:
        top, pool = self.build_recommendation_pool(
            user,
            count=5,
            pool_size=12,
            requested_mode=requested_mode,
            builder_idle=builder_idle,
            lab_idle=lab_idle,
        )
        by_lane: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for rec in pool:
            lane = str(rec.get("lane") or "builder")
            category = str(rec.get("category") or "other")
            by_lane[lane] = by_lane.get(lane, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
        ordered_categories = sorted(by_category.items(), key=lambda kv: (RECOMMENDATION_PRIORITIES.get(kv[0], 99), -kv[1], kv[0]))
        ordered_lanes = sorted(by_lane.items(), key=lambda kv: (kv[0] not in {"hero", "lab", "builder"}, kv[0]))
        return {
            "top": top,
            "pool": pool,
            "pool_size": len(pool),
            "top_size": len(top),
            "by_lane": ordered_lanes,
            "by_category": ordered_categories,
        }

    def build_recommendation_pool_summary(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> str:
        snap = self.build_recommendation_pool_snapshot(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        pool = snap.get("pool") or []
        if not pool:
            return "No upgrade is currently below your advisor targets."
        bits = [f"Top picks: **{snap['top_size']}** · Pool considered: **{snap['pool_size']}**"]
        if snap.get("by_lane"):
            lane_bits = [f"{LANE_EMOJIS.get(lane, '📌')} {lane.title()} {count}" for lane, count in snap["by_lane"][:3]]
            bits.append("Lanes: " + " · ".join(lane_bits))
        if snap.get("by_category"):
            cat_bits = [f"{CATEGORY_EMOJIS.get(cat, '📌')} {cat.replace('_', ' ').title()} {count}" for cat, count in snap["by_category"][:3]]
            bits.append("Mix: " + " · ".join(cat_bits))
        return "\n".join(bits)

    def build_three_concepts_summary(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        account = self.build_account_completion_snapshot(user)
        pool = self.build_recommendation_pool_snapshot(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        return (
            f"**Advisor Progress** → **{progress['done']} / {progress['tracked']}** advisor targets done ({progress['percent']}%).\n"
            f"**Account Completion** → **{account['supported_complete']} / {account['supported_slots']}** modeled TH slots maxed ({account['percent_complete']}%).\n"
            f"**Recommendation Pool** → **{pool['pool_size']}** eligible upgrade options currently under target; top **{pool['top_size']}** are surfaced first."
        )

    def format_top_block(self, recs: list[dict[str, Any]]) -> str:
        chunks = []
        for rec in recs:
            chunks.append(
                f"**{rec['priority']}** - {rec['label']} → {rec['next_level']}  \n"
                f"Score: **{rec['score']}** | Current: {rec['current']} | Target: {rec['target']}\n"
                + "\n".join(f"• {reason}" for reason in rec["reasons"])
            )
        return "\n\n".join(chunks)

    def profile_summary(self, user: dict[str, Any]) -> str:
        role = user.get("role", DEFAULT_ROLE).title()
        player_name = user.get("player_name") or "Unknown"
        player_tag = user.get("player_tag") or "No account selected"
        th = user.get("town_hall") or "?"
        synced_at = user.get("last_synced_at")
        sync_text = "Never"
        if synced_at:
            try:
                sync_text = discord.utils.format_dt(datetime.fromisoformat(synced_at), style="R")
            except Exception:
                sync_text = synced_at
        return f"Account: **{player_name}** ({player_tag}) | TH **{th}** | Role: **{role}** | Last sync: {sync_text}"

    
def build_progress_explainer(self, user: dict[str, Any]) -> str:
    progress = self.build_progress_snapshot(user)
    tracking = self.build_tracking_snapshot(user)
    account = self.build_account_completion_snapshot(user)
    return (
        f"**Advisor progress** is your curated upgrade-path score: **{progress['done']} / {progress['tracked']}** targets complete. "
        f"**Account completion** is separate: **{account['supported_complete']} / {account['supported_slots']}** modeled TH slots are maxed. "
        f"**Tracking coverage** is **{tracking['tracked']} / {tracking['total']}**, so the advisor is scoring from confirmed data. "
        f"Multi-copy buildings/traps only count fully once all copies are tracked manually."
    )

    
    def build_data_source_summary(self, user: dict[str, Any]) -> str:
        synced = len(user.get("synced_levels", {}))
        manual = len(user.get("manual_levels", {}))
        account = self.build_account_completion_snapshot(user)
        return (
            f"Auto-synced from Clash API: **{synced}** hero/lab/pet items\n"
            f"Manual entries: **{manual}** (used for buildings, copy tracking, and overrides)\n"
            f"Supported account-completion scope: **{account['supported_slots']}** TH slots modeled right now\n"
            f"Note: many buildings/defenses/traps still depend on manual entry until broader sync is added."
        )

    def build_milestone_status_block(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        groups = state["group_status"]
        achieved = state["achieved"]
        progress = state["progress"]
        return (
            f"Overall advisor completion: **{progress['percent']}%**\n"
            f"Heroes confirmed at target: **{groups['heroes']['done']}/{groups['heroes']['total']}**\n"
            f"Offense core confirmed at target: **{groups['offense']['done']}/{groups['offense']['total']}**\n"
            f"Builder core confirmed at target: **{groups['builder']['done']}/{groups['builder']['total']}**\n"
            f"War-ready checkpoint: **{'Yes' if achieved.get('war_ready') else 'Not yet'}**\n"
            f"*Core milestone counts ignore untracked building/trap copies until you add them manually.*"
        )

    def _html_escape(self, value: Any) -> str:
        return html.escape(str(value if value is not None else ""))

    def _truncate_for_embed(self, value: Any, limit: int = 1000) -> str:
        text = str(value if value is not None else "")
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def _safe_followup_embed_field(self, embed: discord.Embed, *, name: str, value: Any, inline: bool = False, limit: int = 1000) -> None:
        safe_value = self._truncate_for_embed(value or "—", limit=limit)
        embed.add_field(name=name, value=safe_value or "—", inline=inline)

    def _render_card_progress_bar(self, current: int, target: int) -> tuple[int, str]:
        target = max(1, int(target or 1))
        current = max(0, min(int(current or 0), target))
        pct = int(round((current / target) * 100))
        return max(0, min(100, pct)), f"{current}/{target}"

    def _render_metric_row_html(self, label: str, done: int, total: int, icon: str = "📌") -> str:
        pct, ratio = self._render_card_progress_bar(done, total)
        return f'''
        <div class="metric-row">
            <div class="metric-label">{self._html_escape(icon)} {self._html_escape(label)}</div>
            <div class="metric-bar"><div class="metric-fill" style="width: {pct}%"></div></div>
            <div class="metric-value">{self._html_escape(ratio)} · {pct}%</div>
        </div>
        '''

    def _render_summary_card_html(self, label: str, value: str, icon: str = "📌") -> str:
        return (
            '<div class="summary-card">'
            f'<div class="label"><span class="summary-icon">{self._html_escape(icon)}</span>{self._html_escape(label)}</div>'
            f'<div class="value">{self._html_escape(value)}</div>'
            '</div>'
        )

    def _priority_tone(self, rec: dict[str, Any], idx: int = 0) -> str:
        if idx == 1:
            return "top"
        score = float(rec.get("score", 0) or 0)
        priority = str(rec.get("priority", "")).lower()
        if priority == "high" or score >= 14:
            return "high"
        if priority == "medium" or score >= 9:
            return "medium"
        return "low"

    def _tone_meta(self, tone: str) -> tuple[str, str]:
        mapping = {
            "top": ("Top pick", "🔥"),
            "high": ("High value", "🟢"),
            "medium": ("Solid value", "🟡"),
            "low": ("Can wait", "🔴"),
        }
        return mapping.get(tone, ("Recommended", "📌"))

    def _render_upgrade_pick_row_html(self, rec: dict[str, Any], idx: int) -> str:
        meta = ITEMS.get(rec.get("key") or rec.get("item_key"))
        lane_emoji = LANE_EMOJIS.get(rec.get("lane", ""), "📌")
        category_emoji = CATEGORY_EMOJIS.get(getattr(meta, "category", ""), "📌")
        timing_emoji = TIMING_EMOJIS.get(self.classify_recommendation_timing(rec), "📌")
        current = int(rec.get("current", 0) or 0)
        target = int(rec.get("target", 1) or 1)
        pct, ratio = self._render_card_progress_bar(current, target)
        reason = (rec.get("reasons") or ["Good overall value right now."])[0]
        gap = max(0, target - current)
        score = rec.get("score", 0)
        label = rec.get("label", "Upgrade")
        next_level = rec.get("next_level", current + 1)
        tone = self._priority_tone(rec, idx)
        tone_label, tone_emoji = self._tone_meta(tone)
        highlight_class = " top-pick" if idx == 1 else ""
        return f'''        <div class="donation-row upgrade-row tone-{tone}{highlight_class}">
            <div class="donation-rank">#{idx}</div>
            <div class="donation-main">
                <div class="donation-name">{self._html_escape(label)} <span class="pill">{lane_emoji} {category_emoji} {timing_emoji}</span></div>
                <div class="upgrade-sub">Lvl {current} → {next_level} of {target} <span class="tone-badge">{tone_emoji} {self._html_escape(tone_label)}</span></div>
                <div class="donation-bar"><div class="donation-fill tone-{tone}" style="width: {pct}%"></div></div>
                <div class="upgrade-reason">{self._html_escape(reason)}</div>
            </div>
            <div class="donation-stats">
                <div><strong>{ratio}</strong> complete</div>
                <div>Gap <strong>{gap}</strong></div>
                <div>Score <strong>{self._html_escape(score)}</strong></div>
            </div>
        </div>
        '''

    def _render_lane_tiles_html(self, recs: list[dict[str, Any]]) -> str:
        lane_rows: dict[str, list[dict[str, Any]]] = {"hero": [], "lab": [], "builder": []}
        for rec in recs or []:
            lane_rows.setdefault(rec.get("lane", "builder"), []).append(rec)
        cards: list[str] = []
        for lane in ("hero", "lab", "builder"):
            items = lane_rows.get(lane) or []
            best = items[0] if items else None
            label = f"{LANE_EMOJIS.get(lane, '📌')} {lane.title()} Lane"
            value = "Quiet"
            if best:
                value = f"{best['label']} → {best['next_level']}"
            cards.append(self._render_summary_card_html(label, value))
        return ''.join(cards)

    def _base_upgrade_card_html(self, title: str, subtitle: str, summary_html: str, board_html: str) -> str:
        return f'''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin: 0;
    background: #ececec;
    font-family: Arial, Helvetica, sans-serif;
    color: #202020;
}}
.wrap {{
    padding: 28px;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    box-sizing: border-box;
}}
.container {{
    width: 920px;
    padding: 24px 32px 28px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: white;
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}}
.title {{
    font-size: 44px;
    font-weight: 700;
    line-height: 1.05;
    margin-top: 0;
    margin-bottom: 8px;
    text-align: center;
}}
.subtitle {{
    font-size: 22px;
    color: #7f7f7f;
    margin-bottom: 24px;
    text-align: center;
}}
.summary {{
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 28px;
    text-align: center;
}}
.summary-card {{
    background: #f8f8f8;
    border: 1px solid #e8e8e8;
    border-radius: 16px;
    padding: 18px 16px;
}}
.summary-card .label {{
    font-size: 19px;
    color: #7b7b7b;
    margin-bottom: 6px;
    font-weight: 500;
}}
.summary-card .value {{
    font-size: 30px;
    font-weight: 700;
    color: #1f1f1f;
    line-height: 1.15;
}}
.board {{
    width: 100%;
    margin-top: 6px;
    padding-top: 20px;
    border-top: 1px solid #e3e3e3;
}}
.section-title {{
    font-size: 30px;
    font-weight: 700;
    text-align: center;
    margin: 0 0 18px;
}}
.donation-row {{
    display: grid;
    grid-template-columns: 90px 1fr 185px;
    gap: 16px;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid #ececec;
}}
.donation-rank {{
    font-size: 28px;
    font-weight: 700;
    text-align: center;
    color: #202020;
}}
.donation-main {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.donation-name {{
    font-size: 24px;
    font-weight: 700;
    color: #1f1f1f;
}}
.upgrade-sub {{
    font-size: 18px;
    color: #505050;
}}
.upgrade-reason {{
    font-size: 17px;
    color: #686868;
    line-height: 1.35;
}}
.donation-bar {{
    width: 100%;
    height: 14px;
    background: #dfdfe4;
    border-radius: 999px;
    overflow: hidden;
}}
.donation-fill {{
    height: 100%;
    background: #6fbf73;
    border-radius: 999px;
}}
.donation-stats {{
    text-align: right;
    font-size: 18px;
    color: #404040;
    line-height: 1.5;
}}
.pill {{
    display: inline-block;
    margin-left: 10px;
    padding: 6px 10px;
    border-radius: 999px;
    background: #f1f1f1;
    color: #515151;
    font-size: 15px;
    font-weight: 600;
    vertical-align: middle;
}}
.empty {{
    font-size: 22px;
    color: #777;
    text-align: center;
    padding: 40px 0;
}}
.note {{
    width: 100%;
    padding-top: 18px;
    text-align: center;
    font-size: 18px;
    color: #707070;
}}
.metric-row {{
    display: grid;
    grid-template-columns: 220px 1fr 140px;
    gap: 14px;
    align-items: center;
    margin: 10px 0;
}}
.metric-label {{
    font-size: 20px;
    font-weight: 700;
    color: #2a2a2a;
}}
.metric-bar {{
    width: 100%;
    height: 14px;
    background: #dfdfe4;
    border-radius: 999px;
    overflow: hidden;
}}
.metric-fill {{
    height: 100%;
    background: #4f8df7;
    border-radius: 999px;
}}
.metric-value {{
    text-align: right;
    font-size: 18px;
    color: #404040;
    font-weight: 700;
}}
</style>
</head>
<body>
<div class="wrap">
<div class="container">
    <div class="title">{self._html_escape(title)}</div>
    <div class="subtitle">{self._html_escape(subtitle)}</div>
    <div class="summary">{summary_html}</div>
    <div class="board">{board_html}</div>
</div>
</div>
</body>
</html>
        '''



    def _base_compact_card_html(self, title: str, subtitle: str, body_html: str) -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin: 0;
    background: #eef1f6;
    font-family: Arial, Helvetica, sans-serif;
    color: #1f2937;
}}
.card-shell {{
    width: 920px;
    height: 980px;
    box-sizing: border-box;
    padding: 24px;
}}
.card {{
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border-radius: 18px;
    border: 1px solid #dfe5ee;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    padding: 28px;
}}
.header {{
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 14px;
    margin-bottom: 18px;
}}
.title {{
    font-size: 34px;
    font-weight: 700;
    line-height: 1.1;
    margin: 0 0 6px;
}}
.subtitle {{
    font-size: 18px;
    color: #6b7280;
    margin: 0;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}}
.stat {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px;
}}
.stat .label {{
    font-size: 13px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 6px;
}}
.stat .value {{
    font-size: 26px;
    font-weight: 700;
    color: #111827;
    line-height: 1.15;
}}
.section {{
    margin-top: 16px;
}}
.section-title {{
    font-size: 20px;
    font-weight: 700;
    margin: 0 0 10px;
    color: #111827;
}}
.progress-row {{
    margin: 10px 0 12px;
}}
.progress-meta {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    font-size: 16px;
    margin-bottom: 6px;
}}
.progress-label {{
    font-weight: 700;
    color: #374151;
}}
.progress-value {{
    color: #4b5563;
    font-weight: 700;
}}
.bar {{
    width: 100%;
    height: 14px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
}}
.fill {{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #4f8df7, #60a5fa);
}}
.pick {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
}}
.pick-title {{
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #111827;
}}
.pick-sub {{
    font-size: 15px;
    color: #4b5563;
    line-height: 1.4;
}}
.muted {{
    color: #6b7280;
    font-size: 15px;
    line-height: 1.45;
}}
</style>
</head>
<body>
<div class="card-shell">
  <div class="card">
    <div class="header">
      <div class="title">{self._html_escape(title)}</div>
      <div class="subtitle">{self._html_escape(subtitle)}</div>
    </div>
    {body_html}
  </div>
</div>
</body>
</html>
        """


    def _pick_spotlight_recommendations(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any] | None]:
        ranked = list(recs or [])
        extended = list(pool or [])
        combined: list[dict[str, Any]] = []
        seen: set[str] = set()
        for rec in ranked + extended:
            key = str(rec.get("key") or rec.get("item_key") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            combined.append(rec)

        best = combined[0] if combined else None

        quick = None
        progress = None

        def gap_of(rec: dict[str, Any]) -> int:
            return max(0, int(rec.get("target", 0) or 0) - int(rec.get("current", 0) or 0))

        if combined:
            quick_pool = [rec for rec in combined if gap_of(rec) > 0]
            if quick_pool:
                quick = min(
                    quick_pool,
                    key=lambda rec: (
                        gap_of(rec),
                        0 if rec.get("lane") == "hero" else 1,
                        -float(rec.get("score", 0) or 0),
                    ),
                )

            progress_pool = [rec for rec in combined if gap_of(rec) >= 2]
            if not progress_pool:
                progress_pool = quick_pool
            if progress_pool:
                progress = max(
                    progress_pool,
                    key=lambda rec: (
                        float(rec.get("score", 0) or 0),
                        gap_of(rec),
                        1 if rec.get("lane") == "hero" else 0,
                    ),
                )

        return {"best": best, "quick": quick, "progress": progress}

    def _format_spotlight_line(self, rec: dict[str, Any] | None, label: str, icon: str) -> str:
        if not rec:
            return f"{icon} **{label}:** No upgrade queued."
        reason = (rec.get("reasons") or ["Solid value right now."])[0]
        if len(reason) > 80:
            reason = reason[:77].rstrip() + "..."
        gap = max(0, int(rec.get("target", 0) or 0) - int(rec.get("current", 0) or 0))
        return (
            f"{icon} **{label}:** {rec.get('label', 'Upgrade')} → **{rec.get('next_level', '?')}**\n"
            f"`{self.build_mini_progress_bar(int(rec.get('current', 0) or 0), int(rec.get('target', 1) or 1))}` "
            f"Gap **{gap}** · Score **{rec.get('score', 0)}**\n"
            f"{reason}"
        )

    def build_nextupgrade_spotlight_block(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> str:
        picks = self._pick_spotlight_recommendations(recs, pool)
        lines = [
            self._format_spotlight_line(picks.get("best"), "Best Upgrade", "🔥"),
            self._format_spotlight_line(picks.get("quick"), "Quick Win", "⚡"),
            self._format_spotlight_line(picks.get("progress"), "Big Progress", "📈"),
        ]
        return "\n\n".join(lines)

    def _render_spotlight_tiles_html(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> str:
        picks = self._pick_spotlight_recommendations(recs, pool)
        order = [
            ("best", "🔥 Best Upgrade"),
            ("quick", "⚡ Quick Win"),
            ("progress", "📈 Big Progress"),
        ]
        tiles: list[str] = []
        for key, title in order:
            rec = picks.get(key)
            if rec:
                reason = (rec.get("reasons") or ["Solid value right now."])[0]
                if len(reason) > 90:
                    reason = reason[:87].rstrip() + "..."
                line_1 = f"{self._html_escape(str(rec.get('label', 'Upgrade')))} → {self._html_escape(str(rec.get('next_level', '?')))}"
                line_2 = f"Lvl {int(rec.get('current', 0) or 0)} / {int(rec.get('target', 1) or 1)}"
                line_3 = f"Gap {max(0, int(rec.get('target', 0) or 0) - int(rec.get('current', 0) or 0))} · Score {self._html_escape(str(rec.get('score', 0)))}"
                detail = self._html_escape(reason)
            else:
                line_1 = "No upgrade queued"
                line_2 = "—"
                line_3 = "—"
                detail = "Nothing urgent in this slot right now."
            tiles.append(
                f'<div class="summary-card"><div class="label">{self._html_escape(title)}</div>'
                f'<div class="value" style="font-size:26px;">{line_1}</div>'
                f'<div class="sub">{line_2} · {line_3}</div>'
                f'<div class="sub" style="margin-top:8px; line-height:1.45;">{detail}</div></div>'
            )
        return ''.join(tiles)

    def build_nextupgrade_card_html(self, user: dict[str, Any], recs: list[dict[str, Any]], pool: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        tracking = self.build_tracking_snapshot(user)
        role = str(user.get("role", DEFAULT_ROLE)).title()
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        state = self.get_milestone_state(user)
        war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"
        lane_snapshot = self.build_lane_snapshot(user)
        pressure_lane = min((lane, float(data.get("percent", 100.0))) for lane, data in lane_snapshot.items()) if lane_snapshot else ("none", 100.0)
        top_lane = pressure_lane[0].title() if recs else "None"
        next_reward = self.build_next_reward_block(user).split("\n")[0].replace("**", "")
        timing_context = timing_context or self.get_timing_context(user)
        mode = str(timing_context.get("mode", "war"))
        emoji = MODE_EMOJIS.get(mode, "🧠")
        mode_label = f"{emoji} {mode.title()}"
        builder_label = "Idle" if timing_context.get("builder_idle") else "Busy/Unknown"
        lab_label = "Idle" if timing_context.get("lab_idle") else "Busy/Unknown"
        war_state = dict(timing_context.get("war_state") or {})
        resource_pressure = dict(timing_context.get("resource_pressure") or {})
        war_state_label = "CWL" if war_state.get("cwl") else ("In War" if war_state.get("in_war") else ("Prep" if war_state.get("war_prepping") else "None"))
        hottest_resource = max(resource_pressure.items(), key=lambda kv: kv[1])[0] if resource_pressure else "none"
        hottest_value = int(round(float(resource_pressure.get(hottest_resource, 0.0)) * 100)) if resource_pressure else 0
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role / War Ready", f"{role} · {war_ready}", "⚔️"),
            self._render_summary_card_html("Tracked Progress", f"{progress['percent']}% ({progress['done']}/{progress['tracked']})", "📈"),
            self._render_summary_card_html("Top Pressure Lane", f"{top_lane} ({int(pressure_lane[1])}% done)", LANE_EMOJIS.get(pressure_lane[0], "📌")),
            self._render_summary_card_html("Mode / Builders", f"{mode_label} · {builder_label}", "🛠️"),
            self._render_summary_card_html("War / Resource", f"{war_state_label} · {hottest_resource.replace('_', ' ').title()} {hottest_value}%", "🪖"),
            self._render_summary_card_html("Lab / Next Reward", f"{lab_label} · {next_reward}", "🧪"),
            self._render_summary_card_html("Tracking Coverage", f"{tracking['tracked']}/{tracking['total']}", "🧭"),
            self._render_summary_card_html("Coins / Efficiency", f"{int(self._get_economy(user).get('coins', 0))} · {int(self._get_economy(user).get('efficiency_score', 0))}", "🪙"),
            self._render_summary_card_html("Remaining Goals", self.build_remaining_goal_summary(user), "🎯"),
            self._render_summary_card_html("Advisor Tracking", self.build_untracked_goal_summary(user), "🧭"),
        ])
        if recs:
            rows_html = ''.join(self._render_upgrade_pick_row_html(rec, idx) for idx, rec in enumerate(recs[:5], start=1))
        else:
            rows_html = '<div class="empty">Nothing urgent right now.</div>'
        board_html = (
            '<div class="section-title">Upgrade Spotlights</div>'
            + self._render_spotlight_tiles_html(recs, pool)
            + '<div class="section-title" style="margin-top:28px;">Top Upgrade Picks</div>'
            + rows_html
            + '<div class="section-title" style="margin-top:28px;">Lane Breakdown</div>'
            + self._render_lane_tiles_html(recs)
            + '<div class="section-title" style="margin-top:28px;">Remaining Goals</div>'
            + f'<div class="note" style="text-align:left; line-height:1.5;">{self._html_escape(self.build_remaining_goals_block(user, limit=5).replace("**", ""))}</div>'
            + '<div class="section-title" style="margin-top:20px;">Advisor Tracking Gaps</div>'
            + f'<div class="note" style="text-align:left; line-height:1.5;">{self._html_escape(self.build_untracked_goals_block(user, limit=3).replace("**", ""))}</div>'
            + f'<div class="note">Focus: {self._html_escape(self.build_milestone_hint(user).replace("**", ""))}</div>'
        )
        subtitle = f"Advisor recommendations for {player_name}"
        return self._base_upgrade_card_html("Upgrade Advisor", subtitle, summary_html, board_html)

    def build_upgradeprogress_card_html(self, user: dict[str, Any], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role", role, "⚔️"),
            self._render_summary_card_html("Overall Progress", f"{progress['percent']}%", "📈"),
            self._render_summary_card_html("Goals Complete", f"{progress['done']}/{progress['tracked']}", "🎯"),
            self._render_summary_card_html("War Ready", "Yes" if achieved.get("war_ready") else "Not yet", "✅"),
            self._render_summary_card_html("Last Sync", str(user.get("last_synced_at") or "Never")[:16].replace("T", " "), "🕒"),
            self._render_summary_card_html("Coins / Efficiency", f"{int(self._get_economy(user).get('coins', 0))} · {int(self._get_economy(user).get('efficiency_score', 0))}", "🪙"),
        ])
        breakdown_html = ''.join([
            self._render_metric_row_html("Overall", int(progress["done"]), int(progress["tracked"]), "📊"),
            self._render_metric_row_html("Heroes", int(groups["heroes"]["done"]), int(groups["heroes"]["total"]), "👑"),
            self._render_metric_row_html("Offense", int(groups["offense"]["done"]), int(groups["offense"]["total"]), "⚔️"),
            self._render_metric_row_html("Core Buildings", int(groups["builder"]["done"]), int(groups["builder"]["total"]), "🛠️"),
        ])
        reward_track = self.build_next_reward_block(user).replace("**", "")
        lane_recs = self.build_recommendations(
            user,
            count=3,
            requested_mode=(timing_context or {}).get("mode"),
            builder_idle=(timing_context or {}).get("builder_idle"),
            lab_idle=(timing_context or {}).get("lab_idle"),
        )
        board_html = (
            '<div class="section-title">Progress Breakdown</div>'
            + breakdown_html
            + '<div class="section-title" style="margin-top:28px;">Next Focus</div>'
            + f'<div class="note" style="text-align:left; line-height:1.5;">{self._html_escape(self.build_milestone_hint(user).replace("**", ""))}</div>'
            + '<div class="section-title" style="margin-top:28px;">Lane Snapshot</div>'
            + self._render_lane_tiles_html(lane_recs)
            + '<div class="section-title" style="margin-top:28px;">Remaining Goals</div>'
            + f'<div class="note" style="text-align:left; line-height:1.5;">{self._html_escape(self.build_remaining_goals_block(user, limit=5).replace("**", ""))}</div>'
            + '<div class="section-title" style="margin-top:20px;">Advisor Tracking Gaps</div>'
            + f'<div class="note" style="text-align:left; line-height:1.5;">{self._html_escape(self.build_untracked_goals_block(user, limit=3).replace("**", ""))}</div>'
            + f'<div class="note">Reward track: {self._html_escape(reward_track)}</div>'
        )
        subtitle = f"Progress snapshot for {player_name}"
        return self._base_upgrade_card_html("Upgrade Progress", subtitle, summary_html, board_html)

    def _safe_rec_int(self, rec: dict[str, Any] | None, key: str, default: int = 0) -> int:
        if not isinstance(rec, dict):
            return default
        try:
            value = rec.get(key, default)
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_rec_label(self, rec: dict[str, Any] | None) -> str:
        if not isinstance(rec, dict):
            return "Upgrade"
        label = rec.get("label") or rec.get("key") or "Upgrade"
        return str(label)

    def _build_compact_progress_card_html(self, user: dict[str, Any], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        tracking = self.build_tracking_snapshot(user)
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()
        state = self.get_milestone_state(user)
        war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"
        velocity = self.get_progress_velocity(user)
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role", role, "⚔️"),
            self._render_summary_card_html("Progress", f"{progress['percent']}%", "📈"),
            self._render_summary_card_html("Goals", f"{progress['done']}/{progress['tracked']}", "🎯"),
            self._render_summary_card_html("Tracking", f"{tracking['tracked']}/{tracking['total']}", "🧭"),
            self._render_summary_card_html("TH Age", self.get_town_hall_age_text(user), "⏱️"),
            self._render_summary_card_html("War Ready", war_ready, "✅"),
            self._render_summary_card_html("Efficiency", str(velocity.get("rating", "Unrated")), "⭐"),
        ])
        board_html = (
            '<div class="section-title">Progress Breakdown</div>'
            + ''.join([
                self._render_metric_row_html("Overall", int(progress["done"]), int(progress["tracked"]), "📊"),
                self._render_metric_row_html("Heroes", int(state["group_status"]["heroes"]["done"]), int(state["group_status"]["heroes"]["total"]), "👑"),
                self._render_metric_row_html("Offense", int(state["group_status"]["offense"]["done"]), int(state["group_status"]["offense"]["total"]), "⚔️"),
                self._render_metric_row_html("Core Buildings", int(state["group_status"]["builder"]["done"]), int(state["group_status"]["builder"]["total"]), "🛠️"),
            ])
            + '<div class="section-title" style="margin-top:18px;">Top Focus</div>'
            + f'<div class="note" style="text-align:left; line-height:1.45;">{self._html_escape(self.build_milestone_hint(user).replace("**", ""))}</div>'
            + f'<div class="note" style="margin-top:10px; text-align:left; line-height:1.45;">{self._html_escape(self.build_untracked_goal_callout(user))}</div>'
        )
        subtitle = f"Progress snapshot for {player_name}"
        return self._base_upgrade_card_html("Upgrade Progress", subtitle, summary_html, board_html)

    def _build_compact_nextupgrade_card_html(self, user: dict[str, Any], recs: list[dict[str, Any]], pool: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()
        state = self.get_milestone_state(user)
        war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"
        velocity = self.get_progress_velocity(user)
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role", role, "⚔️"),
            self._render_summary_card_html("War Ready", war_ready, "✅"),
            self._render_summary_card_html("Progress", f"{progress['percent']}% ({progress['done']}/{progress['tracked']})", "📈"),
            self._render_summary_card_html("TH Age", self.get_town_hall_age_text(user), "⏱️"),
            self._render_summary_card_html("Efficiency", str(velocity.get("rating", "Unrated")), "⭐"),
        ])
        rows_html = ''.join(self._render_upgrade_pick_row_html(rec, idx) for idx, rec in enumerate((recs or [])[:3], start=1)) if recs else '<div class="empty">Nothing urgent right now.</div>'
        board_html = (
            '<div class="section-title">Upgrade Spotlights</div>'
            + self._render_spotlight_tiles_html(recs[:3], pool[:6] if pool else [])
            + '<div class="section-title" style="margin-top:18px;">Top Picks</div>'
            + rows_html
        )
        subtitle = f"Advisor recommendations for {player_name}"
        return self._base_upgrade_card_html("Upgrade Advisor", subtitle, summary_html, board_html)

    def _build_safe_nextupgrade_embed(self, user: dict[str, Any], recs: list[dict[str, Any]], pool: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> discord.Embed:
        progress = self.build_progress_snapshot(user)
        tracking = self.build_tracking_snapshot(user)
        timing_context = timing_context or self.get_timing_context(user)
        embed = discord.Embed(
            title=f"{BRAIN} Upgrade Advisor",
            color=0x5865F2,
            description=self.profile_summary(user),
        )
        self._safe_followup_embed_field(
            embed,
            name="Account Snapshot",
            value=self.build_quick_status_block(user, recs, timing_context=timing_context),
            inline=False,
            limit=900,
        )
        self._safe_followup_embed_field(
            embed,
            name="Upgrade Spotlights",
            value=self.build_nextupgrade_spotlight_block(recs[:3], pool[:6] if pool else []),
            inline=False,
            limit=900,
        )
        picks = []
        for idx, rec in enumerate((recs or [])[:3], start=1):
            label = self._safe_rec_label(rec)
            current = self._safe_rec_int(rec, "current", 0)
            next_level = self._safe_rec_int(rec, "next_level", current + 1)
            target = self._safe_rec_int(rec, "target", next_level)
            gap = max(0, target - current)
            reason_list = rec.get("reasons") if isinstance(rec, dict) else None
            reason = (reason_list or ["Good overall value right now."])[0]
            picks.append(f"#{idx} **{label}**\nLvl **{current} → {next_level}** of **{target}** · Gap **{gap}**\n{self._truncate_for_embed(reason, limit=140)}")
        self._safe_followup_embed_field(embed, name="Top Upgrade Picks", value="\n\n".join(picks) or "Nothing urgent right now.", inline=False, limit=950)
        self._safe_followup_embed_field(embed, name="Lane Breakdown", value=self.build_lane_summary(recs[:3]), inline=True, limit=400)
        self._safe_followup_embed_field(embed, name="Progress / Tracking", value=f"{progress['percent']}% complete\n{progress['done']} / {progress['tracked']} tracked goals complete\n{tracking['tracked']} / {tracking['total']} tracking slots confirmed", inline=True, limit=400)
        self._safe_followup_embed_field(embed, name="Missing Input", value=self.build_untracked_goal_callout(user), inline=False, limit=500)
        self._safe_followup_embed_field(embed, name="Speed / ETA", value=self.build_velocity_summary(user), inline=False, limit=500)
        embed.set_footer(text="Compact advisor view shown.")
        return embed

    async def render_html_card_to_file(self, html_content: str, filename: str, width: int = 920, height: int = 980, wait_ms: int = 900) -> discord.File:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        tmp.close()
        browser = None
        context = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                )
                page = await context.new_page()
                await page.emulate_media(media="screen")
                await page.set_content(html_content, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(wait_ms)

                clip_selector = await page.evaluate("""
                    () => {
                        const selectors = ['.container', '.card', '.wrap', '.card-shell', 'body'];
                        for (const selector of selectors) {
                            if (document.querySelector(selector)) return selector;
                        }
                        return 'body';
                    }
                """)
                clip = page.locator(clip_selector).first
                box = await clip.bounding_box()
                if box:
                    viewport_width = max(width, min(int(box["width"] + 48), 1400))
                    viewport_height = max(height, min(int(box["height"] + 48), 4000))
                    await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                    await page.wait_for_timeout(120)
                    clip = page.locator(clip_selector).first

                await clip.screenshot(path=tmp.name)

            with open(tmp.name, 'rb') as f:
                data = io.BytesIO(f.read())
            data.seek(0)
            return discord.File(fp=data, filename=filename)
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass
            try:
                os.remove(tmp.name)
            except OSError:
                pass

    def register(self):
        advisor = self

        async def account_autocomplete(interaction: discord.Interaction, current: str):
            current = (current or "").lower()
            linked_accounts = await advisor.get_linked_accounts(str(interaction.user.id))
            choices: list[app_commands.Choice[str]] = []
            for account in linked_accounts:
                label = f"{account['name']} ({account['tag']})"
                if current and current not in label.lower() and current not in account['tag'].lower():
                    continue
                choices.append(app_commands.Choice(name=label[:100], value=account['tag']))
            return choices[:25]

        @self.tree.command(name="setrole", description="Set your upgrade advisor profile")
        @app_commands.describe(role="Choose how the advisor should prioritize your upgrades")
        @app_commands.choices(
            role=[
                app_commands.Choice(name="Attacker", value="attacker"),
                app_commands.Choice(name="Hybrid", value="hybrid"),
                app_commands.Choice(name="Farmer", value="farmer"),
            ]
        )
        async def setrole(interaction: discord.Interaction, role: app_commands.Choice[str]):
            await advisor.save_user_patch(
                str(interaction.user.id),
                lambda root, account: root.update({"role": role.value}),
            )
            root = await advisor.get_user_root(str(interaction.user.id))
            active_tag = root.get("active_player_tag")
            if active_tag:
                targets = advisor.infer_default_targets(advisor.get_account_from_root(root, active_tag).get("town_hall"), role.value)
                if targets:
                    await advisor.save_user_patch(
                        str(interaction.user.id),
                        lambda root, account: account.setdefault("targets", {}).update({k: account.setdefault("targets", {}).get(k, v) for k, v in targets.items()}),
                        player_tag=active_tag,
                    )
            await interaction.response.send_message(
                f"✅ Upgrade advisor role set to **{role.name}**.",
                ephemeral=True,
            )

        @self.tree.command(name="syncupgrades", description="Sync heroes, troops, spells, and pets from one linked Clash account")
        @app_commands.describe(account="Which linked Clash account to sync")
        async def syncupgrades(interaction: discord.Interaction, account: str | None = None):
            await interaction.response.defer(ephemeral=True)

            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            if not chosen_link:
                await interaction.followup.send("❌ You need to link a Clash account first with /link.", ephemeral=True)
                return

            before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_link["tag"])

            try:
                user = await advisor.sync_player(str(interaction.user.id), account_hint=account)
            except ValueError as exc:
                await interaction.followup.send(f"❌ {exc}", ephemeral=True)
                return

            synced_count = len(user.get("synced_levels", {}))
            progress = advisor.build_progress_snapshot(user)
            milestone_celebration = advisor.build_milestone_celebration(before_user, user)
            reward_state = advisor.evaluate_path_rewards(before_user, user)
            if reward_state.get("coins") or reward_state.get("efficiency"):
                user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_link["tag"], reward_state)

            embed = discord.Embed(title=f"{CHECK} Upgrade Sync Complete", color=0x2ECC71)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="What got refreshed", value=advisor.build_data_source_summary(user), inline=False)
            tracking = advisor.build_tracking_snapshot(user)
            embed.add_field(name="Advisor progress", value=f"{progress['bar']} {progress['percent']}% (**{progress['done']} / {progress['tracked']}** goals complete)", inline=False)
            embed.add_field(name="Tracking coverage", value=f"{tracking['bar']} {tracking['percent']}% (**{tracking['tracked']} / {tracking['total']}** slots tracked)", inline=False)
            embed.add_field(name="Account completion", value=advisor.build_account_completion_summary(user), inline=False)
            embed.add_field(name="Recommendation pool", value=advisor.build_recommendation_pool_summary(user), inline=False)
            embed.add_field(name="What this means", value=advisor.build_progress_explainer(user), inline=False)
            embed.add_field(name="New this sync", value=milestone_celebration, inline=False)
            embed.add_field(name="Path rewards", value=advisor.build_reward_result_block(reward_state), inline=False)
            embed.add_field(name="Economy", value=advisor.build_economy_summary(user), inline=False)
            embed.add_field(name="Speed / ETA", value=advisor.build_velocity_summary(user), inline=False)
            embed.set_footer(text=f"Viewing account: {user.get('player_name', 'Unknown')} {user.get('player_tag', '')}")

            await interaction.followup.send(embed=embed, ephemeral=True)



        @self.tree.command(name="accountcompletion", description="View full-account completion vs advisor progress")
        @app_commands.describe(account="Which linked account to view")
        async def accountcompletion(interaction: discord.Interaction, account: str | None = None):
            await interaction.response.defer(ephemeral=True)
            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            if not chosen_link:
                await interaction.followup.send("❌ You need to link a Clash account first with /link.", ephemeral=True)
                return
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_link["tag"])
            if not user.get("player_tag"):
                await interaction.followup.send("❌ No tracked upgrade profile found for that account yet. Run `/syncupgrades` first.", ephemeral=True)
                return

            progress = advisor.build_progress_snapshot(user)
            tracking = advisor.build_tracking_snapshot(user)

            embed = discord.Embed(title=f"{CHART} Account Completion", color=0x3498DB)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="Three concepts", value=advisor.build_three_concepts_summary(user), inline=False)
            embed.add_field(name="Advisor progress", value=f"{progress['bar']} {progress['percent']}% (**{progress['done']} / {progress['tracked']}** targets complete)", inline=False)
            embed.add_field(name="Tracking coverage", value=f"{tracking['bar']} {tracking['percent']}% (**{tracking['tracked']} / {tracking['total']}** advisor slots confirmed)", inline=False)
            embed.add_field(name="Account completion", value=advisor.build_account_completion_summary(user), inline=False)
            embed.add_field(name="Recommendation pool", value=advisor.build_recommendation_pool_summary(user), inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)

        @accountcompletion.autocomplete("account")
        async def accountcompletion_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @syncupgrades.autocomplete("account")
        async def syncupgrades_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @self.tree.command(name="trackupgrade", description="Track a manual item level or override a target")
        @app_commands.describe(item="Item key to track", current_level="Your current level", target_level="Optional advisor target override", account="Which linked account this should apply to", copy_count="Optional number of copies at this exact level")
        async def trackupgrade(interaction: discord.Interaction, item: str, current_level: int, target_level: int | None = None, account: str | None = None, copy_count: int | None = None):
            item = item.strip().lower()
            if item not in ITEMS:
                await interaction.response.send_message("❌ Unknown item key. Use autocomplete or a valid advisor item.", ephemeral=True)
                return
            if current_level < 0:
                await interaction.response.send_message("❌ Current level cannot be negative.", ephemeral=True)
                return
            if copy_count is not None and copy_count < 1:
                await interaction.response.send_message("❌ Copy count must be at least 1.", ephemeral=True)
                return
            if target_level is not None and target_level < current_level:
                await interaction.response.send_message("❌ Target level cannot be lower than your current level.", ephemeral=True)
                return

            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account
            before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)

            def patch(root: dict[str, Any], account_store: dict[str, Any]):
                if chosen_tag:
                    root["active_player_tag"] = chosen_tag
                    account_store.setdefault("player_tag", chosen_tag)
                    if chosen_link:
                        account_store.setdefault("player_name", chosen_link.get("name", "Unknown"))
                if copy_count and advisor.is_multi_copy_item(account_store.get("town_hall"), item):
                    cap_count = advisor.get_item_copy_cap(account_store.get("town_hall"), item)
                    applied = max(1, min(int(copy_count), cap_count))
                    account_store.setdefault("manual_copy_levels", {})[item] = [int(current_level)] * applied
                    account_store.setdefault("manual_levels", {}).pop(item, None)
                else:
                    account_store.setdefault("manual_levels", {})[item] = int(current_level)
                if target_level is not None:
                    th_for_target = account_store.get("town_hall")
                    cap_target = advisor.get_th_cap_target(th_for_target, item)
                    sanitized_target = int(target_level)
                    if cap_target is not None:
                        sanitized_target = max(int(current_level), min(sanitized_target, cap_target))
                    account_store.setdefault("targets", {})[item] = sanitized_target

            await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            reward_state = advisor.evaluate_path_rewards(before_user, user)
            if reward_state.get("coins") or reward_state.get("efficiency"):
                user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_tag, reward_state)
            effective_target = advisor.get_effective_targets(user).get(item, target_level or current_level)
            if copy_count and advisor.is_multi_copy_item(user.get("town_hall"), item):
                copy_cap = advisor.get_item_copy_cap(user.get("town_hall"), item)
                await interaction.response.send_message(
                    f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{min(copy_count, copy_cap)}/{copy_cap}** copies entered at level **{current_level}** and target **{effective_target}**. Use `/trackcopies` for mixed levels.\n{advisor.build_reward_result_block(reward_state)}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** at level **{current_level}** with target **{effective_target}**.\n{advisor.build_reward_result_block(reward_state)}",
                    ephemeral=True,
                )

        @trackupgrade.autocomplete("item")
        async def trackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
            current = current.lower()
            return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

        @trackupgrade.autocomplete("account")
        async def trackupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @self.tree.command(name="untrackupgrade", description="Remove a manually tracked item or target override")
        @app_commands.describe(item="Item key to remove", account="Which linked account this should apply to")
        async def untrackupgrade(interaction: discord.Interaction, item: str, account: str | None = None):
            item = item.strip().lower()
            if item not in ITEMS:
                await interaction.response.send_message("❌ Unknown item key.", ephemeral=True)
                return

            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account

            def patch(root: dict[str, Any], account_store: dict[str, Any]):
                if chosen_tag:
                    root["active_player_tag"] = chosen_tag
                account_store.setdefault("manual_levels", {}).pop(item, None)
                account_store.setdefault("manual_copy_levels", {}).pop(item, None)
                account_store.setdefault("targets", {}).pop(item, None)

            await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            await interaction.response.send_message(
                f"✅ Removed manual tracking for **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}**.",
                ephemeral=True,
            )

        @self.tree.command(name="trackcopies", description="Track mixed copy levels for a building or trap with multiple copies")
        @app_commands.describe(item="Multi-copy item key to track", levels_csv="Comma-separated copy levels like 13,13,12,12", target_level="Optional advisor target override", account="Which linked account this should apply to")
        async def trackcopies(interaction: discord.Interaction, item: str, levels_csv: str, target_level: int | None = None, account: str | None = None):
            item = item.strip().lower()
            if item not in ITEMS:
                await interaction.response.send_message("❌ Unknown item key. Use autocomplete or a valid advisor item.", ephemeral=True)
                return

            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account
            before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            existing_user = before_user
            town_hall = existing_user.get("town_hall")
            if town_hall is None:
                await interaction.response.send_message(
                    "❌ I do not know this account's Town Hall yet. Run `/syncupgrades` for that account first, then try `/trackcopies` again.",
                    ephemeral=True,
                )
                return
            if not advisor.is_multi_copy_item(town_hall, item):
                label = ITEMS[item].label if item in ITEMS else item
                await interaction.response.send_message(
                    f"❌ **{label}** is not configured as a multi-copy item for TH{town_hall}. Use `/trackupgrade` instead.",
                    ephemeral=True,
                )
                return

            parts = [p.strip() for p in (levels_csv or "").split(",") if p.strip()]
            if not parts:
                await interaction.response.send_message("❌ Enter at least one copy level, like `13,13,12,12`.", ephemeral=True)
                return
            parsed: list[int] = []
            for part in parts:
                try:
                    lvl = int(part)
                except ValueError:
                    await interaction.response.send_message("❌ Every copy level must be a whole number.", ephemeral=True)
                    return
                if lvl < 0:
                    await interaction.response.send_message("❌ Copy levels cannot be negative.", ephemeral=True)
                    return
                parsed.append(lvl)

            cap_count = advisor.get_item_copy_cap(existing_user.get("town_hall"), item)
            parsed = parsed[:cap_count]

            def patch(root: dict[str, Any], account_store: dict[str, Any]):
                if chosen_tag:
                    root["active_player_tag"] = chosen_tag
                    account_store.setdefault("player_tag", chosen_tag)
                    if chosen_link:
                        account_store.setdefault("player_name", chosen_link.get("name", "Unknown"))
                account_store.setdefault("manual_copy_levels", {})[item] = parsed
                account_store.setdefault("manual_levels", {}).pop(item, None)
                if target_level is not None:
                    th_for_target = account_store.get("town_hall")
                    cap_target = advisor.get_th_cap_target(th_for_target, item)
                    sanitized_target = int(target_level)
                    if cap_target is not None:
                        sanitized_target = min(sanitized_target, cap_target)
                    if parsed:
                        sanitized_target = max(sanitized_target, max(parsed))
                    account_store.setdefault("targets", {})[item] = sanitized_target

            await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            reward_state = advisor.evaluate_path_rewards(before_user, user)
            if reward_state.get("coins") or reward_state.get("efficiency"):
                user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_tag, reward_state)
            status = advisor.get_item_status(user, item)
            effective_target = advisor.get_effective_targets(user).get(item, target_level or max(parsed))
            await interaction.response.send_message(
                f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{status.get('tracked_copies', 0)}/{status.get('copy_cap', 1)}** copies entered. Target **{effective_target}**. At target now: **{status.get('done', 0)}/{status.get('copy_cap', 1)}**.\n{advisor.build_reward_result_block(reward_state)}",
                ephemeral=True,
            )

        @trackcopies.autocomplete("item")
        async def trackcopies_item_autocomplete(interaction: discord.Interaction, current: str):
            current = (current or "").lower()

            # Prefer the currently selected account's Town Hall when available.
            requested_account = getattr(getattr(interaction, "namespace", None), "account", None)
            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), requested_account)
            chosen_tag = chosen_link["tag"] if chosen_link else requested_account
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            town_hall = user.get("town_hall")

            seen: set[str] = set()
            choices: list[app_commands.Choice[str]] = []

            def append_choice(item_key: str, copy_count: int | None = None):
                if item_key in seen or item_key not in ITEMS:
                    return
                label = ITEMS[item_key].label
                if copy_count and copy_count > 1:
                    label = f"{label} ({copy_count}x)"
                choice = app_commands.Choice(name=f"{label} ({item_key})", value=item_key)
                if current and current not in choice.value.lower() and current not in choice.name.lower():
                    return
                seen.add(item_key)
                choices.append(choice)

            # Resolve from TH_CAPS dynamically. If the selected TH is missing or stale, the advisor
            # will scan other Town Halls before falling back, so items like X-Bow still appear.
            for item_key in sorted(ITEMS, key=lambda k: ITEMS[k].label.lower()):
                copy_count = advisor.get_item_copy_cap(town_hall, item_key)
                if copy_count > 1:
                    append_choice(item_key, copy_count)

            return choices[:25]

        @trackcopies.autocomplete("account")
        async def trackcopies_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @untrackupgrade.autocomplete("item")
        async def untrackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
            current = current.lower()
            return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

        @untrackupgrade.autocomplete("account")
        async def untrackupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @self.tree.command(name="nextupgrade", description="See your top recommended next upgrades")
        @app_commands.describe(count="How many recommendations to show (1-10)", account="Which linked account to view", mode="Advisor priority mode: auto, war, or farm", builder_idle="Set true if you currently have an idle builder", lab_idle="Set true if your lab is idle")
        @app_commands.choices(mode=[app_commands.Choice(name="Auto", value="auto"), app_commands.Choice(name="War", value="war"), app_commands.Choice(name="Farm", value="farm")])
        async def nextupgrade(interaction: discord.Interaction, count: int = 5, account: str | None = None, mode: str = "auto", builder_idle: bool | None = None, lab_idle: bool | None = None):
            await interaction.response.defer(ephemeral=True)
            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            if chosen_tag and user.get("player_tag") != chosen_tag:
                user["player_tag"] = chosen_tag
                if chosen_link:
                    user["player_name"] = chosen_link.get("name", "Unknown")
            if not user.get("synced_levels") and not user.get("manual_levels"):
                await interaction.followup.send(
                    "❌ No upgrade data found for that account yet. Run `/syncupgrades` on the account first, then optionally add manual buildings with `/trackupgrade`.",
                    ephemeral=True,
                )
                return

            timing_context = advisor.get_timing_context(user, requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
            recs, pool = advisor.build_recommendation_pool(user, count=count, pool_size=max(count + 3, 8), requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
            if not recs:
                await interaction.followup.send(
                    "✅ You are at or above all current advisor targets for this account. Add more manual targets or raise your standards.",
                    ephemeral=True,
                )
                return

            await advisor.save_active_recommendations(str(interaction.user.id), chosen_tag, recs)

            try:
                html_card = advisor._build_compact_nextupgrade_card_html(user, recs, pool, timing_context=timing_context)
                file = await advisor.render_html_card_to_file(html_card, "nextupgrade.png", width=920, height=980, wait_ms=1000)
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[UPGRADE ADVISOR CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()

            try:
                embed = advisor._build_safe_nextupgrade_embed(user, recs, pool, timing_context=timing_context)
                embed.set_footer(text="Image card failed, so this compact advisor view is being shown instead.")
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as fallback_exc:
                print(f"[UPGRADE ADVISOR FALLBACK ERROR] {fallback_exc}")
                import traceback
                traceback.print_exc()
                await interaction.followup.send(
                    "❌ Could not build the next-upgrade view right now. Try `/syncupgrades` again, then rerun `/nextupgrade`.",
                    ephemeral=True,
                )

        @nextupgrade.autocomplete("account")
        async def nextupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @self.tree.command(name="missinggoals", description="See which advisor goals still need manual tracking input")
        @app_commands.describe(account="Which linked account to inspect")
        async def missinggoals(interaction: discord.Interaction, account: str | None = None):
            await interaction.response.defer(ephemeral=True)
            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            if chosen_tag and user.get("player_tag") != chosen_tag:
                user["player_tag"] = chosen_tag
                if chosen_link:
                    user["player_name"] = chosen_link.get("name", "Unknown")

            snapshot = advisor.build_untracked_goal_snapshot(user)
            total_items = int(snapshot.get("items", 0) or 0)
            player_name = user.get("player_name") or "Unknown"

            if total_items <= 0:
                embed = discord.Embed(title="✅ Missing Goal Input", color=0x2ECC71)
                embed.description = f"All current advisor goals for **{player_name}** are already tracked."
                advisor._safe_followup_embed_field(embed, name="What this means", value="Your remaining advisor goals should now mostly be true upgrades left to complete, not missing manual entries.", inline=False, limit=900)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(title="🧭 Missing Goal Input", color=0xF1C40F)
            embed.description = advisor.build_untracked_goal_callout(user)
            advisor._safe_followup_embed_field(
                embed,
                name="Account",
                value=f"{player_name} · TH{user.get('town_hall') or '?'} · {str(user.get('role', DEFAULT_ROLE)).title()}",
                inline=False,
                limit=300,
            )
            advisor._safe_followup_embed_field(
                embed,
                name="Counts",
                value=(
                    f"Missing input items: **{total_items}**\n"
                    f"Fully missing items: **{int(snapshot.get('missing_items', 0) or 0)}**\n"
                    f"Partial multi-copy items: **{int(snapshot.get('partial_items', 0) or 0)}**\n"
                    f"Missing tracking slots: **{int(snapshot.get('missing_slots', 0) or 0)}**"
                ),
                inline=False,
                limit=500,
            )

            groups = snapshot.get("groups") or {}
            for category, items in list(groups.items())[:8]:
                emoji = CATEGORY_EMOJIS.get(category, "📌")
                lines = [advisor._format_untracked_goal_line(goal) for goal in items[:10]]
                if len(items) > 10:
                    lines.append(f"…and **{len(items) - 10}** more in this category.")
                advisor._safe_followup_embed_field(
                    embed,
                    name=f"{emoji} {category.replace('_', ' ').title()} ({len(items)})",
                    value="\n".join(lines),
                    inline=False,
                    limit=1000,
                )

            advisor._safe_followup_embed_field(
                embed,
                name="How to fill these",
                value=(
                    "Use **/trackupgrade** for single-value manual items.\n"
                    "Use **/trackcopies** when a multi-copy building or trap has mixed levels.\n"
                    "A text attachment with the full missing-input report is included below."
                ),
                inline=False,
                limit=900,
            )

            report_text = advisor.build_untracked_goals_export_text(user)
            report_bytes = io.BytesIO(report_text.encode("utf-8"))
            report_file = discord.File(report_bytes, filename="missing_goals_report.txt")
            await interaction.followup.send(embed=embed, file=report_file, ephemeral=True)

        @missinggoals.autocomplete("account")
        async def missinggoals_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)

        @self.tree.command(name="upgradeprogress", description="View your current advisor progress")
        @app_commands.describe(account="Which linked account to view", mode="Advisor priority mode: auto, war, or farm", builder_idle="Set true if you currently have an idle builder", lab_idle="Set true if your lab is idle")
        @app_commands.choices(mode=[app_commands.Choice(name="Auto", value="auto"), app_commands.Choice(name="War", value="war"), app_commands.Choice(name="Farm", value="farm")])
        async def upgradeprogress(interaction: discord.Interaction, account: str | None = None, mode: str = "auto", builder_idle: bool | None = None, lab_idle: bool | None = None):
            await interaction.response.defer(ephemeral=True)
            chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
            chosen_tag = chosen_link["tag"] if chosen_link else account
            user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
            if chosen_tag and user.get("player_tag") != chosen_tag:
                user["player_tag"] = chosen_tag
                if chosen_link:
                    user["player_name"] = chosen_link.get("name", "Unknown")
            progress = advisor.build_progress_snapshot(user)
            milestone_hint = advisor.build_milestone_hint(user)
            timing_context = advisor.get_timing_context(user, requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
            progress_recs = advisor.build_recommendations(user, count=3, requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
            await advisor.save_active_recommendations(str(interaction.user.id), chosen_tag, progress_recs)

            try:
                html_card = advisor._build_compact_progress_card_html(user, timing_context=timing_context)
                file = await advisor.render_html_card_to_file(html_card, "upgradeprogress.png", width=920, height=980, wait_ms=1000)
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[UPGRADE PROGRESS CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()

            try:
                embed = discord.Embed(title=f"{CHART} Upgrade Progress", color=0x3498DB)
                embed.description = advisor.profile_summary(user)
                advisor._safe_followup_embed_field(
                    embed,
                    name="Progress Snapshot",
                    value=f"{progress['percent']}% complete\n{progress['done']} / {progress['tracked']} tracked goals complete",
                    inline=True,
                )
                advisor._safe_followup_embed_field(
                    embed,
                    name="Speed / ETA",
                    value=advisor.build_velocity_summary(user),
                    inline=True,
                )
                advisor._safe_followup_embed_field(
                    embed,
                    name="Next Focus",
                    value=milestone_hint,
                    inline=True,
                )
                advisor._safe_followup_embed_field(
                    embed,
                    name="Next Advisor Reward",
                    value=advisor.build_next_reward_block(user),
                    inline=False,
                )
                advisor._safe_followup_embed_field(embed, name="Milestone Breakdown", value=advisor.build_milestone_status_block(user), inline=False)
                advisor._safe_followup_embed_field(embed, name="Remaining Goals", value=advisor.build_remaining_goals_block(user, limit=6), inline=False)
                advisor._safe_followup_embed_field(embed, name="Missing Input Summary", value=advisor.build_untracked_goal_callout(user), inline=False)
                advisor._safe_followup_embed_field(embed, name="Advisor Tracking Gaps", value=advisor.build_untracked_goals_block(user, limit=4), inline=False)
                advisor._safe_followup_embed_field(embed, name="Data Sources", value=advisor.build_data_source_summary(user), inline=True)
                advisor._safe_followup_embed_field(embed, name="How To Read This", value=advisor.build_progress_explainer(user), inline=True)
                embed.set_footer(text="Image fallback failed, so this condensed embed is being shown instead.")
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as fallback_exc:
                print(f"[UPGRADE PROGRESS FALLBACK ERROR] {fallback_exc}")
                import traceback
                traceback.print_exc()
                await interaction.followup.send(
                    "❌ Could not build the progress image right now, so the advisor fell back to text.",
                    ephemeral=True,
                )
        @upgradeprogress.autocomplete("account")
        async def upgradeprogress_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)


def register_upgrade_advisor(tree: app_commands.CommandTree, deps: dict[str, Any]) -> UpgradeAdvisor:
    advisor = UpgradeAdvisor(tree, deps)
    advisor.register()
    return advisor
