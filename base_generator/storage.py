from __future__ import annotations

from datetime import datetime, timezone

BASES_FILE = "saved_bases.json"

async def load_saved_bases(safe_load_json, data_dir: str) -> list[dict]:
    path = f"{data_dir}/{BASES_FILE}"
    data = await safe_load_json(path)
    return data if isinstance(data, list) else []

async def save_base_entry(
    safe_load_json,
    safe_save_json,
    data_dir: str,
    *,
    user_id: int,
    name: str,
    townhall: int,
    style: str,
    anti_meta: str,
    symmetry: str,
    copy_link: str,
    notes: str | None = None,
) -> dict:
    path = f"{data_dir}/{BASES_FILE}"
    entries = await load_saved_bases(safe_load_json, data_dir)

    entry = {
        "id": len(entries) + 1,
        "user_id": str(user_id),
        "name": name,
        "townhall": townhall,
        "style": style,
        "anti_meta": anti_meta,
        "symmetry": symmetry,
        "copy_link": copy_link,
        "notes": notes or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    entries.append(entry)
    await safe_save_json(path, entries)
    return entry

async def search_saved_bases(
    safe_load_json,
    data_dir: str,
    *,
    townhall: int | None = None,
    anti_meta: str | None = None,
    style: str | None = None,
):
    entries = await load_saved_bases(safe_load_json, data_dir)
    results = []

    for entry in entries:
        if townhall and int(entry.get("townhall", 0)) != int(townhall):
            continue
        if anti_meta and entry.get("anti_meta") != anti_meta:
            continue
        if style and entry.get("style") != style:
            continue
        results.append(entry)

    return sorted(results, key=lambda e: e.get("created_at", ""), reverse=True)
