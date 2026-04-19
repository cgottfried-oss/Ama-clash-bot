from __future__ import annotations

import os
import io
import html
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from th_caps import TH_CAPS, get_item_cap, get_category_caps, normalize_cap_entry

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

# Some TH_CAPS categories only store max level as a plain int (especially defenses/traps),
# so the copy count is not encoded in the cap entry itself. These fallbacks let /trackcopies
# correctly treat those items as multi-copy even when the cap table entry is scalar.
MULTI_COPY_FALLBACK_COUNTS: dict[str, int] = {
    "air_defense": 4,
    "x_bow": 4,
    "inferno_tower": 2,
    "bomb": 8,
    "giant_bomb": 7,
    "air_bomb": 6,
    "seeking_air_mine": 6,
    "spring_trap": 10,
    "skeleton_trap": 4,
    "tornado_trap": 1,
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
            "last_synced_at": None,
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
        legacy_account["last_synced_at"] = user.get("last_synced_at")

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
                legacy_account["last_synced_at"],
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

        def patch(root: dict[str, Any], account: dict[str, Any]):
            role = root.get("role", DEFAULT_ROLE)
            root["active_player_tag"] = player_tag
            account["town_hall"] = th
            account["player_tag"] = player_tag
            account["player_name"] = player_name
            account["synced_levels"] = synced_levels
            account["synced_max_levels"] = synced_max_levels
            account["last_synced_at"] = datetime.now(timezone.utc).isoformat()
            account.setdefault("targets", {})
            inferred = self.infer_default_targets(th, role)
            for key, value in inferred.items():
                account["targets"].setdefault(key, value)

        await self.save_user_patch(discord_user_id, patch, player_tag=player_tag)
        return await self.get_user_store(discord_user_id, player_tag=player_tag)

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

    def get_item_copy_cap(self, town_hall: int | None, item_key: str) -> int:
        fallback = max(1, int(MULTI_COPY_FALLBACK_COUNTS.get(item_key, 1)))
        if item_key not in TH_CAP_NAME_MAP:
            return fallback
        if not town_hall:
            return fallback
        category, cap_name = TH_CAP_NAME_MAP[item_key]
        cap = get_item_cap(int(town_hall), category, cap_name, None)
        if cap is None:
            return fallback
        if isinstance(cap, dict):
            try:
                return max(1, int(normalize_cap_entry(cap).get("count", 1)))
            except (TypeError, ValueError):
                return fallback
        return fallback

    def is_multi_copy_item(self, town_hall: int | None, item_key: str) -> bool:
        copy_cap = self.get_item_copy_cap(town_hall, item_key)
        if copy_cap > 1:
            return True
        # Fallback: if Town Hall is missing, stale, or the cap table entry is unavailable
        # for this specific TH, treat any item that has a multi-copy cap at any TH as multi-copy.
        if item_key not in TH_CAP_NAME_MAP:
            return False
        category, cap_name = TH_CAP_NAME_MAP[item_key]
        for th in sorted(TH_CAPS.keys()):
            cap = get_item_cap(int(th), category, cap_name, None)
            if isinstance(cap, dict):
                try:
                    if int(normalize_cap_entry(cap).get("count", 1)) > 1:
                        return True
                except (TypeError, ValueError):
                    continue
        return False

    def get_item_status(self, user: dict[str, Any], item_key: str, targets: dict[str, int] | None = None, levels: dict[str, int] | None = None) -> dict[str, Any]:
        if targets is None:
            targets = self.get_effective_targets(user)
        if levels is None:
            levels = self.get_effective_levels(user)
        target = int(targets.get(item_key, 0) or 0)
        town_hall = user.get("town_hall")
        copy_cap = self.get_item_copy_cap(town_hall, item_key)
        manual_copy_levels = self.get_manual_copy_levels(user).get(item_key, [])
        if copy_cap > 1 and manual_copy_levels:
            confirmed = [max(0, int(v)) for v in manual_copy_levels[:copy_cap]]
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
            "tracked_copies": 1 if item_key in levels or item_key in (user.get("manual_levels") or {}) else 0,
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

    def get_timing_context(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> dict[str, Any]:
        mode = self.resolve_advisor_mode(user, requested_mode)
        if builder_idle is None:
            builder_idle = bool(user.get("builder_idle") or user.get("builders_idle") or user.get("builder_free"))
        if lab_idle is None:
            lab_idle = bool(user.get("lab_idle") or user.get("laboratory_idle") or user.get("lab_free"))
        return {
            "mode": mode,
            "builder_idle": bool(builder_idle),
            "lab_idle": bool(lab_idle),
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
        timing_context = timing_context or self.get_timing_context(user)
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
        return (
            f"🎯 **Role:** {role}\n"
            f"🏠 **Town Hall:** {user.get('town_hall') or '?'}\n"
            f"📈 **Progress:** {progress['percent']}% ({progress['done']}/{progress['tracked']})\n"
            f"🔥 **War Ready:** {war_ready}\n"
            f"🧭 **Top pressure lane:** {top_lane}\n"
            f"⚙️ **Mode:** {mode}\n"
            f"🛠️ **Builders:** {builder_state}\n"
            f"🧪 **Lab:** {lab_state}"
        )

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
        return (
            f"This is **advisor target progress**, not a full account-max check. "
            f"You have **{progress['done']} of {progress['tracked']}** tracked goals done. "
            f"Milestone core counts only use **confirmed data**. Multi-copy buildings/traps only count fully once all copies are tracked manually."
        )

    def build_data_source_summary(self, user: dict[str, Any]) -> str:
        synced = len(user.get("synced_levels", {}))
        manual = len(user.get("manual_levels", {}))
        return (
            f"Auto-synced from Clash API: **{synced}** hero/lab/pet items\n"
            f"Manual entries: **{manual}** (used for building targets and any overrides)\n"
            f"Note: buildings are **not auto-synced** yet."
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

    def _render_card_progress_bar(self, current: int, target: int) -> tuple[int, str]:
        target = max(1, int(target or 1))
        current = max(0, min(int(current or 0), target))
        pct = int(round((current / target) * 100))
        return max(0, min(100, pct)), f"{current}/{target}"

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
        meta = ITEMS.get(rec.get("key"))
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
}}
.container {{
    width: 1000px;
    min-height: 1150px;
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

    def build_nextupgrade_card_html(self, user: dict[str, Any], recs: list[dict[str, Any]], pool: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
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
        mode_label = f"{MODE_EMOJIS.get(timing_context.get("mode", "war"), "🧠")} {str(timing_context.get("mode", "war")).title()}"
        builder_label = "Idle" if timing_context.get("builder_idle") else "Busy/Unknown"
        lab_label = "Idle" if timing_context.get("lab_idle") else "Busy/Unknown"
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role / War Ready", f"{role} · {war_ready}", "⚔️"),
            self._render_summary_card_html("Tracked Progress", f"{progress['percent']}% ({progress['done']}/{progress['tracked']})", "📈"),
            self._render_summary_card_html("Top Pressure Lane", f"{top_lane} ({int(pressure_lane[1])}% done)", LANE_EMOJIS.get(pressure_lane[0], "📌")),
            self._render_summary_card_html("Mode / Builders", f"{mode_label} · {builder_label}", "🛠️"),
            self._render_summary_card_html("Lab / Next Reward", f"{lab_label} · {next_reward}", "🧪"),
        ])
        if recs:
            rows_html = ''.join(self._render_upgrade_pick_row_html(rec, idx) for idx, rec in enumerate(recs[:5], start=1))
        else:
            rows_html = '<div class="empty">Nothing urgent right now.</div>'
        board_html = (
            '<div class="section-title">Top Upgrade Picks</div>'
            + rows_html
            + '<div class="section-title" style="margin-top:28px;">Lane Breakdown</div>'
            + self._render_lane_tiles_html(recs)
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
            self._render_summary_card_html("Tracked Goals", f"{progress['done']}/{progress['tracked']}", "🎯"),
            self._render_summary_card_html("War Ready", "Yes" if achieved.get("war_ready") else "Not yet", "✅"),
            self._render_summary_card_html("Last Sync", str(user.get("last_synced_at") or "Never")[:16].replace("T", " "), "🕒"),
        ])
        rows = []
        metrics = [
            ("Heroes Complete", f"{groups['heroes']['done']}/{groups['heroes']['total']}", "Confirmed hero targets done"),
            ("Offense Core", f"{groups['offense']['done']}/{groups['offense']['total']}", "Key offensive items at target"),
            ("Builder Core", f"{groups['builder']['done']}/{groups['builder']['total']}", "Core buildings confirmed"),
            ("Next Focus", self.build_milestone_hint(user).replace("**", ""), "Closest milestone right now"),
        ]
        for idx, (name, value, reason) in enumerate(metrics, start=1):
            rows.append(f'''
            <div class="donation-row upgrade-row">
                <div class="donation-rank">{idx}</div>
                <div class="donation-main">
                    <div class="donation-name">{self._html_escape(name)}</div>
                    <div class="upgrade-reason">{self._html_escape(reason)}</div>
                </div>
                <div class="donation-stats"><div><strong>{self._html_escape(value)}</strong></div></div>
            </div>
            ''')
        reward_track = self.build_next_reward_block(user).replace("**", "")
        board_html = (
            '<div class="section-title">Progress Breakdown</div>'
            + ''.join(rows)
            + '<div class="section-title" style="margin-top:28px;">Lane Snapshot</div>'
            + self._render_lane_tiles_html(self.build_recommendations(user, count=3, requested_mode=(timing_context or {}).get("mode"), builder_idle=(timing_context or {}).get("builder_idle"), lab_idle=(timing_context or {}).get("lab_idle")))
            + f'<div class="note">Reward track: {self._html_escape(reward_track)}</div>'
        )
        subtitle = f"Progress snapshot for {player_name}"
        return self._base_upgrade_card_html("Upgrade Progress", subtitle, summary_html, board_html)

    async def render_html_card_to_file(self, html_content: str, filename: str) -> discord.File:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        tmp.close()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox"])
                page = await browser.new_page(viewport={"width": 1060, "height": 1280, "device_scale_factor": 1})
                await page.set_content(html_content, wait_until="networkidle")
                await page.wait_for_timeout(350)
                await page.screenshot(path=tmp.name, full_page=True)
                await browser.close()
            with open(tmp.name, 'rb') as f:
                data = io.BytesIO(f.read())
            data.seek(0)
            return discord.File(fp=data, filename=filename)
        finally:
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

            embed = discord.Embed(title=f"{CHECK} Upgrade Sync Complete", color=0x2ECC71)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="What got refreshed", value=advisor.build_data_source_summary(user), inline=False)
            embed.add_field(name="Advisor progress", value=f"{progress['bar']} {progress['percent']}% (**{progress['done']} / {progress['tracked']}** tracked goals)", inline=False)
            embed.add_field(name="What this means", value=advisor.build_progress_explainer(user), inline=False)
            embed.add_field(name="New this sync", value=milestone_celebration, inline=False)
            embed.set_footer(text=f"Viewing account: {user.get('player_name', 'Unknown')} {user.get('player_tag', '')}")

            await interaction.followup.send(embed=embed, ephemeral=True)

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
            effective_target = advisor.get_effective_targets(user).get(item, target_level or current_level)
            if copy_count and advisor.is_multi_copy_item(user.get("town_hall"), item):
                copy_cap = advisor.get_item_copy_cap(user.get("town_hall"), item)
                await interaction.response.send_message(
                    f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{min(copy_count, copy_cap)}/{copy_cap}** copies entered at level **{current_level}** and target **{effective_target}**. Use `/trackcopies` for mixed levels.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** at level **{current_level}** with target **{effective_target}**.",
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
            existing_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
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
            status = advisor.get_item_status(user, item)
            effective_target = advisor.get_effective_targets(user).get(item, target_level or max(parsed))
            await interaction.response.send_message(
                f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{status.get('tracked_copies', 0)}/{status.get('copy_cap', 1)}** copies entered. Target **{effective_target}**. At target now: **{status.get('done', 0)}/{status.get('copy_cap', 1)}**.",
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

            def append_choice(item_key: str, display_name: str | None = None, copy_count: int | None = None):
                if item_key in seen or item_key not in ITEMS:
                    return
                label = display_name or ITEMS[item_key].label
                if copy_count and copy_count > 1:
                    label = f"{label} ({copy_count}x)"
                choice = app_commands.Choice(name=f"{label} ({item_key})", value=item_key)
                if current and current not in choice.value.lower() and current not in choice.name.lower():
                    return
                seen.add(item_key)
                choices.append(choice)

            # First, try the selected account's TH so the list is as accurate as possible.
            if town_hall:
                caps = TH_CAPS.get(int(town_hall), {})
                for category in caps.values():
                    if not isinstance(category, dict):
                        continue
                    for cap_name, entry in category.items():
                        norm = normalize_cap_entry(entry)
                        if int(norm.get("count", 1)) <= 1:
                            continue
                        matched_key = None
                        for item_key, mapping in TH_CAP_NAME_MAP.items():
                            if item_key in ITEMS and mapping == (next((k for k,v in TH_CAPS[int(town_hall)].items() if v is category), None), cap_name):
                                matched_key = item_key
                                break
                        if matched_key:
                            append_choice(matched_key, cap_name, int(norm.get("count", 1)))

            # Fallback: include any item that is multi-copy at any TH so valid items like
            # Air Defense still appear even before a fresh sync or when a TH entry is stale.
            for item_key in ITEMS:
                if item_key in seen:
                    continue
                if not advisor.is_multi_copy_item(town_hall, item_key):
                    continue
                copy_count = 1
                if item_key in TH_CAP_NAME_MAP:
                    category_name, cap_name = TH_CAP_NAME_MAP[item_key]
                    for th, caps in TH_CAPS.items():
                        entry = get_item_cap(int(th), category_name, cap_name, None)
                        norm = normalize_cap_entry(entry)
                        if int(norm.get("count", 1)) > 1:
                            copy_count = max(copy_count, int(norm.get("count", 1)))
                append_choice(item_key, None, copy_count)

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

            try:
                html_card = advisor.build_nextupgrade_card_html(user, recs, pool, timing_context=timing_context)
                file = await advisor.render_html_card_to_file(html_card, "nextupgrade.png")
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[UPGRADE ADVISOR CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()

            role = user.get("role", DEFAULT_ROLE)
            progress = advisor.build_progress_snapshot(user)

            embed = discord.Embed(
                title=f"{BRAIN} Upgrade Advisor",
                color=0x5865F2,
                description=advisor.profile_summary(user),
            )
            embed.add_field(
                name="Account Snapshot",
                value=advisor.build_quick_status_block(user, recs, timing_context=timing_context),
                inline=False,
            )
            embed.add_field(
                name="Top Upgrade Picks",
                value=advisor.build_upgrade_dashboard(recs),
                inline=False,
            )
            embed.add_field(
                name="Lane Breakdown",
                value=advisor.build_lane_summary(recs),
                inline=True,
            )
            embed.add_field(
                name="Focus Right Now",
                value=advisor.build_milestone_hint(user),
                inline=True,
            )
            embed.add_field(
                name="What Can Wait",
                value=advisor.build_waitlist(pool, role, limit=2),
                inline=False,
            )
            embed.add_field(
                name="Plan Summary",
                value=advisor.build_decision_block(recs[:3], role),
                inline=False,
            )
            embed.add_field(
                name="Progress Toward Targets",
                value=f"{progress['bar']} **{progress['percent']}%** complete\n{progress['done']} / {progress['tracked']} tracked goals done",
                inline=True,
            )
            embed.add_field(
                name="Next Reward / Milestone",
                value=advisor.build_next_reward_block(user),
                inline=True,
            )
            embed.set_footer(text="UI refresh: hero/lab/builder lanes are grouped so the next move is easier to read.")

            await interaction.followup.send(embed=embed, ephemeral=True)
        @nextupgrade.autocomplete("account")
        async def nextupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
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

            try:
                html_card = advisor.build_upgradeprogress_card_html(user, timing_context=timing_context)
                file = await advisor.render_html_card_to_file(html_card, "upgradeprogress.png")
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[UPGRADE PROGRESS CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()

            embed = discord.Embed(title=f"{CHART} Upgrade Progress", color=0x3498DB)
            embed.description = advisor.profile_summary(user)
            embed.add_field(
                name="Progress Snapshot",
                value=f"{progress['bar']} **{progress['percent']}%**\n**{progress['done']} / {progress['tracked']}** tracked goals complete",
                inline=True,
            )
            embed.add_field(
                name="Next Focus",
                value=milestone_hint,
                inline=True,
            )
            embed.add_field(
                name="Next Advisor Reward",
                value=advisor.build_next_reward_block(user),
                inline=False,
            )
            embed.add_field(name="Milestone Breakdown", value=advisor.build_milestone_status_block(user), inline=False)
            embed.add_field(name="Data Sources", value=advisor.build_data_source_summary(user), inline=True)
            embed.add_field(name="How To Read This", value=advisor.build_progress_explainer(user), inline=True)
            embed.set_footer(text="Tip: use the account option if you have multiple linked accounts.")

            await interaction.followup.send(embed=embed, ephemeral=True)
        @upgradeprogress.autocomplete("account")
        async def upgradeprogress_account_autocomplete(interaction: discord.Interaction, current: str):
            return await account_autocomplete(interaction, current)


def register_upgrade_advisor(tree: app_commands.CommandTree, deps: dict[str, Any]) -> UpgradeAdvisor:
    advisor = UpgradeAdvisor(tree, deps)
    advisor.register()
    return advisor
