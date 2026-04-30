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

PET_NAMES = {
    "L.A.S.S.I",
    "Lassi",
    "Mighty Yak",
    "Electro Owl",
    "Unicorn",
    "Phoenix",
    "Poison Lizard",
    "Diggy",
    "Frosty",
    "Spirit Fox",
    "Angry Jelly",
    "Sneezy",
    "Greedy Raven",
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

HERO_ORDER = ["barbarian_king", "archer_queen", "minion_prince", "grand_warden", "royal_champion", "dragon_duke"]
PET_ORDER = ["lassi", "mighty_yak", "electro_owl", "unicorn", "phoenix", "poison_lizard", "diggy", "frosty", "spirit_fox", "angry_jelly", "sneezy", "greedy_raven"]
PET_KEYS = set(PET_ORDER)
TROOP_ORDER = ["barbarian", "archer", "giant", "goblin", "wall_breaker", "balloons", "wizard", "healers", "dragons", "pekka", "baby_dragon", "miners", "electro_dragon", "yeti", "dragon_rider", "electro_titan", "root_rider", "thrower", "meteor_golem", "apprentice_warden", "minion", "hog_rider", "valkyrie", "golem", "witch", "lava_hound", "bowler", "ice_golem", "headhunter", "druid", "furnace"]
SPELL_ORDER = ["lightning_spell", "healing_spell", "rage_spell", "poison_spell", "earthquake_spell", "jump_spell", "freeze_spell", "haste_spell", "skeleton_spell", "clone_spell", "bat_spell", "invisibility_spell", "recall_spell", "overgrowth_spell", "ice_block_spell", "revive_spell", "totem_spell"]
SIEGE_ORDER = ["wall_wrecker", "battle_blimp", "stone_slammer", "siege_barracks", "log_launcher", "flame_flinger", "battle_drill", "troop_launcher"]

ORDER_MAPS = {
    "Heroes": {key: idx for idx, key in enumerate(HERO_ORDER)},
    "Pets": {key: idx for idx, key in enumerate(PET_ORDER)},
    "Troops": {key: idx for idx, key in enumerate(TROOP_ORDER)},
    "Spells": {key: idx for idx, key in enumerate(SPELL_ORDER)},
    "Siege Machines": {key: idx for idx, key in enumerate(SIEGE_ORDER)},
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
    return {"name": name, "key": key, "level": level, "max_level": max_level, "village": village, "is_max": bool(max_level and level >= max_level)}


def _sort_rows(rows: list[dict[str, Any]], section: str) -> list[dict[str, Any]]:
    order_map = ORDER_MAPS.get(section, {})
    return sorted(rows, key=lambda r: (order_map.get(str(r.get("key") or ""), 999), str(r.get("name", "")).lower()))


def _is_super_troop(row: dict[str, Any]) -> bool:
    return str(row.get("name", "")).strip().lower().startswith("super ")


def _is_temporary_troop(row: dict[str, Any]) -> bool:
    return str(row.get("name", "")).strip() in TEMPORARY_TROOP_NAMES


def _is_pet(row: dict[str, Any]) -> bool:
    return str(row.get("name", "")).strip() in PET_NAMES or str(row.get("key", "")).strip() in PET_KEYS


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
        row_permanent = _is_permanent_home_troop(row) or _is_pet(row)
        existing_permanent = _is_permanent_home_troop(existing) or _is_pet(existing)
        if row_permanent and not existing_permanent:
            by_key[key] = row
        elif row_permanent == existing_permanent and int(row.get("level", 0) or 0) > int(existing.get("level", 0) or 0):
            by_key[key] = row
    return list(by_key.values())


def _summary_row(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    maxed = sum(1 for row in rows if bool(row.get("is_max")))
    percent = round((maxed / total) * 100) if total else 0
    return {"label": label, "maxed": maxed, "total": total, "percent": percent, "value": f"{maxed}/{total}"}


def _build_snapshot_summary(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = [
        _summary_row("Heroes Maxed", sections.get("Heroes", [])),
        _summary_row("Pets Maxed", sections.get("Pets", [])),
        _summary_row("Troops Maxed", sections.get("Troops", [])),
        _summary_row("Spells Maxed", sections.get("Spells", [])),
        _summary_row("Siege Maxed", sections.get("Siege Machines", [])),
    ]
    total_maxed = sum(row["maxed"] for row in rows)
    total_items = sum(row["total"] for row in rows)
    overall = round((total_maxed / total_items) * 100) if total_items else 0
    rows.append({"label": "Current Snapshot", "maxed": total_maxed, "total": total_items, "percent": overall, "value": f"{overall}%"})
    return rows


def build_current_progress_data(player: dict[str, Any]) -> dict[str, Any]:
    heroes = [_entry_to_row(e) for e in player.get("heroes", []) or []]
    spells = [_entry_to_row(e) for e in player.get("spells", []) or []]
    troop_rows_all = [_entry_to_row(e) for e in player.get("troops", []) or []]

    pet_entries = player.get("heroPets") or player.get("pets") or []
    explicit_pet_rows = [_entry_to_row(e) for e in pet_entries]
    troop_pet_rows = [r for r in troop_rows_all if _is_pet(r)]
    pets = _dedupe_rows(explicit_pet_rows + troop_pet_rows)

    troop_rows = [r for r in troop_rows_all if not _is_pet(r) and not _is_super_troop(r) and not _is_temporary_troop(r) and _is_permanent_home_troop(r)]
    troop_rows = _dedupe_rows(troop_rows)

    siege = [r for r in troop_rows if r.get("name") in SIEGE_NAMES]
    troops = [r for r in troop_rows if r.get("name") not in SIEGE_NAMES]

    sections = {
        "Heroes": _sort_rows(heroes, "Heroes"),
        "Pets": _sort_rows(pets, "Pets"),
        "Troops": _sort_rows(troops, "Troops"),
        "Spells": _sort_rows(spells, "Spells"),
        "Siege Machines": _sort_rows(siege, "Siege Machines"),
    }

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
        "sections": sections,
        "summary": _build_snapshot_summary(sections),
    }
