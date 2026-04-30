from __future__ import annotations

import re
from typing import Any


def normalize_api_item_key(name: Any) -> str:
    """Normalize Clash API item names into internal snake_case keys."""
    raw = str(name or "").strip().lower()
    if not raw:
        return ""

    compact = re.sub(r"[^a-z0-9]+", "", raw)
    if compact in {"lassi", "pekka"}:
        return compact

    normalized = raw.replace("&", " and ")
    normalized = normalized.replace(".", "")
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def resolve_api_item_key(
    name: Any,
    section: str = "",
    *,
    autosync_name_map: dict[str, str] | None = None,
    items: dict | None = None,
) -> str | None:
    """Resolve a Clash API item name into an internal key, with debug logging.

    autosync_name_map/items are optional for backwards compatibility with older
    call sites. When omitted, they are loaded lazily from advisor modules.
    """
    if autosync_name_map is None:
        from advisor.autosync_mappings import AUTOSYNC_NAME_MAP
        autosync_name_map = AUTOSYNC_NAME_MAP

    if items is None:
        from advisor.items import ITEMS
        items = ITEMS

    raw_name = str(name or "").strip()
    if not raw_name:
        return None

    explicit = autosync_name_map.get(raw_name)
    if explicit:
        return explicit

    normalized = normalize_api_item_key(raw_name)
    if normalized in items:
        print(f"[AUTOSYNC MAP FALLBACK] {section or 'unknown'}: {raw_name!r} -> {normalized!r}")
        return normalized

    print(f"[AUTOSYNC UNMAPPED] {section or 'unknown'}: {raw_name!r} normalized={normalized!r}")
    return None
