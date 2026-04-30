from __future__ import annotations

from typing import Any

from advisor.autosync_mappings import AUTOSYNC_NAME_MAP
from advisor.helpers import normalize_api_item_key
from advisor.items import ITEMS


SIEGE_NAMES = {
    "Wall Wrecker",
    "Battle Blimp",
    "Stone Slammer",
    "Siege Barracks",
    "Log Launcher",
    "Flame Flinger",
    "Battle Drill",
    "Troop Launcher",
}

TEMPORARY_TROOP_NAMES = {
    "Baby Dragon Clone",
    "Barbarian Kicker",
    "Broom Witch",
    "C.O.O.K.I.E",
    "Cookie",
    "Giant Skeleton",
    "Hog Wizard",
    "Ice Minion",
    "Lavaloon",
    "Party Wizard",
    "Ram Rider",
    "Royal Ghost",
    "Sneaky Archer",
}

PERMANENT_TROOP_KEYS = {
    "barbarian", "archer", "giant", "goblin", "wall_breaker", "balloons", "wizard", "healers", "dragons", "pekka",
    "baby_dragon", "miners", "electro_dragon", "yeti", "dragon_rider", "electro_titan", "root_rider", "thrower",
    "meteor_golem", "apprentice_warden", "minion", "hog_rider", "valkyrie", "golem", "witch", "lava_hound", "bowler",
    "ice_golem", "headhunter", "druid", "furnace", "wall_wrecker", "battle_blimp", "stone_slammer", "siege_barracks",
    "log_launcher", "flame_flinger", "battle_drill", "troop_launcher",
}


def resolve_progress_key(name: Any) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""

    mapped = AUTOSYNC_NAME_MAP.get(raw)
    if mapped:
        return mapped

    normalized = normalize_api_item_key(raw)
    if normalized in ITEMS:
        return normalized

    return normalized


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _entry_to_row(entry: dict[str, Any]) -> dict[str, Any]:
    name = str(entry.get("name") or "Unknown")
    level = _safe_int(entry.get("level"), 0)
    max_level = _safe_int(entry.get("maxLevel"), 0)
    key = resolve_progress_key(name)
    village = str(entry.get("village") or entry.get("villageName") or "home").lower()

    return {
        "name": name,
        "key": key,
        "level": level,
        "max_level": max_level,
        "village": village,
        "is_max": bool(max_level and level >= max_level),
    }


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (not bool(r.get("is_max")), str(r.get("name", "")).lower()))


def _is_super_troop(row: dict[str, Any]) -> bool:
    return str(row.get("name", "")).strip().lower().startswith("super ")


def _is_temporary_troop(row: dict[str, Any]) -> bool:
    return str(row.get("name", "")).strip() in TEMPORARY_TROOP_NAMES


def _is_permanent_home_troop(row: dict[str, Any]) -> bool:
    key = str(row.get("key") or "").strip()
    village = str(row.get("village") or "home").lower()
    return key in PERMANENT_TROOP_KEYS and village in {"home", "home village", ""}


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("key") or row.get("name") or "").strip().lower()
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            continue

        row_permanent = _is_permanent_home_troop(row)
        existing_permanent = _is_permanent_home_troop(existing)

        if row_permanent and not existing_permanent:
            by_key[key] = row
        elif row_permanent == existing_permanent and int(row.get("level", 0) or 0) > int(existing.get("level", 0) or 0):
            by_key[key] = row
    return list(by_key.values())


def build_current_progress_data(player: dict[str, Any]) -> dict[str, Any]:
    heroes = [_entry_to_row(e) for e in player.get("heroes", []) or []]
    pet_entries = player.get("heroPets") or player.get("pets") or []
    pets = [_entry_to_row(e) for e in pet_entries]
    spells = [_entry_to_row(e) for e in player.get("spells", []) or []]

    troop_rows = [_entry_to_row(e) for e in player.get("troops", []) or []]
    troop_rows = [r for r in troop_rows if not _is_super_troop(r) and not _is_temporary_troop(r)]
    troop_rows = [r for r in troop_rows if _is_permanent_home_troop(r)]
    troop_rows = _dedupe_rows(troop_rows)

    siege = [r for r in troop_rows if r.get("name") in SIEGE_NAMES]
    troops = [r for r in troop_rows if r.get("name") not in SIEGE_NAMES]

    achievements = player.get("achievements", []) or []

    def achievement_value(name: str) -> int:
        for row in achievements:
            if str(row.get("name", "")).lower() == name.lower():
                return _safe_int(row.get("value"), 0)
        return 0

    labels = player.get("labels", []) or []

    return {
        "player": {
            "name": player.get("name", "Unknown"),
            "tag": player.get("tag", ""),
            "town_hall": player.get("townHallLevel"),
            "exp_level": player.get("expLevel"),
            "league": (player.get("league") or {}).get("name", "Unranked"),
            "trophies": player.get("trophies", 0),
            "clan": (player.get("clan") or {}).get("name", "No Clan"),
            "labels": [label.get("name") for label in labels if isinstance(label, dict)],
        },
        "sections": {
            "Heroes": _sort_rows(heroes),
            "Pets": _sort_rows(pets),
            "Troops": _sort_rows(troops),
            "Spells": _sort_rows(spells),
            "Siege Machines": _sort_rows(siege),
        },
        "stats": {
            "Attack Wins": player.get("attackWins", 0),
            "Defense Wins": player.get("defenseWins", 0),
            "War Stars": player.get("warStars", 0),
            "Donations": player.get("donations", 0),
            "Received": player.get("donationsReceived", 0),
            "Gold Grab": achievement_value("Gold Grab"),
            "Elixir Escapade": achievement_value("Elixir Escapade"),
            "Heroic Heist": achievement_value("Heroic Heist"),
            "Games Champion": achievement_value("Games Champion"),
        },
    }
