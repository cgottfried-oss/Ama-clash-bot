from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from clash_mmo.game.core.profiles import ensure_player_profile


MMO_FILE_NAME = "mmo_state.json"

LEGACY_FILES = {
    "profiles": "phase5_profiles.json",
    "seasons": "phase5_seasons.json",
    "territories": "phase5_territories.json",
    "raids": "phase5_raids.json",
    "marketplace": "phase5_marketplace.json",
    "events": "phase5_ai_events.json",
}


def mmo_file(ctx) -> str:
    data_dir = getattr(ctx, "DATA_DIR", "/app/data")
    return str(Path(data_dir) / MMO_FILE_NAME)


def legacy_file(ctx, key: str) -> str:
    data_dir = getattr(ctx, "DATA_DIR", "/app/data")
    return str(Path(data_dir) / LEGACY_FILES[key])


def default_mmo_state() -> dict[str, Any]:
    return {
        "version": 1,
        "players": {},
        "seasons": {},
        "territories": {},
        "raids": {},
        "marketplace": {"listings": [], "black_market": {}},
        "events": {"events": []},
        "meta": {"created_at": int(time.time())},
    }


def normalize_mmo_state(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    base = default_mmo_state()
    for key, value in base.items():
        data.setdefault(key, value)

    if not isinstance(data.get("players"), dict):
        data["players"] = {}
    if not isinstance(data.get("seasons"), dict):
        data["seasons"] = {}
    if not isinstance(data.get("territories"), dict):
        data["territories"] = {}
    if not isinstance(data.get("raids"), dict):
        data["raids"] = {}
    if not isinstance(data.get("marketplace"), dict):
        data["marketplace"] = {"listings": [], "black_market": {}}
    if not isinstance(data.get("events"), dict):
        data["events"] = {"events": []}

    data["marketplace"].setdefault("listings", [])
    data["marketplace"].setdefault("black_market", {})
    data["events"].setdefault("events", [])
    data.setdefault("meta", {})
    data["meta"].setdefault("updated_at", int(time.time()))
    return data


async def load_mmo_state(ctx) -> dict[str, Any]:
    data = await ctx.safe_load_json(mmo_file(ctx))
    return normalize_mmo_state(data)


async def update_mmo_state(ctx, update_func: Callable[[dict[str, Any]], dict[str, Any] | None]):
    def _update(data):
        data = normalize_mmo_state(data)
        result = update_func(data)
        if result is not None:
            data = result
        data = normalize_mmo_state(data)
        data["meta"]["updated_at"] = int(time.time())
        return data

    return await ctx.update_json_file(mmo_file(ctx), _update)


async def ensure_mmo_player(ctx, user_id: str, name: str) -> dict[str, Any]:
    user_id = str(user_id)

    def _update(data):
        ensure_player_profile(data, user_id, name)
        return data

    await update_mmo_state(ctx, _update)
    data = await load_mmo_state(ctx)
    return data["players"][user_id]


async def migrate_legacy_phase5_files(ctx) -> None:
    profiles = await ctx.safe_load_json(legacy_file(ctx, "profiles"))
    seasons = await ctx.safe_load_json(legacy_file(ctx, "seasons"))
    territories = await ctx.safe_load_json(legacy_file(ctx, "territories"))
    raids = await ctx.safe_load_json(legacy_file(ctx, "raids"))
    marketplace = await ctx.safe_load_json(legacy_file(ctx, "marketplace"))
    events = await ctx.safe_load_json(legacy_file(ctx, "events"))

    def _update(data):
        if isinstance(profiles, dict):
            for uid, profile in (profiles.get("players") or {}).items():
                data["players"].setdefault(str(uid), profile)

        if isinstance(seasons, dict):
            source = seasons.get("seasons", seasons)
            if isinstance(source, dict):
                for key, value in source.items():
                    data["seasons"].setdefault(key, value)

        if isinstance(territories, dict):
            source = territories.get("territories", territories)
            if isinstance(source, dict):
                for key, value in source.items():
                    data["territories"].setdefault(key, value)

        if isinstance(raids, dict):
            for key, value in raids.items():
                data["raids"].setdefault(key, value)

        if isinstance(marketplace, dict):
            listings = data["marketplace"].setdefault("listings", [])
            for listing in marketplace.get("listings", []):
                if listing not in listings:
                    listings.append(listing)
            if "black_market" in marketplace:
                data["marketplace"].setdefault("black_market", marketplace["black_market"])

        if isinstance(events, dict):
            active_events = data["events"].setdefault("events", [])
            for event in events.get("events", []):
                if event not in active_events:
                    active_events.append(event)
            if "latest_event" in events:
                data["events"].setdefault("latest_event", events["latest_event"])

        data["meta"]["legacy_mmo_migrated"] = True
        return data

    await update_mmo_state(ctx, _update)
