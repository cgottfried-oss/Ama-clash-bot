from __future__ import annotations

import re

AUTOSYNC_NAME_MAP: dict[str, str] = {}

ITEMS: set[str] = set()


def normalize_api_item_key(name: object) -> str:
    value = str(name or "").strip().lower()
    value = value.replace("&", " and ")
    value = value.replace(".", "")
    value = value.replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value