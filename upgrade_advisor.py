from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import discord
from discord import app_commands


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
        "barbarian_king": 55,
        "archer_queen": 55,
        "grand_warden": 25,
        "healers": 6,
        "balloons": 9,
        "electro_dragon": 3,
        "hog_rider": 9,
        "miners": 6,
        "rage_spell": 6,
        "freeze_spell": 6,
        "invisibility_spell": 2,
        "army_camp": 10,
        "clan_castle": 9,
        "laboratory": 10,
        "spell_factory": 7,
    },
    13: {
        "barbarian_king": 65,
        "archer_queen": 65,
        "grand_warden": 40,
        "royal_champion": 10,
        "healers": 7,
        "balloons": 10,
        "dragons": 9,
        "hog_rider": 10,
        "miners": 7,
        "freeze_spell": 7,
        "rage_spell": 6,
        "invisibility_spell": 3,
        "army_camp": 11,
        "clan_castle": 10,
        "laboratory": 11,
        "blacksmith": 2,
    },
    14: {
        "barbarian_king": 75,
        "archer_queen": 75,
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
    "barbarian_king": ItemMeta("barbarian_king", "Barbarian King", "hero", 9.0, 3.0, 2.0, 4.0, 5.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="hero"),
    "archer_queen": ItemMeta("archer_queen", "Archer Queen", "hero", 10.0, 4.0, 2.0, 5.0, 5.0, role_bonus={"attacker": 7, "hybrid": 4, "farmer": 0}, source="hero"),
    "grand_warden": ItemMeta("grand_warden", "Grand Warden", "hero", 10.0, 2.0, 2.0, 7.0, 5.0, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={10, 20, 30, 40, 50, 60, 70}, source="hero"),
    "royal_champion": ItemMeta("royal_champion", "Royal Champion", "hero", 9.5, 2.0, 2.5, 4.5, 5.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 10, 20, 25, 35, 45}, source="hero"),
    "minion_prince": ItemMeta("minion_prince", "Minion Prince", "hero", 8.5, 2.0, 2.0, 4.0, 5.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="hero"),
    "dragon_duke": ItemMeta("dragon_duke", "Dragon Duke", "hero", 9.0, 2.0, 2.0, 4.0, 5.5, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -2}, source="hero"),

    # Buildings / structure priorities
    "army_camp": ItemMeta("army_camp", "Army Camp", "building", 10.0, 5.0, 0.0, 8.0, 4.0, foundational=True, role_bonus={"attacker": 8, "hybrid": 7, "farmer": 2}, breakpoints={8, 9, 10, 11, 12, 13}),
    "clan_castle": ItemMeta("clan_castle", "Clan Castle", "building", 9.0, 2.0, 2.0, 8.0, 4.0, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": 0}, breakpoints={7, 8, 9, 10, 11, 12}),
    "laboratory": ItemMeta("laboratory", "Laboratory", "building", 8.0, 3.0, 0.0, 10.0, 4.0, foundational=True, role_bonus={"attacker": 8, "hybrid": 6, "farmer": 0}, breakpoints={8, 9, 10, 11, 12, 13, 14, 15, 16}),
    "spell_factory": ItemMeta("spell_factory", "Spell Factory", "building", 7.0, 1.0, 0.0, 7.0, 4.0, foundational=True, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 6, 7}),
    "dark_spell_factory": ItemMeta("dark_spell_factory", "Dark Spell Factory", "building", 6.0, 1.0, 0.0, 6.0, 4.0, foundational=False, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}),
    "barracks": ItemMeta("barracks", "Barracks", "building", 6.0, 1.0, 0.0, 5.0, 4.0, foundational=False, role_bonus={"attacker": 4, "hybrid": 2, "farmer": -2}),
    "dark_barracks": ItemMeta("dark_barracks", "Dark Barracks", "building", 6.0, 1.0, 0.0, 5.0, 4.0, foundational=False, role_bonus={"attacker": 4, "hybrid": 2, "farmer": -2}),
    "pet_house": ItemMeta("pet_house", "Pet House", "building", 8.0, 1.0, 0.0, 7.0, 4.5, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={4, 8, 10}),
    "blacksmith": ItemMeta("blacksmith", "Blacksmith", "building", 8.0, 1.0, 0.0, 8.0, 4.5, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={2, 4, 6, 8, 10, 12}),
    "hero_hall": ItemMeta("hero_hall", "Hero Hall", "building", 9.0, 1.0, 1.0, 9.0, 5.0, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={9, 10, 11}),

    # Troops
    "healers": ItemMeta("healers", "Healers", "troop", 9.0, 3.0, 0.0, 5.0, 3.0, role_bonus={"attacker": 6, "hybrid": 3, "farmer": 0}, source="troop"),
    "balloons": ItemMeta("balloons", "Balloons", "troop", 9.0, 2.0, 0.0, 4.0, 3.0, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -1}, source="troop"),
    "dragons": ItemMeta("dragons", "Dragons", "troop", 8.0, 2.0, 0.0, 4.0, 3.5, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "electro_dragon": ItemMeta("electro_dragon", "Electro Dragon", "troop", 8.5, 2.0, 0.0, 4.0, 3.8, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "hog_rider": ItemMeta("hog_rider", "Hog Rider", "troop", 8.5, 2.0, 0.0, 4.0, 3.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "miners": ItemMeta("miners", "Miners", "troop", 8.0, 3.0, 0.0, 4.0, 3.0, role_bonus={"attacker": 4, "hybrid": 3, "farmer": 1}, source="troop"),
    "root_rider": ItemMeta("root_rider", "Root Rider", "troop", 9.0, 1.0, 0.0, 4.0, 4.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),
    "apprentice_warden": ItemMeta("apprentice_warden", "Apprentice Warden", "troop", 9.0, 1.0, 0.0, 6.0, 4.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),

    # Spells
    "rage_spell": ItemMeta("rage_spell", "Rage Spell", "spell", 8.0, 1.0, 0.0, 5.0, 2.5, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="spell"),
    "freeze_spell": ItemMeta("freeze_spell", "Freeze Spell", "spell", 9.0, 1.0, 0.0, 6.0, 2.5, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="spell"),
    "invisibility_spell": ItemMeta("invisibility_spell", "Invisibility Spell", "spell", 8.5, 1.0, 0.0, 6.0, 3.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="spell"),
    "recall_spell": ItemMeta("recall_spell", "Recall Spell", "spell", 7.0, 1.0, 0.0, 6.0, 3.0, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -2}, source="spell"),

    # Pets
    "unicorn": ItemMeta("unicorn", "Unicorn", "pet", 9.0, 1.0, 0.0, 5.0, 3.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),
    "phoenix": ItemMeta("phoenix", "Phoenix", "pet", 8.5, 1.0, 0.0, 5.0, 3.2, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, source="pet"),
    "diggy": ItemMeta("diggy", "Diggy", "pet", 8.5, 1.0, 0.0, 5.5, 3.2, role_bonus={"attacker": 5, "hybrid": 4, "farmer": -2}, source="pet"),
    "frosty": ItemMeta("frosty", "Frosty", "pet", 7.5, 1.0, 0.0, 5.0, 3.0, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "spirit_fox": ItemMeta("spirit_fox", "Spirit Fox", "pet", 9.0, 1.0, 0.0, 6.0, 3.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),

    # Economy / defensive options for farmer or hybrid preference
    "gold_mine": ItemMeta("gold_mine", "Gold Mine", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "elixir_collector": ItemMeta("elixir_collector", "Elixir Collector", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "dark_elixir_drill": ItemMeta("dark_elixir_drill", "Dark Elixir Drill", "economy", 0.0, 8.5, 0.0, 2.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 7}),
    "gold_storage": ItemMeta("gold_storage", "Gold Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "elixir_storage": ItemMeta("elixir_storage", "Elixir Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "air_defense": ItemMeta("air_defense", "Air Defense", "defense", 0.0, 1.0, 8.0, 2.0, 3.5, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
    "inferno_tower": ItemMeta("inferno_tower", "Inferno Tower", "defense", 0.0, 1.0, 8.5, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "x_bow": ItemMeta("x_bow", "X-Bow", "defense", 0.0, 1.0, 7.0, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
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

    async def load_store(self) -> dict[str, Any]:
        store = await self.safe_load_json(self.store_path)
        if not isinstance(store, dict):
            store = {}
        store.setdefault("users", {})
        return store

    async def get_user_store(self, user_id: str) -> dict[str, Any]:
        store = await self.load_store()
        users = store.setdefault("users", {})
        user = users.setdefault(
            str(user_id),
            {
                "role": DEFAULT_ROLE,
                "manual_levels": {},
                "targets": {},
                "synced_levels": {},
                "player_tag": None,
                "player_name": None,
                "town_hall": None,
                "last_synced_at": None,
            },
        )
        return user

    async def save_user_patch(self, user_id: str, patch_fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        def _update(store: dict[str, Any]):
            if not isinstance(store, dict):
                store = {}
            users = store.setdefault("users", {})
            user = users.setdefault(
                str(user_id),
                {
                    "role": DEFAULT_ROLE,
                    "manual_levels": {},
                    "targets": {},
                    "synced_levels": {},
                    "player_tag": None,
                    "player_name": None,
                    "town_hall": None,
                    "last_synced_at": None,
                },
            )
            patch_fn(user)
            return store

        return await self.update_json_file(self.store_path, _update)

    async def get_primary_link(self, discord_user_id: str) -> dict[str, str] | None:
        linked_raw = await self.safe_load_json(self.linked_file)
        entries = linked_raw.get(str(discord_user_id), []) if isinstance(linked_raw, dict) else []
        if not entries:
            return None
        first = entries[0]
        if isinstance(first, str):
            return {"tag": self.normalize_tag(first), "name": "Unknown"}
        if isinstance(first, dict) and first.get("tag"):
            return {"tag": self.normalize_tag(first["tag"]), "name": first.get("name", "Unknown")}
        return None

    async def fetch_player_data(self, tag: str) -> dict[str, Any] | None:
        normalized_tag = self.normalize_tag(tag)
        encoded_tag = normalized_tag.replace("#", "%23")
        url = f"{self.clash_api_base}/players/{encoded_tag}"
        return await self.get_cached_or_fetch(f"player_{normalized_tag}", url, ttl=300)

    def infer_default_targets(self, town_hall: int | None, role: str) -> dict[str, int]:
        if not town_hall:
            return {}
        baseline = RECOMMENDED_TARGETS_BY_TH.get(int(town_hall), {})
        targets = dict(baseline)

        if role == "attacker":
            for item in ("barbarian_king", "archer_queen", "grand_warden", "royal_champion", "minion_prince", "dragon_duke", "army_camp", "laboratory", "clan_castle"):
                if item in targets:
                    targets[item] += 1
        elif role == "farmer":
            for item in ("gold_mine", "elixir_collector", "dark_elixir_drill", "gold_storage", "elixir_storage"):
                targets[item] = max(targets.get(item, 0), 1)
        return targets

    def parse_player_levels(self, player: dict[str, Any]) -> tuple[int | None, str, str, dict[str, int]]:
        th = player.get("townHallLevel")
        player_tag = self.normalize_tag(player.get("tag", "")) if player.get("tag") else ""
        player_name = player.get("name", "Unknown")
        levels: dict[str, int] = {}

        for section in ("heroes", "troops", "spells", "heroEquipment", "heroPets"):
            for entry in player.get(section, []) or []:
                item_key = AUTOSYNC_NAME_MAP.get(entry.get("name"))
                if not item_key:
                    continue
                try:
                    levels[item_key] = int(entry.get("level", 0))
                except (TypeError, ValueError):
                    continue

        return th, player_tag, player_name, levels

    async def sync_player(self, discord_user_id: str) -> dict[str, Any]:
        link = await self.get_primary_link(discord_user_id)
        if not link:
            raise ValueError("You need to link a Clash account first with /link.")

        player = await self.fetch_player_data(link["tag"])
        if not player:
            raise ValueError("Could not fetch your Clash player data right now.")

        th, player_tag, player_name, synced_levels = self.parse_player_levels(player)

        def patch(user: dict[str, Any]):
            role = user.get("role", DEFAULT_ROLE)
            user["town_hall"] = th
            user["player_tag"] = player_tag
            user["player_name"] = player_name
            user["synced_levels"] = synced_levels
            user["last_synced_at"] = datetime.now(timezone.utc).isoformat()
            user.setdefault("targets", {})
            inferred = self.infer_default_targets(th, role)
            for key, value in inferred.items():
                user["targets"].setdefault(key, value)

        await self.save_user_patch(discord_user_id, patch)
        return await self.get_user_store(discord_user_id)

    def get_effective_levels(self, user: dict[str, Any]) -> dict[str, int]:
        effective = {}
        effective.update(user.get("synced_levels", {}))
        effective.update(user.get("manual_levels", {}))
        return {k: int(v) for k, v in effective.items() if k in ITEMS}

    def get_effective_targets(self, user: dict[str, Any]) -> dict[str, int]:
        role = user.get("role", DEFAULT_ROLE)
        inferred = self.infer_default_targets(user.get("town_hall"), role)
        targets = dict(inferred)
        targets.update({k: int(v) for k, v in (user.get("targets") or {}).items() if k in ITEMS})
        return targets

    def score_candidate(self, *, item_key: str, current: int, target: int, role: str) -> dict[str, Any]:
        meta = ITEMS[item_key]
        role_weights = ROLE_WEIGHTS.get(role, ROLE_WEIGHTS[DEFAULT_ROLE])
        gap = max(target - current, 0)
        if gap <= 0:
            return {
                "item_key": item_key,
                "label": meta.label,
                "score": 0.0,
                "priority": "done",
                "current": current,
                "next_level": current,
                "target": target,
                "reasons": ["At or above advisor target."],
            }

        next_level = current + 1
        weighted_impact = (
            meta.offense * role_weights["offense"]
            + meta.farming * role_weights["farming"]
            + meta.defense * role_weights["defense"]
            + meta.utility * role_weights["utility"]
        )
        base = weighted_impact * 4.0
        efficiency = min(12.0, (weighted_impact / max(meta.time_weight, 1.0)) * 4.0)
        urgency = min(10.0, gap * 1.8)
        foundational = 8.0 if meta.foundational else 0.0
        breakpoint = 6.0 if next_level in meta.breakpoints else 0.0
        role_bonus = float(meta.role_bonus.get(role, 0.0))
        finish_bonus = 3.0 if next_level >= target else 0.0

        score = round(base + efficiency + urgency + foundational + breakpoint + role_bonus + finish_bonus, 1)
        if score >= 78:
            priority = "High"
        elif score >= 56:
            priority = "Medium"
        else:
            priority = "Low"

        reasons: list[str] = []
        if meta.foundational:
            reasons.append("Foundational upgrade that boosts multiple future choices.")
        if role == "attacker" and meta.offense >= 8:
            reasons.append("Strong war-hit impact for an attacker profile.")
        elif role == "farmer" and meta.farming >= 8:
            reasons.append("Strong resource efficiency for a farmer profile.")
        elif role == "hybrid" and (meta.offense + meta.utility) >= 13:
            reasons.append("High all-around value for a balanced profile.")
        if gap >= 5:
            reasons.append(f"You are {gap} levels behind your advisor target.")
        elif gap >= 3:
            reasons.append(f"Still {gap} levels away from your advisor target.")
        if next_level in meta.breakpoints:
            reasons.append(f"Level {next_level} is a meaningful breakpoint for this item.")
        if efficiency >= 9:
            reasons.append("Excellent value per upgrade step.")
        if not reasons:
            reasons.append("Useful incremental upgrade with solid efficiency.")

        return {
            "item_key": item_key,
            "label": meta.label,
            "score": score,
            "priority": priority,
            "current": current,
            "next_level": next_level,
            "target": target,
            "gap": gap,
            "reasons": reasons[:3],
        }

    def build_recommendations(self, user: dict[str, Any], count: int = 5) -> list[dict[str, Any]]:
        role = user.get("role", DEFAULT_ROLE)
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        candidates: list[dict[str, Any]] = []
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            current = int(levels.get(item_key, 0))
            if current >= target:
                continue
            candidates.append(self.score_candidate(item_key=item_key, current=current, target=int(target), role=role))

        candidates.sort(key=lambda row: (-row["score"], row["label"].lower()))
        return candidates[: max(1, min(count, 10))]

    def build_progress_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        if not targets:
            return {"tracked": 0, "done": 0, "percent": 0, "bar": "ââââââââââ"}

        tracked = 0
        done = 0
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            tracked += 1
            current = int(levels.get(item_key, 0))
            if current >= int(target):
                done += 1

        percent = round((done / tracked) * 100) if tracked else 0
        filled = max(0, min(10, round(percent / 10)))
        bar = "â" * filled + "â" * (10 - filled)
        return {"tracked": tracked, "done": done, "percent": percent, "bar": bar}

    def format_top_block(self, recs: list[dict[str, Any]]) -> str:
        chunks = []
        for rec in recs:
            chunks.append(
                f"**{rec['priority']}** â {rec['label']} â {rec['next_level']}  \n"
                f"Score: **{rec['score']}** | Current: {rec['current']} | Target: {rec['target']}\n"
                + "\n".join(f"â¢ {reason}" for reason in rec["reasons"])
            )
        return "\n\n".join(chunks)

    def profile_summary(self, user: dict[str, Any]) -> str:
        role = user.get("role", DEFAULT_ROLE).title()
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        synced_at = user.get("last_synced_at")
        sync_text = "Never"
        if synced_at:
            try:
                sync_text = discord.utils.format_dt(datetime.fromisoformat(synced_at), style="R")
            except Exception:
                sync_text = synced_at
        return f"Player: **{player_name}** | TH **{th}** | Role: **{role}** | Last sync: {sync_text}"

    def register(self):
        advisor = self

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
                lambda user: user.update({"role": role.value}),
            )
            user = await advisor.get_user_store(str(interaction.user.id))
            targets = advisor.infer_default_targets(user.get("town_hall"), role.value)
            if targets:
                await advisor.save_user_patch(
                    str(interaction.user.id),
                    lambda user: user.setdefault("targets", {}).update({k: user.setdefault("targets", {}).get(k, v) for k, v in targets.items()}),
                )
            await interaction.response.send_message(
                f"â Upgrade advisor role set to **{role.name}**.",
                ephemeral=True,
            )

        @self.tree.command(name="syncupgrades", description="Sync heroes, troops, spells, and pets from your linked Clash account")
        async def syncupgrades(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                user = await advisor.sync_player(str(interaction.user.id))
            except ValueError as exc:
                await interaction.followup.send(f"â {exc}", ephemeral=True)
                return

            synced_count = len(user.get("synced_levels", {}))
            progress = advisor.build_progress_snapshot(user)
            embed = discord.Embed(title="â Upgrade Sync Complete", color=0x2ECC71)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="Synced items", value=str(synced_count), inline=True)
            embed.add_field(name="Tracked progress", value=f"{progress['bar']} {progress['percent']}%", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

        @self.tree.command(name="trackupgrade", description="Track a manual item level or override a target")
        @app_commands.describe(item="Item key to track", current_level="Your current level", target_level="Optional advisor target override")
        async def trackupgrade(interaction: discord.Interaction, item: str, current_level: int, target_level: int | None = None):
            item = item.strip().lower()
            if item not in ITEMS:
                await interaction.response.send_message("â Unknown item key. Use autocomplete or a valid advisor item.", ephemeral=True)
                return
            if current_level < 0:
                await interaction.response.send_message("â Current level cannot be negative.", ephemeral=True)
                return
            if target_level is not None and target_level < current_level:
                await interaction.response.send_message("â Target level cannot be lower than your current level.", ephemeral=True)
                return

            def patch(user: dict[str, Any]):
                user.setdefault("manual_levels", {})[item] = int(current_level)
                if target_level is not None:
                    user.setdefault("targets", {})[item] = int(target_level)

            await advisor.save_user_patch(str(interaction.user.id), patch)
            user = await advisor.get_user_store(str(interaction.user.id))
            effective_target = advisor.get_effective_targets(user).get(item, target_level or current_level)
            await interaction.response.send_message(
                f"â Tracking **{ITEMS[item].label}** at level **{current_level}** with target **{effective_target}**.",
                ephemeral=True,
            )

        @trackupgrade.autocomplete("item")
        async def trackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
            current = current.lower()
            return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

        @self.tree.command(name="untrackupgrade", description="Remove a manually tracked item or target override")
        @app_commands.describe(item="Item key to remove")
        async def untrackupgrade(interaction: discord.Interaction, item: str):
            item = item.strip().lower()
            if item not in ITEMS:
                await interaction.response.send_message("â Unknown item key.", ephemeral=True)
                return

            def patch(user: dict[str, Any]):
                user.setdefault("manual_levels", {}).pop(item, None)
                user.setdefault("targets", {}).pop(item, None)

            await advisor.save_user_patch(str(interaction.user.id), patch)
            await interaction.response.send_message(
                f"â Removed manual tracking for **{ITEMS[item].label}**.",
                ephemeral=True,
            )

        @untrackupgrade.autocomplete("item")
        async def untrackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
            current = current.lower()
            return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

        @self.tree.command(name="nextupgrade", description="See your top recommended next upgrades")
        @app_commands.describe(count="How many recommendations to show (1-10)")
        async def nextupgrade(interaction: discord.Interaction, count: int = 5):
            await interaction.response.defer(ephemeral=True)
            user = await advisor.get_user_store(str(interaction.user.id))
            if not user.get("synced_levels") and not user.get("manual_levels"):
                await interaction.followup.send(
                    "â No upgrade data found yet. Run `/syncupgrades` first, then optionally add manual buildings with `/trackupgrade`.",
                    ephemeral=True,
                )
                return

            recs = advisor.build_recommendations(user, count=count)
            if not recs:
                await interaction.followup.send(
                    "â You are at or above all current advisor targets. Add more manual targets or raise your standards.",
                    ephemeral=True,
                )
                return

            progress = advisor.build_progress_snapshot(user)
            embed = discord.Embed(title="ð§  Upgrade Advisor", color=0x5865F2)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="Recommended next upgrades", value=advisor.format_top_block(recs), inline=False)
            embed.add_field(name="Progress", value=f"{progress['bar']} {progress['percent']}% ({progress['done']}/{progress['tracked']})", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)

        @self.tree.command(name="upgradeprogress", description="View your current advisor progress")
        async def upgradeprogress(interaction: discord.Interaction):
            user = await advisor.get_user_store(str(interaction.user.id))
            progress = advisor.build_progress_snapshot(user)
            embed = discord.Embed(title="ð Upgrade Progress", color=0x3498DB)
            embed.description = advisor.profile_summary(user)
            embed.add_field(name="Progress", value=f"{progress['bar']} {progress['percent']}%", inline=False)
            embed.add_field(name="Tracked goals", value=f"{progress['done']} / {progress['tracked']}", inline=True)
            embed.add_field(name="Manual items", value=str(len(user.get('manual_levels', {}))), inline=True)
            embed.add_field(name="Synced items", value=str(len(user.get('synced_levels', {}))), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)


def register_upgrade_advisor(tree: app_commands.CommandTree, deps: dict[str, Any]) -> UpgradeAdvisor:
    advisor = UpgradeAdvisor(tree, deps)
    advisor.register()
    return advisor