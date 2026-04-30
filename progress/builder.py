from __future__ import annotations

import re
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


def _entry_to_row(entry: dict[str, Any]) -> dict[str, Any]:
    name = str(entry.get("name") or "Unknown")
    level = int(entry.get("level") or 0)
    max_level = int(entry.get("maxLevel") or 0)
    key = resolve_progress_key(name)

    return {
        "name": name,
        "key": key,
        "level": level,
        "max_level": max_level,
        "is_max": bool(max_level and level >= max_level),
    }


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            not bool(r.get("is_max")),
            str(r.get("name", "")).lower(),
        ),
    )


def build_current_progress_data(player: dict[str, Any]) -> dict[str, Any]:
    heroes = [_entry_to_row(e) for e in player.get("heroes", []) or []]
    pets = [_entry_to_row(e) for e in player.get("heroPets", []) or []]
    spells = [_entry_to_row(e) for e in player.get("spells", []) or []]

    troop_rows = [_entry_to_row(e) for e in player.get("troops", []) or []]
    siege = [r for r in troop_rows if r.get("name") in SIEGE_NAMES]
    troops = [r for r in troop_rows if r.get("name") not in SIEGE_NAMES]

    achievements = player.get("achievements", []) or []

    def achievement_value(name: str) -> int:
        for row in achievements:
            if str(row.get("name", "")).lower() == name.lower():
                try:
                    return int(row.get("value") or 0)
                except (TypeError, ValueError):
                    return 0
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
