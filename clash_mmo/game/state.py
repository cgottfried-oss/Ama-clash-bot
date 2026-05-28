from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from clash_mmo.game.core.profiles import ensure_player_profile


MMO_FILE_NAME = "mmo_state.json"


def mmo_file(ctx) -> str:
    data_dir = getattr(ctx, "DATA_DIR", "/app/data")
    return str(Path(data_dir) / MMO_FILE_NAME)


def default_mmo_state() -> dict[str, Any]:
    return {
        "version": 1,
        "players": {},
        "seasons": {},
        "territories": {},
        "raids": {},
        "marketplace": {
            "listings": [],
            "listing_history": [],
            "trades": [],
            "trade_logs": [],
            "stats": {},
            "gold_sunk": 0,
            "black_market": {},
        },
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
        data["marketplace"] = {
            "listings": [],
            "listing_history": [],
            "trades": [],
            "trade_logs": [],
            "stats": {},
            "gold_sunk": 0,
            "black_market": {},
        }
    if not isinstance(data.get("events"), dict):
        data["events"] = {"events": []}

    data["marketplace"].setdefault("listings", [])
    data["marketplace"].setdefault("listing_history", [])
    data["marketplace"].setdefault("trades", [])
    data["marketplace"].setdefault("trade_logs", [])
    data["marketplace"].setdefault("stats", {})
    data["marketplace"].setdefault("gold_sunk", 0)
    data["marketplace"].setdefault("black_market", {})
    data["events"].setdefault("events", [])
    data.setdefault("meta", {})
    data["meta"].setdefault("updated_at", int(time.time()))
    return data


async def load_mmo_state(ctx) -> dict[str, Any]:
    data = await ctx.safe_load_json(mmo_file(ctx))
    return normalize_mmo_state(data)


async def reset_mmo_state(ctx) -> dict[str, Any]:
    data = default_mmo_state()
    await ctx.safe_save_json(mmo_file(ctx), data)
    return data


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
