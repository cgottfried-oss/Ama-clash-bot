from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

ITEM_ICON_ASSET_MAP = {}
ITEM_ICON_NAME_ALIASES = {}

def asset_to_data_uri(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def normalize_icon_name(name: str) -> str:
    return (
        str(name or "")
        .strip()
        .lower()
        .replace("&", " and ")
        .replace(".", "")
        .replace("'", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_icon_uri(row: dict[str, Any], assets_dir: str | Path) -> str | None:
    assets_dir = Path(assets_dir)
    icons_dir = assets_dir / "icons"

    key = str(row.get("key") or "").strip()
    name = str(row.get("name") or "").strip()

    candidates: list[str] = []

    if key:
        candidates.append(ITEM_ICON_ASSET_MAP.get(key, key))

    alias = ITEM_ICON_NAME_ALIASES.get(name)
    if alias:
        candidates.append(alias)

    if name:
        candidates.append(normalize_icon_name(name))

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        for ext in (".png", ".webp", ".jpg", ".jpeg"):
            uri = asset_to_data_uri(icons_dir / f"{candidate}{ext}")
            if uri:
                return uri

    return None
