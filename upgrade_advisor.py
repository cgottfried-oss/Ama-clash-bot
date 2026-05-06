from __future__ import annotations

import asyncio
import os
import re
import base64
import io
import html
import json
import mimetypes
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from th_caps import TH_CAPS, get_item_cap, get_category_caps, normalize_cap_entry, get_all_cap_items, get_cap_category_group
from reward_config import mark_reward

import discord
from renderers.advisor_renderer import render_advisor_card_to_file

from discord import app_commands
from advisor.account_completion_rendering import _build_compact_accountcompletion_card_html
from advisor.icon_mappings import ITEM_ICON_ASSET_MAP, ITEM_ICON_NAME_ALIASES
from advisor.autosync_mappings import AUTOSYNC_NAME_MAP
from advisor.account_only import apply_account_only_items
from advisor.helpers import normalize_api_item_key, resolve_api_item_key
from advisor.items import ItemMeta, ITEMS
from advisor.targets import RECOMMENDED_TARGETS_BY_TH
from advisor.rendering import render_html_card_to_file as render_advisor_html_card_to_file
from advisor.upgradeprogress_rendering import build_upgradeprogress_card_html
from advisor.nextupgrade_rendering import build_nextupgrade_card_html
from advisor.sync_rendering import build_syncupgrades_card_html
from advisor.upgrade_cards import (
    base_upgrade_card_html,
    metric_row,
    status_note,
    summary_card,
    townhall_summary_card,
)
from advisor.constants import (
    CHECK,
    BRAIN,
    CHART,
    FULL,
    EMPTY,
    LANE_EMOJIS,
    CATEGORY_EMOJIS,
    TIMING_EMOJIS,
    MODE_EMOJIS,
    MODE_CATEGORY_BIAS,
    MODE_LANE_BIAS,
    ELIXIR_BUILDING_KEYS,
    GOLD_BUILDING_KEYS,
    ROLE_WEIGHTS,
    DEFAULT_ROLE,
    LANE_WEIGHTS,
    MILESTONE_PROGRESS_MARKS,
    HERO_KEYS,
)

from advisor.cap_mappings import (
    TH_CAP_NAME_MAP,
    ACCOUNT_COMPLETION_CATEGORIES,
    ACCOUNT_COMPLETION_CATEGORY_LABELS,
    RECOMMENDATION_PRIORITIES,
    ARMY_BUILDING_CAP_NAME_ALIASES,
    rebuild_th_cap_lookup,
    TH_CAP_LOOKUP_TO_KEY,
    OFFENSE_CORE_KEYS,
    BUILDER_CORE_KEYS,
    MIN_COPY_FALLBACK_COUNTS,
)

ACCOUNT_ONLY_ITEM_KEYS, TH_CAP_LOOKUP_TO_KEY = apply_account_only_items(
    th_cap_name_map=TH_CAP_NAME_MAP,
    min_copy_fallback_counts=MIN_COPY_FALLBACK_COUNTS,
    items=ITEMS,
    item_meta=ItemMeta,
    rebuild_th_cap_lookup=rebuild_th_cap_lookup,
)

TRACKABLE_CHOICES = [
    app_commands.Choice(name=f"{meta.label} ({key})", value=key)
    for key, meta in sorted(ITEMS.items(), key=lambda kv: kv[1].label.lower())
]


class UpgradeAdvisor:
    
    def _build_compact_accountcompletion_card_html(
        self,
        user: dict[str, Any],
        requested_mode: str | None = None,
        builder_idle: bool | None = None,
        lab_idle: bool | None = None,
    ) -> str:
        return _build_compact_accountcompletion_card_html(
            self,
            user,
            requested_mode=requested_mode,
            builder_idle=builder_idle,
            lab_idle=lab_idle,
        )
    
    
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
        self.assets_dir = Path(str(deps.get("assets_dir") or os.getenv("UPGRADE_ADVISOR_ASSETS_DIR") or "/app/assets")).expanduser()
        self._icon_path_cache: dict[tuple[str, str], str | None] = {}
        self._asset_index: dict[str, str] | None = None

    def default_user_root(self) -> dict[str, Any]:
        return {
            "role": DEFAULT_ROLE,
            "active_player_tag": None,
            "accounts": {},
        }

    def default_account_store(self) -> dict[str, Any]:
        return {
            "manual_levels": {},
            "manual_copy_levels": {},
            "targets": {},
            "synced_levels": {},
            "synced_max_levels": {},
            "advisor_mode": "auto",
            "player_tag": None,
            "player_name": None,
            "town_hall": None,
            "town_hall_started_at": None,
            "last_synced_at": None,
            "progress_history": [],
            "advisor_economy": {
                "coins": 0,
                "efficiency_score": 0,
                "followed_paths": 0,
                "missed_paths": 0,
                "last_recommendations": [],
                "last_award_at": None,
            },
        }

    def migrate_user_root(self, user: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(user, dict):
            user = {}

        if "accounts" in user and isinstance(user.get("accounts"), dict):
            user.setdefault("role", DEFAULT_ROLE)
            user.setdefault("active_player_tag", None)
            for account in (user.get("accounts") or {}).values():
                if isinstance(account, dict):
                    account.setdefault("advisor_mode", "auto")
            return user

        legacy_account = self.default_account_store()
        legacy_account["manual_levels"] = dict(user.get("manual_levels", {}) or {})
        legacy_account["manual_copy_levels"] = dict(user.get("manual_copy_levels", {}) or {})
        legacy_account["targets"] = dict(user.get("targets", {}) or {})
        legacy_account["synced_levels"] = dict(user.get("synced_levels", {}) or {})
        legacy_account["synced_max_levels"] = dict(user.get("synced_max_levels", {}) or {})
        legacy_account["player_tag"] = user.get("player_tag")
        legacy_account["player_name"] = user.get("player_name")
        legacy_account["town_hall"] = user.get("town_hall")
        legacy_account["town_hall_started_at"] = user.get("town_hall_started_at")
        legacy_account["last_synced_at"] = user.get("last_synced_at")
        legacy_account["progress_history"] = list(user.get("progress_history", []) or [])

        root = self.default_user_root()
        root["role"] = user.get("role", DEFAULT_ROLE)

        player_tag = legacy_account.get("player_tag")
        has_legacy_data = any(
            [
                legacy_account["manual_levels"],
                legacy_account["manual_copy_levels"],
                legacy_account["targets"],
                legacy_account["synced_levels"],
                legacy_account["synced_max_levels"],
                legacy_account["player_name"],
                legacy_account["town_hall"],
                legacy_account["town_hall_started_at"],
                legacy_account["last_synced_at"],
                legacy_account["progress_history"],
            ]
        )
        if has_legacy_data:
            key = self.normalize_tag(player_tag) if player_tag else "legacy"
            legacy_account["player_tag"] = self.normalize_tag(player_tag) if player_tag else None
            root["accounts"][key] = legacy_account
            root["active_player_tag"] = key

        return root

    async def load_store(self) -> dict[str, Any]:
        store = await self.safe_load_json(self.store_path)
        if not isinstance(store, dict):
            store = {}
        store.setdefault("users", {})
        return store

    async def get_user_root(self, user_id: str) -> dict[str, Any]:
        store = await self.load_store()
        users = store.setdefault("users", {})
        user = users.setdefault(str(user_id), self.default_user_root())
        migrated = self.migrate_user_root(user)
        users[str(user_id)] = migrated
        return migrated

    def get_account_from_root(self, user_root: dict[str, Any], player_tag: str | None = None) -> dict[str, Any]:
        accounts = user_root.setdefault("accounts", {})
        target_tag = self.normalize_tag(player_tag) if player_tag else user_root.get("active_player_tag")
        if not target_tag or target_tag not in accounts:
            return self.default_account_store()
        account = accounts.get(target_tag) or self.default_account_store()
        return account

    async def get_user_store(self, user_id: str, player_tag: str | None = None) -> dict[str, Any]:
        root = await self.get_user_root(user_id)
        account = dict(self.get_account_from_root(root, player_tag))
        account["role"] = root.get("role", DEFAULT_ROLE)
        account["active_player_tag"] = root.get("active_player_tag")
        return account

    async def save_user_patch(self, user_id: str, patch_fn: Callable[[dict[str, Any]], None], player_tag: str | None = None) -> dict[str, Any]:
        normalized_player_tag = self.normalize_tag(player_tag) if player_tag else None

        def _update(store: dict[str, Any]):
            if not isinstance(store, dict):
                store = {}
            users = store.setdefault("users", {})
            existing = users.setdefault(str(user_id), self.default_user_root())
            root = self.migrate_user_root(existing)
            accounts = root.setdefault("accounts", {})
            target_tag = normalized_player_tag or root.get("active_player_tag") or "legacy"
            account = accounts.setdefault(target_tag, self.default_account_store())
            account.setdefault("player_tag", None)
            if account.get("player_tag") is None and target_tag != "legacy":
                account["player_tag"] = target_tag
            patch_fn(root, account)
            users[str(user_id)] = root
            return store

        return await self.update_json_file(self.store_path, _update)

    async def get_linked_accounts(self, discord_user_id: str) -> list[dict[str, str]]:
        linked_raw = await self.safe_load_json(self.linked_file)
        entries = linked_raw.get(str(discord_user_id), []) if isinstance(linked_raw, dict) else []
        results: list[dict[str, str]] = []
        seen: set[str] = set()

        for entry in entries:
            tag = None
            name = "Unknown"
            if isinstance(entry, str):
                tag = self.normalize_tag(entry)
            elif isinstance(entry, dict) and entry.get("tag"):
                tag = self.normalize_tag(entry["tag"])
                name = entry.get("name", "Unknown")
            if not tag or tag in seen:
                continue
            seen.add(tag)
            results.append({"tag": tag, "name": name})

        return results

    async def resolve_linked_account(self, discord_user_id: str, account_hint: str | None = None) -> dict[str, str] | None:
        linked_accounts = await self.get_linked_accounts(discord_user_id)
        if not linked_accounts:
            return None

        if account_hint:
            hint = account_hint.strip().lower()
            normalized_hint = self.normalize_tag(account_hint) if "#" in account_hint or account_hint.upper().startswith("P") else None
            for account in linked_accounts:
                if normalized_hint and account["tag"] == normalized_hint:
                    return account
                if hint == account["name"].lower() or hint in account["name"].lower() or hint in account["tag"].lower():
                    return account

        root = await self.get_user_root(discord_user_id)
        active_tag = root.get("active_player_tag")
        if active_tag:
            for account in linked_accounts:
                if account["tag"] == active_tag:
                    return account

        return linked_accounts[0]

    async def fetch_player_data(self, tag: str) -> dict[str, Any] | None:
        normalized_tag = self.normalize_tag(tag)
        encoded_tag = normalized_tag.replace("#", "%23")
        url = f"{self.clash_api_base}/players/{encoded_tag}"
        return await self.get_cached_or_fetch(f"player_{normalized_tag}", url, ttl=300)

    def get_th_cap_target(self, town_hall: int | None, item_key: str) -> int | None:
        if not town_hall or item_key not in ITEMS:
            return None
        category_and_name = TH_CAP_NAME_MAP.get(item_key)
        if not category_and_name:
            return None
        category, cap_name = category_and_name
        cap = get_item_cap(int(town_hall), category, cap_name, None)
        if cap is None:
            return None
        if isinstance(cap, dict):
            try:
                return int(normalize_cap_entry(cap).get("max_level", 0))
            except (TypeError, ValueError):
                return None
        try:
            return int(cap)
        except (TypeError, ValueError):
            return None

    def infer_default_targets(self, town_hall: int | None, role: str) -> dict[str, int]:
        if not town_hall:
            return {}
        baseline = RECOMMENDED_TARGETS_BY_TH.get(int(town_hall), {})
        targets = dict(baseline)

        if role == "attacker":
            for item in ("army_camp", "laboratory", "clan_castle"):
                if item in targets:
                    targets[item] += 1
        elif role == "farmer":
            for item in ("gold_mine", "elixir_collector", "dark_elixir_drill", "gold_storage", "elixir_storage"):
                targets[item] = max(targets.get(item, 0), 1)

        # TH caps are the source of truth for which items are actually supported at
        # the player's current Town Hall. Baseline recommendations may still contain
        # legacy entries, so overwrite supported targets from TH caps and drop any
        # unsupported baseline items before returning.
        supported_targets: dict[str, int] = {}
        for item_key in TH_CAP_NAME_MAP:
            if item_key in ACCOUNT_ONLY_ITEM_KEYS:
                continue
            cap_target = self.get_th_cap_target(town_hall, item_key)
            if cap_target is not None:
                supported_targets[item_key] = cap_target

        for item_key, target in targets.items():
            if item_key in supported_targets:
                continue
            if item_key not in ITEMS:
                continue
            # Keep non-TH-cap items only when they are not part of the TH-cap model.
            # Anything in TH_CAP_NAME_MAP with no TH cap is unsupported for this TH.
            if item_key in TH_CAP_NAME_MAP:
                continue
            supported_targets[item_key] = int(target)

        return supported_targets

    def parse_player_levels(self, player: dict[str, Any]) -> tuple[int | None, str, str, dict[str, int], dict[str, int]]:
        th = player.get("townHallLevel")
        player_tag = self.normalize_tag(player.get("tag", "")) if player.get("tag") else ""
        player_name = player.get("name", "Unknown")
        levels: dict[str, int] = {}
        max_levels: dict[str, int] = {}

        for section in ("heroes", "troops", "spells", "heroPets"):
            for entry in player.get(section, []) or []:
                item_key = resolve_api_item_key(entry.get("name"), section)
                if not item_key:
                    continue
                try:
                    levels[item_key] = int(entry.get("level", 0))
                except (TypeError, ValueError):
                    continue
                try:
                    max_level = int(entry.get("maxLevel", 0))
                except (TypeError, ValueError):
                    max_level = 0
                if max_level > 0:
                    max_levels[item_key] = max_level

        return th, player_tag, player_name, levels, max_levels

    async def sync_player(self, discord_user_id: str, account_hint: str | None = None) -> dict[str, Any]:
        link = await self.resolve_linked_account(discord_user_id, account_hint)
        if not link:
            raise ValueError("You need to link a Clash account first with /link.")

        player = await self.fetch_player_data(link["tag"])
        if not player:
            raise ValueError("Could not fetch your Clash player data right now.")

        th, player_tag, player_name, synced_levels, synced_max_levels = self.parse_player_levels(player)

        sync_now = datetime.now(timezone.utc).isoformat()

        def patch(root: dict[str, Any], account: dict[str, Any]):
            role = root.get("role", DEFAULT_ROLE)
            root["active_player_tag"] = player_tag
            previous_th = account.get("town_hall")
            if account.get("town_hall_started_at") is None or (th and previous_th and int(previous_th) != int(th)) or (th and previous_th is None):
                account["town_hall_started_at"] = sync_now
            account["town_hall"] = th
            account["player_tag"] = player_tag
            account["player_name"] = player_name
            account["synced_levels"] = synced_levels
            account["synced_max_levels"] = synced_max_levels
            account["last_synced_at"] = sync_now
            account.setdefault("targets", {})
            account.setdefault("progress_history", [])
            inferred = self.infer_default_targets(th, role)
            for key, value in inferred.items():
                account["targets"].setdefault(key, value)

        await self.save_user_patch(discord_user_id, patch, player_tag=player_tag)
        user = await self.get_user_store(discord_user_id, player_tag=player_tag)
        await self.record_progress_snapshot(discord_user_id, player_tag, user)
        return await self.get_user_store(discord_user_id, player_tag=player_tag)


    def _parse_iso_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = datetime.fromisoformat(str(value))
            except Exception:
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _format_duration_short(self, delta_seconds: float) -> str:
        seconds = max(0, int(delta_seconds))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days >= 1:
            return f"{days}d {hours}h"
        if hours >= 1:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def get_town_hall_age_text(self, user: dict[str, Any]) -> str:
        started_at = self._parse_iso_datetime(user.get("town_hall_started_at"))
        if not started_at:
            return "Unknown"
        return self._format_duration_short((datetime.now(timezone.utc) - started_at).total_seconds())

    def _trim_progress_history(self, history: list[dict[str, Any]], limit: int = 90) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            ts = self._parse_iso_datetime(entry.get("timestamp"))
            if not ts:
                continue
            cleaned.append({
                "timestamp": ts.isoformat(),
                "done": int(entry.get("done", 0) or 0),
                "tracked": int(entry.get("tracked", 0) or 0),
                "percent": int(entry.get("percent", 0) or 0),
            })
        cleaned.sort(key=lambda row: row["timestamp"])
        return cleaned[-limit:]

    async def record_progress_snapshot(self, user_id: str, player_tag: str | None, user: dict[str, Any] | None = None) -> None:
        user = user or await self.get_user_store(str(user_id), player_tag=player_tag)
        progress = self.build_progress_snapshot(user)
        timestamp = self._parse_iso_datetime(user.get("last_synced_at")) or datetime.now(timezone.utc)
        new_entry = {
            "timestamp": timestamp.isoformat(),
            "done": int(progress.get("done", 0) or 0),
            "tracked": int(progress.get("tracked", 0) or 0),
            "percent": int(progress.get("percent", 0) or 0),
        }

        def patch(root: dict[str, Any], account: dict[str, Any]):
            history = self._trim_progress_history(list(account.get("progress_history", []) or []), limit=90)
            if history:
                last = history[-1]
                last_ts = self._parse_iso_datetime(last.get("timestamp"))
                same_values = (
                    int(last.get("done", -1)) == new_entry["done"]
                    and int(last.get("tracked", -1)) == new_entry["tracked"]
                    and int(last.get("percent", -1)) == new_entry["percent"]
                )
                if same_values and last_ts and abs((timestamp - last_ts).total_seconds()) < 43200:
                    return
            history.append(new_entry)
            account["progress_history"] = self._trim_progress_history(history, limit=90)

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)

    def get_progress_velocity(self, user: dict[str, Any]) -> dict[str, Any]:
        history = self._trim_progress_history(list(user.get("progress_history", []) or []), limit=90)
        if len(history) < 2:
            return {"points_per_day": 0.0, "percent_per_day": 0.0, "days_to_target": None, "rating": "Unrated"}
        first = history[0]
        last = history[-1]
        first_ts = self._parse_iso_datetime(first.get("timestamp"))
        last_ts = self._parse_iso_datetime(last.get("timestamp"))
        if not first_ts or not last_ts or last_ts <= first_ts:
            return {"points_per_day": 0.0, "percent_per_day": 0.0, "days_to_target": None, "rating": "Unrated"}
        elapsed_days = max((last_ts - first_ts).total_seconds() / 86400.0, 1 / 24)
        done_gain = max(0, int(last.get("done", 0) or 0) - int(first.get("done", 0) or 0))
        percent_gain = max(0.0, float(last.get("percent", 0) or 0) - float(first.get("percent", 0) or 0))
        points_per_day = done_gain / elapsed_days
        percent_per_day = percent_gain / elapsed_days
        remaining_points = max(0, int(last.get("tracked", 0) or 0) - int(last.get("done", 0) or 0))
        days_to_target = (remaining_points / points_per_day) if points_per_day > 0 else None

        if points_per_day >= 2.0 or percent_per_day >= 1.25:
            rating = "Elite"
        elif points_per_day >= 1.0 or percent_per_day >= 0.75:
            rating = "Strong"
        elif points_per_day >= 0.35 or percent_per_day >= 0.25:
            rating = "Steady"
        elif done_gain > 0:
            rating = "Slow burn"
        else:
            rating = "Idle"

        return {
            "points_per_day": round(points_per_day, 2),
            "percent_per_day": round(percent_per_day, 2),
            "days_to_target": round(days_to_target, 1) if days_to_target is not None else None,
            "rating": rating,
            "samples": len(history),
        }

    def build_velocity_summary(self, user: dict[str, Any]) -> str:
        velocity = self.get_progress_velocity(user)
        eta = velocity.get("days_to_target")
        eta_text = f"~{eta} days to finish targets" if eta is not None else "ETA needs more sync history"
        return (
            f"📈 **Progress/day:** {velocity.get('points_per_day', 0):.2f} goals · {velocity.get('percent_per_day', 0):.2f}%\n"
            f"🏁 **ETA to target:** {eta_text}\n"
            f"⭐ **Player efficiency rating:** {velocity.get('rating', 'Unrated')}"
        )

    def get_effective_levels(self, user: dict[str, Any]) -> dict[str, int]:
        effective = {}
        effective.update(user.get("synced_levels", {}))
        effective.update(user.get("manual_levels", {}))
        return {k: int(v) for k, v in effective.items() if k in ITEMS}

    def get_manual_copy_levels(self, user: dict[str, Any]) -> dict[str, list[int]]:
        raw = user.get("manual_copy_levels") or {}
        out: dict[str, list[int]] = {}
        if not isinstance(raw, dict):
            return out
        for key, value in raw.items():
            if key not in ITEMS:
                continue
            if isinstance(value, list):
                levels: list[int] = []
                for entry in value:
                    try:
                        levels.append(max(0, int(entry)))
                    except (TypeError, ValueError):
                        continue
                out[key] = levels
        return out

    def parse_copy_level_entries(self, raw: str, *, require_counts: bool = False) -> tuple[list[int], list[str]]:
        """Parse copy levels from CSV. Supports `13,13,12` and compact `13x4,12x2`."""
        levels: list[int] = []
        errors: list[str] = []
        parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
        for part in parts:
            normalized = part.lower().replace("×", "x").replace("*", "x")
            if "x" in normalized:
                left, right = normalized.split("x", 1)
                try:
                    level = int(left.strip())
                    count = int(right.strip())
                except ValueError:
                    errors.append(f"`{part}` must look like `levelxcount`, for example `18x230`.")
                    continue
                if level < 0:
                    errors.append(f"`{part}` has a negative level.")
                    continue
                if count < 1:
                    errors.append(f"`{part}` must have a count of at least 1.")
                    continue
                levels.extend([level] * count)
            else:
                if require_counts:
                    errors.append(f"`{part}` needs a count. Use `18x230` instead of just `18`.")
                    continue
                try:
                    level = int(normalized)
                except ValueError:
                    errors.append(f"`{part}` is not a whole-number level.")
                    continue
                if level < 0:
                    errors.append(f"`{part}` has a negative level.")
                    continue
                levels.append(level)
        return levels, errors

    def summarize_copy_levels(self, levels: list[int]) -> str:
        if not levels:
            return "none"
        counts: dict[int, int] = {}
        for lvl in levels:
            counts[int(lvl)] = counts.get(int(lvl), 0) + 1
        return ", ".join(f"L{level}×{count}" for level, count in sorted(counts.items(), reverse=True))

    def _normalize_cap_lookup_key(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        for char in ("-", ".", "'", "’", "&", "/"):
            text = text.replace(char, " ")
        return " ".join(text.split())

    def _extract_copy_count_from_cap(self, cap: Any) -> int | None:
        if cap is None:
            return None
        try:
            normalized = normalize_cap_entry(cap)
        except Exception:
            normalized = cap

        candidates: list[Any] = []
        if isinstance(normalized, dict):
            for field in ("count", "copies", "copy_count", "instance_count", "instances", "quantity", "qty"):
                if field in normalized:
                    candidates.append(normalized.get(field))
            for field in ("levels", "copy_levels", "instances"):
                value = normalized.get(field)
                if isinstance(value, (list, tuple)):
                    candidates.append(len(value))
        elif isinstance(normalized, (list, tuple)):
            candidates.append(len(normalized))

        for value in candidates:
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            if count > 0:
                return count
        return None

    def _find_cap_from_category_caps(self, town_hall: int, category: str, cap_name: str) -> Any:
        try:
            category_caps = get_category_caps(int(town_hall), category)
        except Exception:
            return None
        if not category_caps:
            return None

        target = self._normalize_cap_lookup_key(cap_name)
        if isinstance(category_caps, dict):
            for key, value in category_caps.items():
                if self._normalize_cap_lookup_key(key) == target:
                    return value
                if isinstance(value, dict):
                    for name_field in ("name", "label", "title"):
                        if self._normalize_cap_lookup_key(value.get(name_field)) == target:
                            return value
        elif isinstance(category_caps, list):
            for value in category_caps:
                if isinstance(value, dict):
                    for name_field in ("name", "label", "title"):
                        if self._normalize_cap_lookup_key(value.get(name_field)) == target:
                            return value
        return None

    def _resolve_item_copy_cap_from_caps(self, town_hall: int, item_key: str) -> int | None:
        # Walls are stored in TH_CAPS as a category-level dict, e.g.
        # {"walls": {"count": 325, "max_level": 18}}, not always as a normal
        # named item. Resolve them directly so /trackcopies, coverage, and
        # account-completion totals follow th_caps.py instead of any stale fallback.
        if item_key == "wall":
            try:
                wall_cap = (TH_CAPS.get(int(town_hall), {}) or {}).get("walls")
                wall_count = self._extract_copy_count_from_cap(wall_cap)
                if wall_count is not None:
                    return max(1, int(wall_count))
            except Exception:
                pass

        mapping = TH_CAP_NAME_MAP.get(item_key)
        if not mapping:
            return None
        category, cap_name = mapping

        entry = None
        try:
            entry = get_item_cap(int(town_hall), category, cap_name, None)
        except Exception:
            entry = None
        copy_count = self._extract_copy_count_from_cap(entry)
        if copy_count is not None:
            return max(1, copy_count)

        entry = self._find_cap_from_category_caps(int(town_hall), category, cap_name)
        copy_count = self._extract_copy_count_from_cap(entry)
        if copy_count is not None:
            return max(1, copy_count)
        return None

    def get_item_copy_cap(self, town_hall: int | None, item_key: str) -> int:
        if item_key not in TH_CAP_NAME_MAP:
            return max(1, int(MIN_COPY_FALLBACK_COUNTS.get(item_key, 1)))

        if town_hall:
            direct = self._resolve_item_copy_cap_from_caps(int(town_hall), item_key)
            if direct is not None:
                return direct

        resolved_counts: list[int] = []
        for th in sorted(TH_CAPS.keys()):
            count = self._resolve_item_copy_cap_from_caps(int(th), item_key)
            if count is not None:
                resolved_counts.append(int(count))
        if resolved_counts:
            return max(1, max(resolved_counts))

        if item_key == "wall" and town_hall and int(town_hall) >= 17:
            return 325
        return max(1, int(MIN_COPY_FALLBACK_COUNTS.get(item_key, 1)))

    def is_multi_copy_item(self, town_hall: int | None, item_key: str) -> bool:
        return self.get_item_copy_cap(town_hall, item_key) > 1

    def get_item_status(self, user: dict[str, Any], item_key: str, targets: dict[str, int] | None = None, levels: dict[str, int] | None = None) -> dict[str, Any]:
        if targets is None:
            targets = self.get_effective_targets(user)
        if levels is None:
            levels = self.get_effective_levels(user)
        target = int(targets.get(item_key, 0) or 0)
        town_hall = user.get("town_hall")
        copy_cap = self.get_item_copy_cap(town_hall, item_key)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user).get(item_key, [])

        if copy_cap > 1:
            if manual_copy_levels:
                confirmed = [max(0, int(v)) for v in manual_copy_levels[:copy_cap]]
            elif item_key in manual_levels and item_key != "wall":
                # Treat a plain /trackupgrade on a multi-copy manual item as
                # "all copies are at this same level". Walls are excluded because
                # one entered wall level should never imply every wall is complete.
                inferred_level = max(0, int(manual_levels.get(item_key, 0) or 0))
                confirmed = [inferred_level] * copy_cap
            else:
                confirmed = []

            if confirmed:
                tracked_copies = len(confirmed)
                padded = confirmed + [0] * max(0, copy_cap - tracked_copies)
                done = sum(1 for lvl in padded if target > 0 and lvl >= target)
                lowest = min(padded) if padded else 0
                highest = max(padded) if padded else 0
                return {
                    "multi_copy": True,
                    "copy_cap": copy_cap,
                    "tracked": copy_cap,
                    "done": done,
                    "target": target,
                    "current": lowest,
                    "highest": highest,
                    "next_level": min(lowest + 1, target) if target > 0 else lowest + 1,
                    "gap": max(target - lowest, 0),
                    "remaining_copies": max(copy_cap - done, 0),
                    "tracked_copies": tracked_copies,
                    "untracked_copies": max(copy_cap - tracked_copies, 0),
                    "fully_confirmed": tracked_copies >= copy_cap,
                    "copy_levels": padded,
                }

        current = int(levels.get(item_key, 0) or 0)
        done = 1 if current >= target and target > 0 else 0
        return {
            "multi_copy": False,
            "copy_cap": 1,
            "tracked": 1,
            "done": done,
            "target": target,
            "current": current,
            "highest": current,
            "next_level": min(current + 1, target) if target > 0 else current + 1,
            "gap": max(target - current, 0),
            "remaining_copies": 0 if done else 1,
            "tracked_copies": 1 if item_key in levels or item_key in manual_levels else 0,
            "untracked_copies": 0,
            "fully_confirmed": True,
            "copy_levels": [current],
        }

    def get_synced_max_levels(self, user: dict[str, Any]) -> dict[str, int]:
        return {
            k: int(v)
            for k, v in (user.get("synced_max_levels") or {}).items()
            if k in ITEMS
        }

    def sanitize_target(self, item_key: str, current: int, target: int, town_hall: int | None = None, synced_max_levels: dict[str, int] | None = None) -> int:
        target = max(int(target), int(current))
        th_cap = self.get_th_cap_target(town_hall, item_key)
        if th_cap and th_cap > 0:
            target = min(target, int(th_cap))
            target = max(target, int(current))
        if synced_max_levels:
            hard_cap = int(synced_max_levels.get(item_key, 0) or 0)
            if hard_cap > 0:
                target = min(target, hard_cap)
                target = max(target, int(current))
        return target

    def get_effective_targets(self, user: dict[str, Any]) -> dict[str, int]:
        role = user.get("role", DEFAULT_ROLE)
        town_hall = user.get("town_hall")
        inferred = self.infer_default_targets(town_hall, role)
        targets = dict(inferred)
        targets.update({k: int(v) for k, v in (user.get("targets") or {}).items() if k in ITEMS})

        # TH caps are the source of truth for supported items.
        for item_key in TH_CAP_NAME_MAP:
            cap_target = self.get_th_cap_target(town_hall, item_key)
            if cap_target is not None:
                targets[item_key] = cap_target

        levels = self.get_effective_levels(user)
        synced_max_levels = self.get_synced_max_levels(user)

        sanitized: dict[str, int] = {}
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue

            # Prevent progress/tracking totals from drifting away from sync/account
            # completion totals. If an item is part of the TH-cap model but the
            # current Town Hall has no cap entry for it, exclude it from the active
            # target pool for this account.
            if item_key in TH_CAP_NAME_MAP and self.get_th_cap_target(town_hall, item_key) is None:
                continue

            current = int(levels.get(item_key, 0))
            sanitized[item_key] = self.sanitize_target(item_key, current, int(target), town_hall, synced_max_levels)

        return sanitized
    
    def clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def lane_weight(self, lane: str) -> float:
        return LANE_WEIGHTS.get(lane, 1.0)

    def compute_weighted_impact(self, meta: ItemMeta, role: str, mode: str | None = None) -> float:
        role_weights = ROLE_WEIGHTS.get(role, ROLE_WEIGHTS[DEFAULT_ROLE])
        role_offense = role_weights["offense"]
        role_farming = role_weights["farming"]
        role_defense = role_weights["defense"]
        role_utility = role_weights["utility"]

        if mode == "war":
            role_offense *= 1.12
            role_utility *= 1.05
            role_farming *= 0.90
            role_defense *= 0.92
        elif mode == "farm":
            role_farming *= 1.12
            role_utility *= 1.06
            role_offense *= 0.94

        return (
            meta.offense * role_offense
            + meta.farming * role_farming
            + meta.defense * role_defense
            + meta.utility * role_utility
        )

    def compute_time_efficiency(self, weighted_impact: float, meta: ItemMeta) -> float:
        raw = (weighted_impact / max(meta.time_weight, 1.0)) * 10.0
        return round(self.clamp(raw, 0.0, 20.0), 2)

    def compute_cost_efficiency(self, weighted_impact: float, meta: ItemMeta) -> float:
        raw = (weighted_impact / max(meta.cost_weight, 1.0)) * 8.0
        return round(self.clamp(raw, 0.0, 16.0), 2)

    def compute_urgency(self, gap: int) -> float:
        raw = 3.0 + (gap * 2.4)
        return round(self.clamp(raw, 0.0, 16.0), 2)

    def compute_blocking_bonus(self, meta: ItemMeta) -> float:
        raw = meta.blocks_progress * 4.0 * self.lane_weight(meta.lane)
        return round(self.clamp(raw, 0.0, 10.0), 2)

    def build_lane_snapshot(self, user: dict[str, Any]) -> dict[str, dict[str, float]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        lanes: dict[str, dict[str, float]] = {
            "hero": {"tracked": 0, "done": 0, "percent": 100.0},
            "lab": {"tracked": 0, "done": 0, "percent": 100.0},
            "builder": {"tracked": 0, "done": 0, "percent": 100.0},
        }
        for item_key in targets:
            meta = ITEMS.get(item_key)
            if not meta:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            lane = meta.lane
            lanes.setdefault(lane, {"tracked": 0, "done": 0, "percent": 100.0})
            lanes[lane]["tracked"] += int(status.get("tracked", 0))
            lanes[lane]["done"] += int(status.get("done", 0))
        for lane, row in lanes.items():
            tracked = int(row.get("tracked", 0))
            done = int(row.get("done", 0))
            row["percent"] = round((done / tracked) * 100, 1) if tracked else 100.0
        return lanes

    def resolve_advisor_mode(self, user: dict[str, Any], requested_mode: str | None = None) -> str:
        mode = str(requested_mode or user.get("advisor_mode") or "auto").strip().lower()
        if mode in {"war", "farm"}:
            return mode
        role = str(user.get("role", DEFAULT_ROLE)).lower()
        return "farm" if role == "farmer" else "war"

    def get_mode_profile(self, user: dict[str, Any], requested_mode: str | None = None) -> dict[str, Any]:
        mode = self.resolve_advisor_mode(user, requested_mode=requested_mode)
        return {
            "mode": mode,
            "category_bias": dict(MODE_CATEGORY_BIAS.get(mode, {})),
            "lane_bias": dict(MODE_LANE_BIAS.get(mode, {})),
        }

    def get_item_resource_type(self, item_key: str, meta: ItemMeta) -> str:
        if meta.category in {"hero", "pet"}:
            return "dark_elixir"
        if meta.category in {"troop", "spell", "siege"}:
            return "elixir"
        if meta.category in {"defense", "trap", "economy"}:
            return "gold"
        if item_key in ELIXIR_BUILDING_KEYS:
            return "elixir"
        if item_key in GOLD_BUILDING_KEYS:
            return "gold"
        if meta.lane == "lab":
            return "elixir"
        return "gold"

    def compute_mode_multiplier(self, *, item_key: str, meta: ItemMeta, mode: str, role: str, timing_context: dict[str, Any] | None = None) -> float:
        category_bias = float(MODE_CATEGORY_BIAS.get(mode, {}).get(meta.category, 1.0))
        lane_bias = float(MODE_LANE_BIAS.get(mode, {}).get(meta.lane, 1.0))
        resource_pressure = dict((timing_context or {}).get("resource_pressure") or {})
        war_state = dict((timing_context or {}).get("war_state") or {})
        resource_type = self.get_item_resource_type(item_key, meta)

        multiplier = category_bias * lane_bias

        if mode == "war":
            if item_key in OFFENSE_CORE_KEYS or item_key in HERO_KEYS:
                multiplier += 0.08
            if war_state.get("cwl") and meta.category in {"hero", "troop", "spell", "siege", "pet"}:
                multiplier += 0.06
            if war_state.get("in_war") and meta.category in {"hero", "pet"}:
                multiplier -= 0.08
        elif mode == "farm":
            if item_key in BUILDER_CORE_KEYS:
                multiplier += 0.08
            if meta.category == "economy":
                multiplier += 0.06
            if meta.category in {"troop", "spell", "siege"} and meta.offense >= 8 and item_key not in OFFENSE_CORE_KEYS:
                multiplier -= 0.05

        pressure = float(resource_pressure.get(resource_type, 0.0))
        if pressure >= 0.90:
            multiplier += 0.08
        elif pressure >= 0.75:
            multiplier += 0.04

        if role == "attacker" and mode == "war" and meta.offense >= 8:
            multiplier += 0.04
        elif role == "farmer" and mode == "farm" and (meta.farming >= 5 or meta.utility >= 6):
            multiplier += 0.04

        return round(self.clamp(multiplier, 0.70, 1.35), 3)

    def select_recommendation_mix(self, candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        count = max(1, min(int(count or 1), 10))
        if len(candidates) <= count:
            return candidates[:count]

        chosen: list[dict[str, Any]] = []
        category_seen: dict[str, int] = {}
        lane_seen: dict[str, int] = {}

        remaining = list(candidates)
        while remaining and len(chosen) < count:
            best_index = 0
            best_value = None
            for idx, rec in enumerate(remaining):
                adjusted = float(rec.get("score", 0.0))
                category = str(ITEMS.get(rec.get("item_key"), ItemMeta("", "", "building",0,0,0,0,1)).category) if rec.get("item_key") in ITEMS else str(rec.get("category", "building"))
                lane = str(rec.get("lane", "builder"))
                adjusted -= category_seen.get(category, 0) * 2.5
                adjusted -= lane_seen.get(lane, 0) * 1.4
                if rec.get("multi_copy"):
                    adjusted -= 0.5
                if best_value is None or adjusted > best_value:
                    best_value = adjusted
                    best_index = idx
            pick = remaining.pop(best_index)
            chosen.append(pick)
            pick_meta = ITEMS.get(pick.get("item_key"))
            if pick_meta:
                category_seen[pick_meta.category] = category_seen.get(pick_meta.category, 0) + 1
            lane_seen[str(pick.get("lane", "builder"))] = lane_seen.get(str(pick.get("lane", "builder")), 0) + 1

        chosen.sort(key=lambda row: (-float(row.get("score", 0.0)), str(row.get("label", "")).lower()))
        return chosen

    def _normalize_pressure_value(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric > 1.0:
                numeric = numeric / 100.0
            return max(0.0, min(1.0, numeric))
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "")
            if not cleaned:
                return 0.0
            try:
                numeric = float(cleaned)
                if numeric > 1.0:
                    numeric = numeric / 100.0
                return max(0.0, min(1.0, numeric))
            except ValueError:
                return 0.0
        return 0.0

    def _extract_resource_pressure(self, user: dict[str, Any]) -> dict[str, float]:
        resources = dict(user.get("resources") or {})
        storages = dict(user.get("storage_pressure") or {})
        return {
            "gold": self._normalize_pressure_value(user.get("gold_pressure", resources.get("gold_pressure", storages.get("gold", user.get("gold_fill"))))),
            "elixir": self._normalize_pressure_value(user.get("elixir_pressure", resources.get("elixir_pressure", storages.get("elixir", user.get("elixir_fill"))))),
            "dark_elixir": self._normalize_pressure_value(user.get("dark_elixir_pressure", resources.get("dark_elixir_pressure", storages.get("dark_elixir", user.get("dark_elixir_fill"))))),
        }

    def _extract_hero_availability(self, user: dict[str, Any]) -> dict[str, Any]:
        hero_keys = {
            "king_up": ("king_up", "barbarian_king_up", "bk_up"),
            "queen_up": ("queen_up", "archer_queen_up", "aq_up"),
            "warden_up": ("warden_up", "grand_warden_up", "gw_up"),
            "rc_up": ("rc_up", "royal_champion_up", "champ_up"),
        }
        availability: dict[str, Any] = {}
        down_count = 0
        any_known = False
        for output_key, candidates in hero_keys.items():
            raw = None
            for key in candidates:
                if key in user:
                    raw = user.get(key)
                    break
            if raw is None:
                availability[output_key] = None
                continue
            is_up = bool(raw)
            any_known = True
            availability[output_key] = is_up
            if not is_up:
                down_count += 1
        availability["down_count"] = down_count if any_known else 0
        availability["known"] = any_known
        return availability

    def _extract_war_state(self, user: dict[str, Any]) -> dict[str, Any]:
        raw = dict(user.get("war_state") or {})
        in_war = bool(
            raw.get("in_war")
            or user.get("in_war")
            or user.get("war_active")
            or user.get("war_day")
            or user.get("war_live")
        )
        war_prepping = bool(
            raw.get("war_prepping")
            or user.get("war_prepping")
            or user.get("prep_day")
            or user.get("war_prep")
        )
        cwl = bool(
            raw.get("cwl")
            or user.get("cwl")
            or user.get("cwl_active")
            or user.get("league_war")
        )
        return {
            "in_war": in_war,
            "war_prepping": war_prepping,
            "cwl": cwl,
            "active": bool(in_war or war_prepping or cwl),
        }

    def get_timing_context(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> dict[str, Any]:
        mode = self.resolve_advisor_mode(user, requested_mode)
        if builder_idle is None:
            builder_idle = bool(user.get("builder_idle") or user.get("builders_idle") or user.get("builder_free"))
        if lab_idle is None:
            lab_idle = bool(user.get("lab_idle") or user.get("laboratory_idle") or user.get("lab_free"))

        lane_snapshot = self.build_lane_snapshot(user)
        resource_pressure = self._extract_resource_pressure(user)
        hero_availability = self._extract_hero_availability(user)
        war_state = self._extract_war_state(user)

        hero_pct = float(lane_snapshot.get("hero", {}).get("percent", 100.0))
        lab_pct = float(lane_snapshot.get("lab", {}).get("percent", 100.0))
        builder_pct = float(lane_snapshot.get("builder", {}).get("percent", 100.0))
        account_pressure = {
            "hero_lane": round(max(0.0, min(1.0, (100.0 - hero_pct) / 100.0)), 3),
            "lab_lane": round(max(0.0, min(1.0, (100.0 - lab_pct) / 100.0)), 3),
            "builder_lane": round(max(0.0, min(1.0, (100.0 - builder_pct) / 100.0)), 3),
            "offense_core": round(
                max(
                    0.0,
                    min(
                        1.0,
                        (
                            resource_pressure["dark_elixir"]
                            + (1.0 if not hero_availability.get("known") else hero_availability.get("down_count", 0) / 4.0)
                        )
                        / 2.0,
                    ),
                ),
                3,
            ),
        }

        if mode == "auto":
            if war_state["active"]:
                resolved_mode = "war"
            elif resource_pressure["gold"] >= 0.85 or resource_pressure["elixir"] >= 0.85 or resource_pressure["dark_elixir"] >= 0.85:
                resolved_mode = "farm"
            elif account_pressure["hero_lane"] >= max(account_pressure["lab_lane"], account_pressure["builder_lane"]) and account_pressure["hero_lane"] >= 0.35:
                resolved_mode = "war"
            else:
                resolved_mode = "farm" if str(user.get("role", DEFAULT_ROLE)).lower() == "farmer" else "war"
        else:
            resolved_mode = mode

        upgrade_window = {
            "short_builders": int(user.get("short_builders") or (1 if builder_idle else 0)),
            "long_builders": int(user.get("long_builders") or 0),
            "lab_finishing_soon": bool(user.get("lab_finishing_soon") or user.get("lab_soon")),
        }

        return {
            "mode": resolved_mode,
            "requested_mode": mode,
            "builder_idle": bool(builder_idle),
            "lab_idle": bool(lab_idle),
            "resource_pressure": resource_pressure,
            "hero_availability": hero_availability,
            "war_state": war_state,
            "account_pressure": account_pressure,
            "upgrade_window": upgrade_window,
        }

    def compute_strategic_bonus(self, *, item_key: str, meta: ItemMeta, current: int, target: int, role: str, user: dict[str, Any] | None = None, lane_snapshot: dict[str, Any] | None = None, milestone_state: dict[str, Any] | None = None, timing_context: dict[str, Any] | None = None) -> tuple[float, list[str]]:
        bonus = 0.0
        reasons: list[str] = []
        gap = max(target - current, 0)
        if not user:
            return bonus, reasons

        milestone_state = milestone_state or self.get_milestone_state(user)
        achieved = milestone_state.get("achieved", {})
        groups = milestone_state.get("group_status", {})
        lane_snapshot = lane_snapshot or self.build_lane_snapshot(user)
        timing_context = timing_context or self.get_timing_context(user)
        mode = str(timing_context.get("mode", "war"))
        builder_idle = bool(timing_context.get("builder_idle", False))
        lab_idle = bool(timing_context.get("lab_idle", False))
        resource_pressure = dict(timing_context.get("resource_pressure") or {})
        war_state = dict(timing_context.get("war_state") or {})
        hero_availability = dict(timing_context.get("hero_availability") or {})
        account_pressure = dict(timing_context.get("account_pressure") or {})
        upgrade_window = dict(timing_context.get("upgrade_window") or {})

        hero_pct = float(lane_snapshot.get("hero", {}).get("percent", 100.0))
        lab_pct = float(lane_snapshot.get("lab", {}).get("percent", 100.0))
        builder_pct = float(lane_snapshot.get("builder", {}).get("percent", 100.0))
        lowest_lane = min(("hero", hero_pct), ("lab", lab_pct), ("builder", builder_pct), key=lambda x: x[1])[0]

        if meta.lane == lowest_lane and lane_snapshot.get(lowest_lane, {}).get("tracked", 0):
            lane_gap = max(hero_pct, lab_pct, builder_pct) - float(lane_snapshot.get(lowest_lane, {}).get("percent", 100.0))
            lane_bonus = min(7.0, round(lane_gap / 9.0, 1))
            if lane_bonus > 0:
                bonus += lane_bonus
                reasons.append(f"{lowest_lane.title()} lane is your most behind right now.")

        if not achieved.get("war_ready"):
            if item_key in HERO_KEYS:
                bonus += 8.0
                reasons.append("Hero progress directly pushes your war-ready checkpoint.")
            elif item_key in OFFENSE_CORE_KEYS:
                bonus += 6.5
                reasons.append("This helps close your core war offense gap.")
            elif role == "attacker" and meta.category in {"defense", "economy", "trap"}:
                bonus -= 6.0
                reasons.append("War value is lagging, so this can wait behind offense.")

        if not achieved.get("heroes_complete") and item_key in HERO_KEYS:
            remaining = max(0, int(groups.get("heroes", {}).get("total", 0)) - int(groups.get("heroes", {}).get("done", 0)))
            bonus += 5.5
            if remaining:
                reasons.append(f"Hero targets are still incomplete ({remaining} remaining).")

        if not achieved.get("offense_core_complete") and item_key in OFFENSE_CORE_KEYS:
            bonus += 5.0
            reasons.append("This is part of your tracked offense core.")

        if not achieved.get("builder_core_complete") and item_key in BUILDER_CORE_KEYS:
            bonus += 4.5
            reasons.append("Builder core is still unfinished, so this unlocks cleaner follow-up choices.")

        if gap == 1:
            bonus += 5.0
            reasons.append("One level finishes this target immediately.")
        elif gap == 2:
            bonus += 2.5
            reasons.append("Only two levels remain to finish this target.")

        if role == "attacker" and meta.category in {"troop", "spell", "hero", "siege", "pet"} and meta.offense >= 8:
            bonus += 3.0
        elif role == "farmer" and meta.category in {"economy", "hero", "building"} and meta.farming >= 4:
            bonus += 2.5

        if mode == "war":
            if meta.category in {"hero", "troop", "spell", "siege", "pet"}:
                war_bonus = 4.5 if meta.offense >= 8 else 2.0
                bonus += war_bonus
                reasons.append("War mode is pushing offense-first value.")
            elif meta.category in {"economy", "defense", "trap"}:
                bonus -= 5.0
                reasons.append("War mode is holding lower-value farm/defense work for later.")
            elif meta.category == "building" and item_key in OFFENSE_CORE_KEYS | BUILDER_CORE_KEYS:
                bonus += 2.5
                reasons.append("War mode still values core unlock buildings.")
        elif mode == "farm":
            if meta.category in {"economy", "building"}:
                farm_bonus = 4.0 if meta.farming >= 4 or meta.utility >= 7 else 2.0
                bonus += farm_bonus
                reasons.append("Farm mode is favoring economy and progression flow.")
            elif meta.category in {"defense", "trap"}:
                bonus += 1.5
            elif meta.category in {"siege", "spell", "troop"} and meta.offense >= 8:
                bonus -= 2.5
                reasons.append("Farm mode is letting pure war offense wait a bit.")

        if builder_idle:
            if meta.lane == "builder":
                bonus += 10.0
                reasons.append("A builder is idle, so builder work gets immediate value.")
            else:
                bonus -= 1.5
        if lab_idle:
            if meta.lane == "lab":
                bonus += 10.0
                reasons.append("Your lab is idle, so lab upgrades jump the queue.")
            else:
                bonus -= 1.5

        if float(resource_pressure.get("dark_elixir", 0.0)) >= 0.85 and meta.category in {"hero", "pet"}:
            bonus += 6.0
            reasons.append("Dark elixir pressure is high, so hero/pet value rises.")
        if float(resource_pressure.get("gold", 0.0)) >= 0.85 and meta.category in {"building", "defense", "trap", "economy"}:
            bonus += 4.0
            reasons.append("Gold is filling up, so builder-side spending becomes more urgent.")
        if float(resource_pressure.get("elixir", 0.0)) >= 0.85 and meta.category in {"troop", "spell", "siege", "building", "economy"}:
            bonus += 4.0
            reasons.append("Elixir pressure is high, so lab/progression work gets a bump.")

        if war_state.get("war_prepping") and meta.category in {"hero", "pet"}:
            bonus -= 4.5
            reasons.append("War prep is active, so extra hero downtime is less attractive.")
        if war_state.get("in_war") and meta.category in {"hero", "pet"}:
            bonus -= 6.0
            reasons.append("You are in war, so hero downtime is being held back.")
        if war_state.get("cwl") and meta.category in {"troop", "spell", "siege"}:
            bonus += 5.0
            reasons.append("CWL pressure boosts immediate army value.")

        if hero_availability.get("known") and hero_availability.get("down_count", 0) >= 2 and meta.category in {"hero", "pet"} and mode == "war":
            bonus -= 3.5
            reasons.append("Multiple heroes are already down, so more war downtime is less ideal.")

        if float(account_pressure.get("hero_lane", 0.0)) >= 0.60 and meta.lane == "hero":
            bonus += 4.0
            reasons.append("Hero lane pressure is high right now.")
        if float(account_pressure.get("lab_lane", 0.0)) >= 0.60 and meta.lane == "lab":
            bonus += 3.5
            reasons.append("Lab lane is lagging behind your other progress.")
        if float(account_pressure.get("builder_lane", 0.0)) >= 0.60 and meta.lane == "builder":
            bonus += 3.5
            reasons.append("Builder lane is your biggest structural backlog.")

        if bool(upgrade_window.get("lab_finishing_soon")) and meta.lane == "lab":
            bonus += 2.5
            reasons.append("Your lab is finishing soon, so planning the next lab step has extra value.")

        return round(bonus, 2), reasons[:3]

    def score_candidate(self, *, item_key: str, current: int, target: int, role: str, user: dict[str, Any] | None = None, lane_snapshot: dict[str, Any] | None = None, milestone_state: dict[str, Any] | None = None, timing_context: dict[str, Any] | None = None) -> dict[str, Any]:
        meta = ITEMS[item_key]
        gap = max(target - current, 0)

        if gap <= 0:
            return {
                "item_key": item_key,
                "label": meta.label,
                "score": 0.0,
                "priority": "Done",
                "current": current,
                "next_level": current,
                "target": target,
                "gap": 0,
                "reasons": ["At or above advisor target."],
                "score_breakdown": {},
            }

        next_level = current + 1
        mode = str((timing_context or {}).get("mode") or self.resolve_advisor_mode(user or {}, None) if user else "war")
        mode_multiplier = self.compute_mode_multiplier(
            item_key=item_key,
            meta=meta,
            mode=mode,
            role=role,
            timing_context=timing_context,
        )

        weighted_impact = self.compute_weighted_impact(meta, role, mode=mode) * mode_multiplier
        impact_score = round(weighted_impact * 3.8, 2)
        time_efficiency = self.compute_time_efficiency(weighted_impact, meta)
        cost_efficiency = self.compute_cost_efficiency(weighted_impact, meta)
        urgency = self.compute_urgency(gap)
        blocking_bonus = self.compute_blocking_bonus(meta)

        foundational_bonus = 6.0 if meta.foundational else 0.0
        breakpoint_bonus = 5.0 if next_level in meta.breakpoints else 0.0
        role_bonus = float(meta.role_bonus.get(role, 0.0))
        finish_bonus = 6.0 if next_level >= target else (2.0 if gap == 2 else 0.0)
        strategic_bonus, strategic_reasons = self.compute_strategic_bonus(
            item_key=item_key,
            meta=meta,
            current=current,
            target=target,
            role=role,
            user=user,
            lane_snapshot=lane_snapshot,
            milestone_state=milestone_state,
            timing_context=timing_context,
        )

        score = round(
            impact_score
            + time_efficiency
            + cost_efficiency
            + urgency
            + blocking_bonus
            + foundational_bonus
            + breakpoint_bonus
            + role_bonus
            + finish_bonus
            + strategic_bonus
            + ((mode_multiplier - 1.0) * 22.0),
            1,
        )

        if score >= 90:
            priority = "High"
        elif score >= 65:
            priority = "Medium"
        else:
            priority = "Low"

        reasons: list[str] = []

        if meta.foundational:
            reasons.append("Unlocks stronger follow-up upgrades.")
        if blocking_bonus >= 7:
            reasons.append("High blocker value, so it is worth clearing early.")
        if time_efficiency >= 14:
            reasons.append("Excellent time-to-value upgrade.")
        elif time_efficiency >= 10:
            reasons.append("Strong value for the time invested.")
        if cost_efficiency >= 11:
            reasons.append("Good value for the resource cost.")
        if gap >= 5:
            reasons.append(f"You are {gap} levels behind target here.")
        elif gap >= 3:
            reasons.append(f"Still {gap} levels away from target.")
        if next_level in meta.breakpoints:
            reasons.append(f"Level {next_level} is a meaningful breakpoint.")
        if role == "attacker" and meta.offense >= 8:
            reasons.append("Very strong for your attacker profile.")
        elif role == "farmer" and meta.farming >= 8:
            reasons.append("Very efficient for a farmer profile.")
        elif role == "hybrid" and (meta.offense + meta.utility) >= 13:
            reasons.append("Strong balanced value for a hybrid profile.")

        for strategic_reason in strategic_reasons:
            if strategic_reason not in reasons:
                reasons.append(strategic_reason)

        if not reasons:
            reasons.append("Solid upgrade with balanced short-term value.")

        return {
            "item_key": item_key,
            "label": meta.label,
            "score": score,
            "priority": priority,
            "current": current,
            "next_level": next_level,
            "target": target,
            "gap": gap,
            "lane": meta.lane,
            "mode": (timing_context or {}).get("mode", "war") if timing_context else "war",
            "builder_idle": bool((timing_context or {}).get("builder_idle", False)) if timing_context else False,
            "lab_idle": bool((timing_context or {}).get("lab_idle", False)) if timing_context else False,
            "reasons": reasons[:3],
            "score_breakdown": {
                "impact": round(impact_score, 1),
                "time": round(time_efficiency, 1),
                "cost": round(cost_efficiency, 1),
                "urgency": round(urgency, 1),
                "blocking": round(blocking_bonus, 1),
                "foundational": round(foundational_bonus, 1),
                "breakpoint": round(breakpoint_bonus, 1),
                "role": round(role_bonus, 1),
                "finish": round(finish_bonus, 1),
                "strategy": round(strategic_bonus, 1),
                "mode": round((mode_multiplier - 1.0) * 22.0, 1),
            },
        }
    
    def classify_recommendation_timing(self, rec: dict[str, Any]) -> str:
        breakdown = rec.get("score_breakdown", {})
        time_score = float(breakdown.get("time", 0.0))
        cost_score = float(breakdown.get("cost", 0.0))
        blocking_score = float(breakdown.get("blocking", 0.0))
        urgency_score = float(breakdown.get("urgency", 0.0))
        total_score = float(rec.get("score", 0.0))

        if total_score >= 95 and (time_score >= 11 or blocking_score >= 7):
            return "do_now"

        if blocking_score >= 8:
            return "do_now"

        if urgency_score >= 12 and time_score >= 9:
            return "do_now"

        if total_score >= 78:
            return "good_next"

        if cost_score < 7 and time_score < 8:
            return "wait"

        if blocking_score >= 5 and (time_score < 8 or cost_score < 8):
            return "save_for"

        return "good_next"

    def build_decision_summary(self, rec: dict[str, Any]) -> str:
        decision = self.classify_recommendation_timing(rec)

        if decision == "do_now":
            return "Do this now"
        if decision == "good_next":
            return "Good next move"
        if decision == "wait":
            return "Wait on this"
        if decision == "save_for":
            return "Save for this"

        return "Recommended"

    def build_decision_reason(self, rec: dict[str, Any], role: str) -> str:
        breakdown = rec.get("score_breakdown", {})
        time_score = float(breakdown.get("time", 0.0))
        cost_score = float(breakdown.get("cost", 0.0))
        blocking_score = float(breakdown.get("blocking", 0.0))
        urgency_score = float(breakdown.get("urgency", 0.0))
        impact_score = float(breakdown.get("impact", 0.0))
        strategy_score = float(breakdown.get("strategy", 0.0))
        gap = int(rec.get("gap", 0))
        lane = str(rec.get("lane", "builder"))

        reasons: list[str] = []

        if impact_score >= 28:
            if role == "attacker":
                reasons.append("strong war value")
            elif role == "farmer":
                reasons.append("strong farming value")
            else:
                reasons.append("strong all-around value")

        if time_score >= 14:
            reasons.append("fast payoff")
        elif time_score >= 10:
            reasons.append("good time efficiency")

        if cost_score >= 11:
            reasons.append("good resource value")
        elif cost_score <= 6:
            reasons.append("resource heavy")

        if blocking_score >= 7:
            reasons.append("clears a progression bottleneck")

        if strategy_score >= 8:
            reasons.append("fits your current account checkpoint")
        elif strategy_score >= 4:
            reasons.append("lines up with your current progression pressure")

        if urgency_score >= 12 or gap >= 5:
            reasons.append("you are far behind target")
        elif gap >= 3:
            reasons.append("you are still behind target")

        if lane == "hero":
            reasons.append("uses your hero lane")
        elif lane == "lab":
            reasons.append("fits your lab lane")
        elif lane == "builder":
            reasons.append("fits your builder lane")

        if not reasons:
            reasons.append("solid upgrade value")

        return ", ".join(reasons[:3]).capitalize() + "."

    def build_decision_block(self, recs: list[dict[str, Any]], role: str) -> str:
        lines: list[str] = []

        for idx, rec in enumerate(recs, start=1):
            summary = self.build_decision_summary(rec)
            reason = self.build_decision_reason(rec, role)

            lines.append(
                f"**{idx}. {rec['label']} → {rec['next_level']}**\n"
                f"{summary} — {reason}"
            )

        return "\n\n".join(lines)

    def build_waitlist(self, recs: list[dict[str, Any]], role: str, limit: int = 2) -> str:
        if not recs:
            return "Nothing to hold for later right now."

        ranked = sorted(
            recs,
            key=lambda row: (
                self.classify_recommendation_timing(row) not in {"wait", "save_for"},
                -float(row.get("score", 0.0)),
            ),
        )

        wait_items = [r for r in ranked if self.classify_recommendation_timing(r) in {"wait", "save_for"}][:limit]

        if not wait_items:
            return "Top options are all immediately solid right now."

        parts = []
        for rec in wait_items:
            summary = self.build_decision_summary(rec)
            reason = self.build_decision_reason(rec, role)
            parts.append(f"**{rec['label']}** — {summary.lower()} because {reason[:-1].lower()}")

        return "\n".join(parts)

    def build_recommendations(self, user: dict[str, Any], count: int = 5, requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> list[dict[str, Any]]:
        role = user.get("role", DEFAULT_ROLE)
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        candidates: list[dict[str, Any]] = []
        lane_snapshot = self.build_lane_snapshot(user)
        milestone_state = self.get_milestone_state(user)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            current = int(status.get("current", 0))
            if bool(status.get("multi_copy")):
                if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                    continue
                if int(status.get("untracked_copies", 0)) > 0 and current >= int(target):
                    continue
                rec = self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context)
                rec["multi_copy"] = True
                rec["copy_cap"] = int(status.get("copy_cap", 1))
                rec["done_copies"] = int(status.get("done", 0))
                rec["tracked_copies"] = int(status.get("tracked_copies", 0))
                rec["remaining_copies"] = int(status.get("remaining_copies", 0))
                rec["untracked_copies"] = int(status.get("untracked_copies", 0))
                rec["copy_levels"] = list(status.get("copy_levels", []))
                if rec["untracked_copies"] > 0:
                    rec.setdefault("reasons", []).append(f"Track the remaining {rec['untracked_copies']} copy/copies manually to unlock full count progress.")
                elif rec["remaining_copies"] > 1:
                    rec.setdefault("reasons", []).append(f"{rec['done_copies']}/{rec['copy_cap']} copies are already at target.")
                candidates.append(rec)
                continue
            if current >= target:
                continue
            candidates.append(self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context))

        candidates.sort(key=lambda row: (-row["score"], row["label"].lower()))
        return candidates[: max(1, min(count, 10))]

    def build_recommendation_pool(self, user: dict[str, Any], count: int = 5, pool_size: int = 8, requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        role = user.get("role", DEFAULT_ROLE)
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        candidates: list[dict[str, Any]] = []
        lane_snapshot = self.build_lane_snapshot(user)
        milestone_state = self.get_milestone_state(user)
        timing_context = self.get_timing_context(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        for item_key, target in targets.items():
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            current = int(status.get("current", 0))
            if bool(status.get("multi_copy")):
                if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                    continue
                if int(status.get("untracked_copies", 0)) > 0 and current >= int(target):
                    continue
                rec = self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context)
                rec["multi_copy"] = True
                rec["copy_cap"] = int(status.get("copy_cap", 1))
                rec["done_copies"] = int(status.get("done", 0))
                rec["tracked_copies"] = int(status.get("tracked_copies", 0))
                rec["remaining_copies"] = int(status.get("remaining_copies", 0))
                rec["untracked_copies"] = int(status.get("untracked_copies", 0))
                rec["copy_levels"] = list(status.get("copy_levels", []))
                if rec["untracked_copies"] > 0:
                    rec.setdefault("reasons", []).append(f"Track the remaining {rec['untracked_copies']} copy/copies manually to unlock full count progress.")
                elif rec["remaining_copies"] > 1:
                    rec.setdefault("reasons", []).append(f"{rec['done_copies']}/{rec['copy_cap']} copies are already at target.")
                candidates.append(rec)
                continue
            if current >= target:
                continue
            candidates.append(self.score_candidate(item_key=item_key, current=current, target=int(target), role=role, user=user, lane_snapshot=lane_snapshot, milestone_state=milestone_state, timing_context=timing_context))

        candidates.sort(key=lambda row: (-row["score"], row["label"].lower()))

        pool = candidates[: max(1, min(pool_size, 12))]
        top = self.select_recommendation_mix(pool, count=max(1, min(count, 10)))
        return top, pool

    def build_progress_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        if not targets:
            return {"tracked": 0, "done": 0, "percent": 0, "bar": "░░░░░░░░░░"}

        tracked = 0
        done = 0
        for item_key in targets:
            if item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            tracked += int(status.get("tracked", 0))
            done += int(status.get("done", 0))

        percent = round((done / tracked) * 100) if tracked else 0
        filled = max(0, min(10, round(percent / 10)))
        bar = FULL * filled + EMPTY * (10 - filled)
        return {"tracked": tracked, "done": done, "percent": percent, "bar": bar}

    def build_tracking_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        targets = self.get_effective_targets(user)
        levels = self.get_effective_levels(user)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user)

        if not targets:
            return {"tracked": 0, "total": 0, "percent": 0, "bar": "░░░░░░░░░░"}

        tracked = 0
        total = 0
        for item_key in targets:
            meta = ITEMS.get(item_key)
            if not meta:
                continue

            status = self.get_item_status(user, item_key, targets=targets, levels=levels)
            slot_total = int(status.get("tracked", 0))
            total += slot_total

            if meta.source != "manual":
                tracked += slot_total
                continue

            if int(status.get("copy_cap", 1)) > 1:
                if item_key in manual_levels and item_key not in manual_copy_levels:
                    tracked += slot_total
                else:
                    tracked += min(int(status.get("tracked_copies", 0)), slot_total)
            elif item_key in manual_levels or item_key in manual_copy_levels:
                tracked += 1

        percent = round((tracked / total) * 100) if total else 0
        filled = max(0, min(10, round(percent / 10)))
        bar = FULL * filled + EMPTY * (10 - filled)
        return {"tracked": tracked, "total": total, "percent": percent, "bar": bar}

    def _counts_for_confirmed_milestones(self, user: dict[str, Any], key: str) -> bool:
        if key not in ITEMS:
            return False
        meta = ITEMS[key]
        if meta.source != "manual":
            return True
        if self.is_multi_copy_item(user.get("town_hall"), key):
            copy_levels = self.get_manual_copy_levels(user).get(key, [])
            return len(copy_levels) >= self.get_item_copy_cap(user.get("town_hall"), key)
        return key in (user.get("manual_levels") or {})

    def _milestone_group_complete(self, user: dict[str, Any], keys: set[str]) -> tuple[bool, int, int]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        relevant = [
            key for key in keys
            if key in ITEMS and key in targets and self._counts_for_confirmed_milestones(user, key)
        ]
        if not relevant:
            return False, 0, 0

        done = 0
        for key in relevant:
            status = self.get_item_status(user, key, targets=targets, levels=levels)
            if int(status.get("done", 0)) >= int(status.get("tracked", 0)):
                done += 1

        return done == len(relevant), done, len(relevant)

        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)

        relevant = [
            key for key in keys
            if key in ITEMS and key in targets and self._counts_for_confirmed_milestones(user, key)
        ]
        if not relevant:
            return False, 0, 0

        done = 0
        for key in relevant:
            current = int(levels.get(key, 0))
            target = int(targets.get(key, 0))
            if current >= target:
                done += 1

        return done == len(relevant), done, len(relevant)

    def get_milestone_state(self, user: dict[str, Any]) -> dict[str, Any]:
        progress = self.build_progress_snapshot(user)
        percent = int(progress.get("percent", 0))

        progress_hits = [mark for mark in MILESTONE_PROGRESS_MARKS if percent >= mark]

        heroes_complete, heroes_done, heroes_total = self._milestone_group_complete(user, HERO_KEYS)
        offense_complete, offense_done, offense_total = self._milestone_group_complete(user, OFFENSE_CORE_KEYS)
        builder_complete, builder_done, builder_total = self._milestone_group_complete(user, BUILDER_CORE_KEYS)

        role = user.get("role", DEFAULT_ROLE)
        war_ready = heroes_complete and offense_complete and percent >= 60
        if role == "farmer":
            war_ready = heroes_complete and percent >= 60

        achieved = {
            "progress_marks": progress_hits,
            "heroes_complete": heroes_complete,
            "offense_core_complete": offense_complete,
            "builder_core_complete": builder_complete,
            "war_ready": war_ready,
        }

        return {
            "progress": progress,
            "achieved": achieved,
            "group_status": {
                "heroes": {"done": heroes_done, "total": heroes_total},
                "offense": {"done": offense_done, "total": offense_total},
                "builder": {"done": builder_done, "total": builder_total},
            },
        }

    def get_new_milestones(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> list[str]:
        before_state = self.get_milestone_state(before_user)
        after_state = self.get_milestone_state(after_user)

        before_achieved = before_state["achieved"]
        after_achieved = after_state["achieved"]

        new_hits: list[str] = []

        before_marks = set(before_achieved.get("progress_marks", []))
        after_marks = set(after_achieved.get("progress_marks", []))
        for mark in sorted(after_marks - before_marks):
            new_hits.append(f"Reached **{mark}%** tracked progress.")

        if after_achieved.get("heroes_complete") and not before_achieved.get("heroes_complete"):
            new_hits.append("Completed all tracked **hero targets**.")

        if after_achieved.get("offense_core_complete") and not before_achieved.get("offense_core_complete"):
            new_hits.append("Confirmed all tracked **offense-core** targets.")

        if after_achieved.get("builder_core_complete") and not before_achieved.get("builder_core_complete"):
            new_hits.append("Confirmed all tracked **builder-core** targets.")

        if after_achieved.get("war_ready") and not before_achieved.get("war_ready"):
            new_hits.append("Unlocked your **war-ready checkpoint**.")

        return new_hits

    def build_milestone_summary(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]

        badges: list[str] = []

        progress_marks = achieved.get("progress_marks", [])
        if progress_marks:
            badges.append(f"Progress: **{max(progress_marks)}%**")
        else:
            badges.append("Progress: **0%**")

        if achieved.get("heroes_complete"):
            badges.append("Heroes: **Complete**")
        else:
            badges.append(f"Heroes: **{groups['heroes']['done']}/{groups['heroes']['total']}**")

        if achieved.get("offense_core_complete"):
            badges.append("Offense Core Confirmed: **Complete**")
        elif groups["offense"]["total"] > 0:
            badges.append(f"Offense Core Confirmed: **{groups['offense']['done']}/{groups['offense']['total']}**")

        if achieved.get("builder_core_complete"):
            badges.append("Builder Core Confirmed: **Complete**")
        elif groups["builder"]["total"] > 0:
            badges.append(f"Builder Core Confirmed: **{groups['builder']['done']}/{groups['builder']['total']}**")

        badges.append("War Ready: **Yes**" if achieved.get("war_ready") else "War Ready: **Not yet**")
        return " | ".join(badges)

    def build_milestone_celebration(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> str:
        new_hits = self.get_new_milestones(before_user, after_user)
        if not new_hits:
            return "No new milestone unlocked this sync."

        return "\n".join(f"• {hit}" for hit in new_hits[:4])

    def build_milestone_hint(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]

        if not achieved.get("heroes_complete") and groups["heroes"]["total"] > 0:
            remaining = groups["heroes"]["total"] - groups["heroes"]["done"]
            return f"Closest confirmed milestone: finish your **hero targets** ({remaining} remaining)."

        if not achieved.get("offense_core_complete") and groups["offense"]["total"] > 0:
            remaining = groups["offense"]["total"] - groups["offense"]["done"]
            return f"Closest confirmed milestone: finish your **offense core** ({remaining} remaining)."

        if not achieved.get("builder_core_complete") and groups["builder"]["total"] > 0:
            remaining = groups["builder"]["total"] - groups["builder"]["done"]
            return f"Closest confirmed milestone: finish your **builder core** ({remaining} remaining)."

        if not achieved.get("war_ready"):
            return "Closest confirmed milestone: push overall tracked progress high enough for **war-ready**."

        return "Major milestones complete. Time to raise targets and keep climbing."

    def build_mini_progress_bar(self, current: int, target: int, width: int = 8) -> str:
        target = max(1, int(target or 1))
        current = max(0, min(int(current or 0), target))
        filled = round((current / target) * width)
        filled = max(0, min(width, filled))
        return FULL * filled + EMPTY * (width - filled)

    def format_recommendation_card(self, rec: dict[str, Any], idx: int) -> str:
        meta = ITEMS.get(rec["key"])
        lane_emoji = LANE_EMOJIS.get(rec.get("lane", ""), "📌")
        category_emoji = CATEGORY_EMOJIS.get(getattr(meta, "category", ""), "📌")
        timing = self.classify_recommendation_timing(rec)
        timing_emoji = TIMING_EMOJIS.get(timing, "📌")
        progress_bar = self.build_mini_progress_bar(int(rec.get("current", 0)), int(rec.get("target", 1)))
        gap = max(0, int(rec.get("target", 0)) - int(rec.get("current", 0)))
        reason = (rec.get("reasons") or ["Good overall value right now."])[0]
        return (
            f"{timing_emoji} **#{idx} {rec['label']}** {lane_emoji}{category_emoji}\n"
            f"Lvl **{rec['current']} → {rec['next_level']}** of **{rec['target']}**  `{progress_bar}`\n"
            f"Gap: **{gap}** | Score: **{rec['score']}** | {reason}"
        )

    def build_upgrade_dashboard(self, recs: list[dict[str, Any]]) -> str:
        if not recs:
            return "Nothing urgent right now."
        return "\n\n".join(self.format_recommendation_card(rec, idx) for idx, rec in enumerate(recs, start=1))

    def build_lane_summary(self, recs: list[dict[str, Any]]) -> str:
        if not recs:
            return "No lane pressure detected."

        lane_rows: dict[str, list[dict[str, Any]]] = {"hero": [], "lab": [], "builder": []}
        for rec in recs:
            lane_rows.setdefault(rec.get("lane", "builder"), []).append(rec)

        lines: list[str] = []
        for lane in ("hero", "lab", "builder"):
            items = lane_rows.get(lane) or []
            if not items:
                continue
            best = items[0]
            lines.append(f"{LANE_EMOJIS.get(lane, '📌')} **{lane.title()} lane:** {best['label']} → **{best['next_level']}**")
        return "\n".join(lines[:3]) if lines else "No lane pressure detected."

    def build_quick_status_block(self, user: dict[str, Any], recs: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        role = user.get("role", DEFAULT_ROLE).title()
        state = self.get_milestone_state(user)
        war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"
        lane_snapshot = self.build_lane_snapshot(user)
        pressure_lane = min((lane, float(data.get("percent", 100.0))) for lane, data in lane_snapshot.items()) if lane_snapshot else ("none", 100.0)
        top_lane = pressure_lane[0].title() if recs else "None"
        timing_context = timing_context or self.get_timing_context(user)
        mode = str(timing_context.get("mode", "war")).title()
        builder_state = "Idle" if timing_context.get("builder_idle") else "Busy/Unknown"
        lab_state = "Idle" if timing_context.get("lab_idle") else "Busy/Unknown"
        war_state = dict(timing_context.get("war_state") or {})
        resource_pressure = dict(timing_context.get("resource_pressure") or {})
        war_state_label = "CWL" if war_state.get("cwl") else ("In War" if war_state.get("in_war") else ("Prep" if war_state.get("war_prepping") else "None"))
        hottest_resource = max(resource_pressure.items(), key=lambda kv: kv[1])[0] if resource_pressure else "none"
        hottest_value = int(round(float(resource_pressure.get(hottest_resource, 0.0)) * 100)) if resource_pressure else 0
        return (
            f"🎯 **Role:** {role}\n"
            f"🏠 **Town Hall:** {user.get('town_hall') or '?'}\n"
            f"📈 **Progress:** {progress['percent']}% ({progress['done']}/{progress['tracked']})\n"
            f"🔥 **War Ready:** {war_ready}\n"
            f"🧭 **Top pressure lane:** {top_lane}\n"
            f"⚙️ **Mode:** {mode}\n"
            f"🪖 **War state:** {war_state_label}\n"
            f"💰 **Top resource pressure:** {hottest_resource.replace('_', ' ').title()} ({hottest_value}%)\n"
            f"🛠️ **Builders:** {builder_state}\n"
            f"🧪 **Lab:** {lab_state}"
        )

    def _get_economy(self, user: dict[str, Any]) -> dict[str, Any]:
        econ = dict(user.get("advisor_economy") or {})
        econ.setdefault("coins", 0)
        econ.setdefault("efficiency_score", 0)
        econ.setdefault("followed_paths", 0)
        econ.setdefault("missed_paths", 0)
        econ.setdefault("last_recommendations", [])
        econ.setdefault("last_award_at", None)
        return econ

    def build_economy_summary(self, user: dict[str, Any]) -> str:
        econ = self._get_economy(user)
        velocity = self.get_progress_velocity(user)
        return (
            f"🪙 **Coins:** {int(econ.get('coins', 0))}\n"
            f"📈 **Efficiency:** {int(econ.get('efficiency_score', 0))}\n"
            f"✅ **Paths followed:** {int(econ.get('followed_paths', 0))}\n"
            f"🚀 **Progress/day:** {velocity.get('points_per_day', 0):.2f} goals\n"
            f"⭐ **Rating:** {velocity.get('rating', 'Unrated')}"
        )

    def _recommendation_signature(self, rec: dict[str, Any], idx: int) -> dict[str, Any]:
        meta = ITEMS.get(rec.get("key") or rec.get("item_key"))
        return {
            "rank": idx,
            "key": rec.get("key") or rec.get("item_key"),
            "label": rec.get("label"),
            "lane": rec.get("lane"),
            "category": rec.get("category") or (meta.category if meta else None),
            "target": int(rec.get("target", 0) or 0),
            "current": int(rec.get("current", 0) or 0),
            "next_level": int(rec.get("next_level", 0) or 0),
            "score": float(rec.get("score", 0) or 0),
        }

    async def save_active_recommendations(self, user_id: str, player_tag: str | None, recs: list[dict[str, Any]]) -> None:
        payload = [self._recommendation_signature(rec, idx) for idx, rec in enumerate((recs or [])[:10], start=1)]
        timestamp = datetime.now(timezone.utc).isoformat()

        def patch(root: dict[str, Any], account: dict[str, Any]):
            econ = account.setdefault("advisor_economy", {})
            econ.setdefault("coins", 0)
            econ.setdefault("efficiency_score", 0)
            econ.setdefault("followed_paths", 0)
            econ.setdefault("missed_paths", 0)
            econ["last_recommendations"] = payload
            econ["last_award_at"] = econ.get("last_award_at")
            account["advisor_last_mode"] = account.get("advisor_last_mode")
            account["advisor_path_saved_at"] = timestamp

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)

    def evaluate_path_rewards(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> dict[str, Any]:
        econ = self._get_economy(before_user)
        saved = list(econ.get("last_recommendations") or [])
        if not saved:
            return {"coins": 0, "efficiency": 0, "matches": []}

        before_levels = self.get_effective_levels(before_user)
        after_levels = self.get_effective_levels(after_user)
        matches: list[dict[str, Any]] = []
        total_coins = 0
        total_eff = 0

        base_by_rank = {1: 25, 2: 15, 3: 10}
        bonus_cats = {"hero": 8, "troop": 6, "spell": 6, "siege": 6, "pet": 6, "building": 3, "economy": 2, "defense": 2, "trap": 1}

        for rec in saved[:3]:
            key = rec.get("key")
            if not key or key not in ITEMS:
                continue
            before_status = self.get_item_status(before_user, key, targets=self.get_effective_targets(before_user), levels=before_levels)
            after_status = self.get_item_status(after_user, key, targets=self.get_effective_targets(after_user), levels=after_levels)
            before_cur = int(before_status.get("current", before_levels.get(key, 0)) or 0)
            after_cur = int(after_status.get("current", after_levels.get(key, 0)) or 0)
            before_done = int(before_status.get("done", 0) or 0)
            after_done = int(after_status.get("done", 0) or 0)
            progressed = (after_cur > before_cur) or (after_done > before_done)
            if not progressed:
                continue
            rank = int(rec.get("rank", 99) or 99)
            cat = str(rec.get("category") or ITEMS[key].category)
            coins = base_by_rank.get(rank, 5) + bonus_cats.get(cat, 0)
            eff = max(4, 14 - (rank - 1) * 3) + (3 if cat in {"hero", "troop", "spell", "siege", "pet"} else 1)
            total_coins += coins
            total_eff += eff
            matches.append({
                "rank": rank,
                "key": key,
                "label": rec.get("label") or ITEMS[key].label,
                "coins": coins,
                "efficiency": eff,
                "category": cat,
            })

        return {"coins": total_coins, "efficiency": total_eff, "matches": matches}

    async def apply_path_rewards(self, user_id: str, player_tag: str | None, reward_state: dict[str, Any]) -> dict[str, Any]:
        coins = int(reward_state.get("coins", 0) or 0)
        efficiency = int(reward_state.get("efficiency", 0) or 0)
        matches = list(reward_state.get("matches") or [])
        if coins <= 0 and efficiency <= 0 and not matches:
            return await self.get_user_store(str(user_id), player_tag=player_tag)

        def patch(root: dict[str, Any], account: dict[str, Any]):
            econ = account.setdefault("advisor_economy", {})
            econ["coins"] = int(econ.get("coins", 0) or 0) + coins
            econ["efficiency_score"] = int(econ.get("efficiency_score", 0) or 0) + efficiency
            econ["followed_paths"] = int(econ.get("followed_paths", 0) or 0) + len(matches)
            econ["last_award_at"] = datetime.now(timezone.utc).isoformat()

        await self.save_user_patch(str(user_id), patch, player_tag=player_tag)
        return await self.get_user_store(str(user_id), player_tag=player_tag)

    def build_reward_result_block(self, reward_state: dict[str, Any]) -> str:
        matches = list(reward_state.get("matches") or [])
        if not matches:
            return "No active path rewards earned this time."
        lines = [f"🪙 **+{int(reward_state.get('coins', 0))} coins** · 📈 **+{int(reward_state.get('efficiency', 0))} efficiency**"]
        for match in matches[:3]:
            lines.append(f"#{match['rank']} {match['label']} → +{match['coins']} coins / +{match['efficiency']} eff")
        return "\n".join(lines)

    def build_next_reward_block(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        achieved = state["achieved"]
        groups = state["group_status"]
        percent = int(state["progress"].get("percent", 0))

        progress_lines: list[str] = []
        for mark in MILESTONE_PROGRESS_MARKS:
            if percent < mark:
                remaining = mark - percent
                progress_lines.append(f"📈 **{mark}% progress** → +{mark_reward(mark)} coins (**{remaining}%** more)")
                break

        milestone_lines: list[str] = []
        if not achieved.get("heroes_complete") and groups["heroes"]["total"] > 0:
            remaining = groups["heroes"]["total"] - groups["heroes"]["done"]
            milestone_lines.append(f"🏆 **Heroes Complete** → +75 coins (**{remaining}** left)")
        if not achieved.get("offense_core_complete") and groups["offense"]["total"] > 0:
            remaining = groups["offense"]["total"] - groups["offense"]["done"]
            milestone_lines.append(f"⚔️ **Offense Core Complete** → +100 coins (**{remaining}** left)")
        if not achieved.get("builder_core_complete") and groups["builder"]["total"] > 0:
            remaining = groups["builder"]["total"] - groups["builder"]["done"]
            milestone_lines.append(f"🧱 **Builder Core Complete** → +100 coins (**{remaining}** left)")
        if not achieved.get("war_ready"):
            milestone_lines.append("🔥 **War Ready** → +150 coins (heroes + offense core + **60%** progress)")

        lines = progress_lines + milestone_lines[:2]
        if not lines:
            return "✅ All current advisor rewards are unlocked. Raise your targets to create the next milestone."
        return "\n".join(lines[:3])


    def get_untracked_goals(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        manual_levels = user.get("manual_levels") or {}
        manual_copy_levels = self.get_manual_copy_levels(user)
        goals: list[dict[str, Any]] = []

        for key in sorted(targets):
            meta = ITEMS.get(key)
            if not meta:
                continue
            target = int(targets.get(key, 0) or 0)
            current = int(levels.get(key, 0) or 0)
            category = str(meta.category or "other")
            copy_cap = self.get_item_copy_cap(user.get("town_hall"), key)
            status = self.get_item_status(user, key, targets=targets, levels=levels)

            if meta.source == "manual":
                if copy_cap > 1:
                    # A plain /trackupgrade on a multi-copy manual item is treated as
                    # all copies being at the same level. /trackcopies remains the
                    # detailed path for mixed-level copies.
                    tracked_copies = copy_cap if key in manual_levels and key not in manual_copy_levels else int(status.get("tracked_copies", 0))
                    if tracked_copies < copy_cap:
                        goals.append({
                            "key": key,
                            "label": meta.label,
                            "category": category,
                            "lane": meta.lane,
                            "target": target,
                            "current": current,
                            "copy_cap": copy_cap,
                            "tracked_copies": tracked_copies,
                            "remaining": copy_cap - tracked_copies,
                            "reason": f"{tracked_copies}/{copy_cap} copies tracked",
                            "kind": "partial_multi_copy",
                        })
                elif key not in manual_levels and key not in manual_copy_levels:
                    goals.append({
                        "key": key,
                        "label": meta.label,
                        "category": category,
                        "lane": meta.lane,
                        "target": target,
                        "current": current,
                        "copy_cap": 1,
                        "tracked_copies": 0,
                        "remaining": 1,
                        "reason": f"Current target {target}",
                        "kind": "missing_manual",
                    })

        def _sort_key(goal: dict[str, Any]):
            priority = 0 if goal.get("lane") == "hero" else (1 if goal.get("lane") == "lab" else 2)
            remaining = int(goal.get("remaining", 0) or 0)
            return (priority, -remaining, str(goal.get("label", "")))

        goals.sort(key=_sort_key)
        return goals

    def build_untracked_goal_summary(self, user: dict[str, Any]) -> str:
        goals = self.get_untracked_goals(user)
        if not goals:
            return "✅ All current advisor goals are tracked."

        category_counts: dict[str, int] = {}
        for goal in goals:
            category_counts[goal["category"]] = category_counts.get(goal["category"], 0) + 1

        parts: list[str] = []
        for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {count}")
        return f"{len(goals)} missing · " + " · ".join(parts)

    def build_untracked_goals_block(self, user: dict[str, Any], limit: int = 8) -> str:
        goals = self.get_untracked_goals(user)
        if not goals:
            return "✅ All current advisor goals are already tracked."

        grouped: dict[str, list[dict[str, Any]]] = {}
        for goal in goals:
            grouped.setdefault(goal["category"], []).append(goal)

        ordered_groups = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        lines: list[str] = [f"Still missing **{len(goals)}** advisor tracking goal(s):"]
        used = 0
        for category, items in ordered_groups:
            if used >= limit:
                continue
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            lines.append(f"{emoji} **{category.replace('_', ' ').title()}** ({len(items)})")
            for goal in items:
                if used >= limit:
                    break
                if goal.get("kind") == "partial_multi_copy":
                    lines.append(
                        f"• {goal['label']} — **{goal['tracked_copies']}/{goal['copy_cap']}** copies tracked (target **{goal['target']}**)"
                    )
                else:
                    lines.append(
                        f"• {goal['label']} — not tracked yet (target **{goal['target']}**)"
                    )
                used += 1
        if len(goals) > used:
            lines.append(f"…and **{len(goals) - used}** more advisor tracking goal(s).")
        return "\n".join(lines)


    def build_untracked_goal_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        goals = self.get_untracked_goals(user)
        grouped: dict[str, list[dict[str, Any]]] = {}
        missing_items = 0
        partial_items = 0
        missing_slots = 0

        for goal in goals:
            category = str(goal.get("category") or "other")
            grouped.setdefault(category, []).append(goal)
            remaining = max(1, int(goal.get("remaining", 1) or 1))
            missing_slots += remaining
            if goal.get("kind") == "partial_multi_copy":
                partial_items += 1
            else:
                missing_items += 1

        ordered_groups = dict(sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])))
        return {
            "items": len(goals),
            "missing_items": missing_items,
            "partial_items": partial_items,
            "missing_slots": missing_slots,
            "groups": ordered_groups,
        }

    def build_untracked_goal_callout(self, user: dict[str, Any]) -> str:
        snapshot = self.build_untracked_goal_snapshot(user)
        total_items = int(snapshot.get("items", 0) or 0)
        if total_items <= 0:
            return "✅ Missing input: none."

        parts: list[str] = [f"Missing input: {total_items} item(s)"]
        missing_slots = int(snapshot.get("missing_slots", 0) or 0)
        if missing_slots > total_items:
            parts.append(f"{missing_slots} tracking slot(s)")
        partial_items = int(snapshot.get("partial_items", 0) or 0)
        if partial_items:
            parts.append(f"{partial_items} partial multi-copy")
        top_groups = list((snapshot.get("groups") or {}).items())[:2]
        for category, items in top_groups:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {len(items)}")
        parts.append("Use /missinggoals")
        return " · ".join(parts)

    def _format_untracked_goal_line(self, goal: dict[str, Any]) -> str:
        if goal.get("kind") == "partial_multi_copy":
            tracked_copies = int(goal.get("tracked_copies", 0) or 0)
            copy_cap = int(goal.get("copy_cap", 1) or 1)
            target = int(goal.get("target", 0) or 0)
            return f"• {goal['label']} — {tracked_copies}/{copy_cap} copies tracked (target {target})"
        target = int(goal.get("target", 0) or 0)
        return f"• {goal['label']} — not tracked yet (target {target})"

    def build_untracked_goals_export_text(self, user: dict[str, Any]) -> str:
        snapshot = self.build_untracked_goal_snapshot(user)
        total_items = int(snapshot.get("items", 0) or 0)
        player_name = user.get("player_name") or "Unknown"
        tag = user.get("player_tag") or ""
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()

        lines: list[str] = [
            f"Missing Goal Input Report",
            f"Account: {player_name} ({tag})",
            f"Town Hall: {th}",
            f"Role: {role}",
            "",
        ]

        if total_items <= 0:
            lines.append("All current advisor goals are already tracked.")
            return "\n".join(lines)

        missing_items = int(snapshot.get("missing_items", 0) or 0)
        partial_items = int(snapshot.get("partial_items", 0) or 0)
        missing_slots = int(snapshot.get("missing_slots", 0) or 0)
        lines.extend([
            f"Missing input items: {total_items}",
            f"Fully missing items: {missing_items}",
            f"Partial multi-copy items: {partial_items}",
            f"Missing tracking slots: {missing_slots}",
            "",
            "Items grouped by category:",
        ])

        for category, items in (snapshot.get("groups") or {}).items():
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            lines.append(f"")
            lines.append(f"{emoji} {category.replace('_', ' ').title()} ({len(items)})")
            for goal in items:
                lines.append(self._format_untracked_goal_line(goal))

        lines.extend([
            "",
            "Tips:",
            "- Use /trackupgrade for single-level manual items and manual overrides.",
            "- Use /trackcopies for multi-copy buildings/traps when copies are not all the same level.",
            "- Auto-synced troop/spell/hero/pet data still counts toward progress when available, but manual-only items must be entered by hand.",
        ])
        return "\n".join(lines)

    def get_remaining_goals(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        goals: list[dict[str, Any]] = []

        for key in sorted(targets):
            meta = ITEMS.get(key)
            if not meta:
                continue
            status = self.get_item_status(user, key, targets=targets, levels=levels)
            tracked = int(status.get("tracked", 0) or 0)
            done = int(status.get("done", 0) or 0)
            remaining = max(tracked - done, 0)
            if remaining <= 0:
                continue

            target = int(targets.get(key, 0) or 0)
            current = int(status.get("current", 0) or 0)
            category = str(meta.category or "other")
            entry = {
                "key": key,
                "label": meta.label,
                "category": category,
                "lane": meta.lane,
                "target": target,
                "current": current,
                "tracked": tracked,
                "done": done,
                "remaining": remaining,
                "multi_copy": bool(status.get("multi_copy")),
                "copy_cap": int(status.get("copy_cap", 1) or 1),
                "tracked_copies": int(status.get("tracked_copies", 0) or 0),
                "fully_confirmed": bool(status.get("fully_confirmed", False)),
                "copy_levels": list(status.get("copy_levels") or []),
            }
            if entry["multi_copy"]:
                entry["highest"] = int(status.get("highest", current) or current)
                entry["lowest"] = current
            goals.append(entry)

        def _sort_key(goal: dict[str, Any]):
            lane_priority = 0 if goal.get("lane") == "hero" else (1 if goal.get("lane") == "lab" else 2)
            remaining = int(goal.get("remaining", 0) or 0)
            gap = max(int(goal.get("target", 0) or 0) - int(goal.get("current", 0) or 0), 0)
            return (lane_priority, -remaining, -gap, str(goal.get("label", "")))

        goals.sort(key=_sort_key)
        return goals

    def build_remaining_goal_summary(self, user: dict[str, Any]) -> str:
        goals = self.get_remaining_goals(user)
        if not goals:
            return "✅ All tracked goals are complete."

        category_counts: dict[str, int] = {}
        for goal in goals:
            category_counts[goal["category"]] = category_counts.get(goal["category"], 0) + int(goal.get("remaining", 1) or 1)

        parts: list[str] = []
        for category, count in sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]:
            parts.append(f"{CATEGORY_EMOJIS.get(category, '📌')} {category.replace('_', ' ').title()} {count}")
        return f"{sum(int(goal.get('remaining', 0) or 0) for goal in goals)} remaining · " + " · ".join(parts)

    def build_remaining_goals_block(self, user: dict[str, Any], limit: int = 8) -> str:
        goals = self.get_remaining_goals(user)
        if not goals:
            return "✅ All tracked goals are complete."

        lines: list[str] = [f"Still need to finish **{sum(int(goal.get('remaining', 0) or 0) for goal in goals)}** tracked goal(s):"]
        used = 0
        shown_remaining = 0
        for goal in goals:
            if used >= limit:
                break
            shown_remaining += int(goal.get("remaining", 0) or 0)
            if goal.get("multi_copy"):
                current_best = int(goal.get("highest", goal.get("current", 0)) or 0)
                tracked_copies = int(goal.get("tracked_copies", 0) or 0)
                copy_cap = int(goal.get("copy_cap", 1) or 1)
                if tracked_copies < copy_cap:
                    lines.append(
                        f"• {goal['label']} — **{goal['done']}/{goal['tracked']}** copies at target **{goal['target']}** ({tracked_copies}/{copy_cap} copies tracked)"
                    )
                else:
                    lines.append(
                        f"• {goal['label']} — **{goal['done']}/{goal['tracked']}** copies at target **{goal['target']}** (best tracked level **{current_best}**)"
                    )
            else:
                lines.append(
                    f"• {goal['label']} — level **{goal['current']} → {goal['target']}**"
                )
            used += 1
        total_remaining = sum(int(goal.get('remaining', 0) or 0) for goal in goals)
        hidden_remaining = max(total_remaining - shown_remaining, 0)
        if hidden_remaining > 0:
            lines.append(f"…and **{hidden_remaining}** more tracked goal(s) still to finish.")
        return "\n".join(lines)

    def get_missing_core_items(self, user: dict[str, Any]) -> list[dict[str, str]]:
        levels = self.get_effective_levels(user)
        targets = self.get_effective_targets(user)
        issues: list[dict[str, str]] = []
        seen: set[str] = set()

        def add_issue(issue_key: str, text: str):
            if issue_key in seen:
                return
            seen.add(issue_key)
            issues.append({"key": issue_key, "text": text})

        core_keys = HERO_KEYS | OFFENSE_CORE_KEYS | BUILDER_CORE_KEYS
        for key in sorted(core_keys):
            if key not in ITEMS or key not in targets:
                continue
            meta = ITEMS[key]
            target = int(targets.get(key, 0))
            current = int(levels.get(key, 0))
            if meta.source == "manual":
                if self.is_multi_copy_item(user.get("town_hall"), key):
                    status = self.get_item_status(user, key, targets=targets, levels=levels)
                    if int(status.get("tracked_copies", 0)) < int(status.get("copy_cap", 1)):
                        add_issue(key, f"Track all **{meta.label}** copies manually (**{status.get('tracked_copies', 0)}/{status.get('copy_cap', 1)}** entered) to confirm full progress.")
                        continue
                    if int(status.get("done", 0)) < int(status.get("tracked", 0)):
                        add_issue(key, f"{meta.label} has **{status.get('done', 0)}/{status.get('tracked', 0)}** copies at target **{target}**.")
                        continue
                elif key not in (user.get("manual_levels") or {}):
                    add_issue(key, f"Track **{meta.label}** manually (target **{target}**) to confirm core progress.")
                    continue
            if current < target:
                add_issue(key, f"{meta.label} is **{current}/{target}** (**{target - current}** away).")

        return issues

    def get_rewardable_sync_summary(self, before_user: dict[str, Any], after_user: dict[str, Any]) -> dict[str, Any]:
        before_state = self.get_milestone_state(before_user)
        after_state = self.get_milestone_state(after_user)

        before_achieved = before_state["achieved"]
        after_achieved = after_state["achieved"]

        new_progress_marks = sorted(
            set(after_achieved.get("progress_marks", [])) - set(before_achieved.get("progress_marks", []))
        )

        ordered_group_keys = [
            "heroes_complete",
            "offense_core_complete",
            "builder_core_complete",
            "war_ready",
        ]
        new_group_milestones = [
            key for key in ordered_group_keys
            if after_achieved.get(key) and not before_achieved.get(key)
        ]

        sync_day = None
        synced_at = after_user.get("last_synced_at")
        if synced_at:
            try:
                sync_day = datetime.fromisoformat(synced_at).astimezone(timezone.utc).date().isoformat()
            except Exception:
                sync_day = None

        return {
            "player_tag": after_user.get("player_tag"),
            "player_name": after_user.get("player_name", "Unknown"),
            "new_progress_marks": new_progress_marks,
            "new_group_milestones": new_group_milestones,
            "new_missing_core_fixes": max(0, len(self.get_missing_core_items(before_user)) - len(self.get_missing_core_items(after_user))),
            "should_reward_sync": bool(after_user.get("last_synced_at")),
            "sync_day": sync_day,
        }



    def _resolve_cap_item_key(self, category: str, item_name: str) -> str | None:
        category = str(category)
        item_name = str(item_name)
        item_key = TH_CAP_LOOKUP_TO_KEY.get((category, item_name))
        if item_key:
            return item_key
        if category == "army_buildings":
            return ARMY_BUILDING_CAP_NAME_ALIASES.get(item_name)
        return None


    def progress_bar(self, percent: int | float, length: int = 10, filled: str = "█", empty: str = "░") -> str:
        try:
            percent_value = float(percent)
        except Exception:
            percent_value = 0.0

        percent_value = max(0.0, min(percent_value, 100.0))
        filled_count = int(round((percent_value / 100.0) * length))
        filled_count = max(0, min(filled_count, length))
        empty_count = max(0, length - filled_count)
        return f"{filled * filled_count}{empty * empty_count}"

    def build_account_completion_snapshot(self, user: dict[str, Any]) -> dict[str, Any]:
        town_hall = int(user.get("town_hall") or 0)
        if town_hall <= 0:
            return {
                "town_hall": town_hall,
                "total_slots": 0,
                "supported_slots": 0,
                "supported_complete": 0,
                "supported_known": 0,
                "unsupported_slots": 0,
                "percent_complete": 0,
                "coverage_percent": 0,
                "completion_bar": "░░░░░░░░░░",
                "coverage_bar": "░░░░░░░░░░",
                "group_breakdown": {},
            }

        levels = self.get_effective_levels(user)
        groups: dict[str, dict[str, Any]] = {}
        total_slots = 0
        supported_slots = 0
        supported_complete = 0
        supported_known = 0
        unsupported_slots = 0

        for row in get_all_cap_items(town_hall, categories=list(ACCOUNT_COMPLETION_CATEGORIES)):
            category = str(row.get("category") or "other")
            item_name = str(row.get("item_name") or "Unknown")
            count = max(1, int(row.get("count", 1) or 1))
            max_level = max(0, int(row.get("max_level", 0) or 0))
            total_slots += count
            bucket = groups.setdefault(category, {
                "label": ACCOUNT_COMPLETION_CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
                "total": 0,
                "supported": 0,
                "known": 0,
                "complete": 0,
                "unsupported": 0,
            })
            bucket["total"] += count

            item_key = self._resolve_cap_item_key(category, item_name)
            if not item_key or item_key not in ITEMS:
                unsupported_slots += count
                bucket["unsupported"] += count
                continue

            supported_slots += count
            bucket["supported"] += count
            status = self.get_item_status(user, item_key, levels=levels)
            copy_cap = max(1, int(status.get("copy_cap", 1) or 1))

            if bool(status.get("multi_copy")):
                tracked_copies = min(count, int(status.get("tracked_copies", 0) or 0), copy_cap)
                copy_levels = list(status.get("copy_levels", []) or [])[:count]
                done_copies = sum(1 for lvl in copy_levels if max_level > 0 and int(lvl or 0) >= max_level)
                done_copies = min(count, done_copies, copy_cap)
                supported_known += tracked_copies
                supported_complete += done_copies
                bucket["known"] += tracked_copies
                bucket["complete"] += done_copies
            else:
                current = int(levels.get(item_key, 0) or 0)
                if current > 0 or item_key in (user.get("manual_levels") or {}) or item_key in (user.get("synced_levels") or {}):
                    supported_known += count
                    bucket["known"] += count
                if max_level > 0 and current >= max_level:
                    supported_complete += count
                    bucket["complete"] += count

        percent_complete = round((supported_complete / supported_slots) * 100) if supported_slots else 0
        coverage_percent = round((supported_known / supported_slots) * 100) if supported_slots else 0
        completion_bar = self.progress_bar(percent_complete)
        coverage_bar = self.progress_bar(coverage_percent)
        return {
            "town_hall": town_hall,
            "total_slots": total_slots,
            "supported_slots": supported_slots,
            "supported_complete": supported_complete,
            "supported_known": supported_known,
            "unsupported_slots": unsupported_slots,
            "unknown_supported": max(supported_slots - supported_known, 0),
            "remaining_supported": max(supported_slots - supported_complete, 0),
            "percent_complete": percent_complete,
            "coverage_percent": coverage_percent,
            "completion_bar": completion_bar,
            "coverage_bar": coverage_bar,
            "group_breakdown": groups,
        }

    def get_missing_account_data(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        town_hall = int(user.get("town_hall") or 0)
        if town_hall <= 0:
            return []
        levels = self.get_effective_levels(user)
        manual_levels = user.get("manual_levels") or {}
        synced_levels = user.get("synced_levels") or {}
        missing: list[dict[str, Any]] = []
        for row in get_all_cap_items(town_hall, categories=list(ACCOUNT_COMPLETION_CATEGORIES)):
            category = str(row.get("category") or "other")
            item_name = str(row.get("item_name") or "Unknown")
            count = max(1, int(row.get("count", 1) or 1))
            max_level = max(0, int(row.get("max_level", 0) or 0))
            item_key = self._resolve_cap_item_key(category, item_name)
            if not item_key or item_key not in ITEMS:
                continue
            status = self.get_item_status(user, item_key, levels=levels)
            label = ITEMS[item_key].label
            if bool(status.get("multi_copy")):
                tracked_copies = min(count, int(status.get("tracked_copies", 0) or 0))
                missing_copies = max(0, count - tracked_copies)
                if missing_copies <= 0:
                    continue
                copy_levels = list(status.get("copy_levels", []) or [])[:tracked_copies]
                missing.append({
                    "key": item_key, "label": label, "category": category, "count": count,
                    "known": tracked_copies, "missing": missing_copies, "max_level": max_level,
                    "kind": "partial_multi_copy" if tracked_copies else "missing_multi_copy",
                    "tracked_summary": self.summarize_copy_levels([int(v or 0) for v in copy_levels]) if copy_levels else "none",
                    "hint": f"Use /trackcopies item:{item_key} levels_csv:<level>x<count>,...",
                })
                continue
            current = int(levels.get(item_key, 0) or 0)
            known = current > 0 or item_key in manual_levels or item_key in synced_levels
            if not known:
                missing.append({
                    "key": item_key, "label": label, "category": category, "count": count,
                    "known": 0, "missing": count, "max_level": max_level,
                    "kind": "missing_single", "tracked_summary": "none",
                    "hint": f"Use /trackupgrade item:{item_key} current_level:<level>",
                })
        category_order = {name: index for index, name in enumerate(ACCOUNT_COMPLETION_CATEGORIES)}
        missing.sort(key=lambda row: (category_order.get(str(row.get("category") or ""), 999), -int(row.get("missing", 0) or 0), str(row.get("label") or "")))
        return missing

    def build_missing_account_data_export_text(self, user: dict[str, Any]) -> str:
        missing = self.get_missing_account_data(user)
        account = self.build_account_completion_snapshot(user)
        player_name = user.get("player_name") or "Unknown"
        town_hall = user.get("town_hall") or "?"
        lines = [
            f"Missing Account Data Report for {player_name} · TH{town_hall}",
            "",
            f"Coverage: {account.get('supported_known', 0)}/{account.get('supported_slots', 0)} supported TH slots known ({account.get('coverage_percent', 0)}%)",
            f"Missing supported slots: {sum(int(row.get('missing', 0) or 0) for row in missing)}",
            "",
        ]
        if not missing:
            lines.append("No missing supported account-completion data.")
            return "\n".join(lines)
        current_category = None
        for row in missing:
            category = str(row.get("category") or "other")
            if category != current_category:
                current_category = category
                label = ACCOUNT_COMPLETION_CATEGORY_LABELS.get(category, category.replace("_", " ").title())
                lines.extend(["", f"[{label}]"])
            count = int(row.get("count", 0) or 0)
            known = int(row.get("known", 0) or 0)
            missing_count = int(row.get("missing", 0) or 0)
            max_level = int(row.get("max_level", 0) or 0)
            lines.append(f"- {row.get('label')}: missing {missing_count}/{count} known level slot(s); known {known}/{count}; TH max {max_level}; tracked: {row.get('tracked_summary')}; key: {row.get('key')}")
            lines.append(f"  Hint: {row.get('hint')}")
        return "\n".join(lines).strip() + "\n"

    def _format_missing_account_data_line(self, row: dict[str, Any]) -> str:
        missing_count = int(row.get("missing", 0) or 0)
        count = int(row.get("count", 0) or 0)
        known = int(row.get("known", 0) or 0)
        max_level = int(row.get("max_level", 0) or 0)
        label = str(row.get("label") or row.get("key") or "Unknown")
        key = str(row.get("key") or "")
        tracked = str(row.get("tracked_summary") or "none")
        if count > 1:
            return f"• **{label}** (`{key}`): missing **{missing_count}/{count}** slots · known **{known}/{count}** · TH max **{max_level}** · tracked: {tracked}"
        return f"• **{label}** (`{key}`): missing current level · TH max **{max_level}**"

    def build_account_completion_summary(self, user: dict[str, Any]) -> str:
        snap = self.build_account_completion_snapshot(user)
        if int(snap.get("supported_slots", 0) or 0) <= 0:
            return "No TH account-completion scope is available yet for this account."
        parts = [
            f"{snap['completion_bar']} {snap['percent_complete']}% (**{snap['supported_complete']} / {snap['supported_slots']}** supported slots maxed)",
            f"Coverage: {snap['coverage_bar']} {snap['coverage_percent']}% (**{snap['supported_known']} / {snap['supported_slots']}** supported slots have known data)",
        ]
        unsupported = int(snap.get("unsupported_slots", 0) or 0)
        if unsupported:
            parts.append(f"Outside Current Model: **{unsupported}** TH slot(s) are not yet part of the bot's full-account data model.")
        return "\n".join(parts)

    def build_recommendation_pool_snapshot(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> dict[str, Any]:
        top, pool = self.build_recommendation_pool(
            user,
            count=5,
            pool_size=12,
            requested_mode=requested_mode,
            builder_idle=builder_idle,
            lab_idle=lab_idle,
        )
        by_lane: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for rec in pool:
            lane = str(rec.get("lane") or "builder")
            category = str(rec.get("category") or "other")
            by_lane[lane] = by_lane.get(lane, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
        ordered_categories = sorted(by_category.items(), key=lambda kv: (RECOMMENDATION_PRIORITIES.get(kv[0], 99), -kv[1], kv[0]))
        ordered_lanes = sorted(by_lane.items(), key=lambda kv: (kv[0] not in {"hero", "lab", "builder"}, kv[0]))
        return {
            "top": top,
            "pool": pool,
            "pool_size": len(pool),
            "top_size": len(top),
            "by_lane": ordered_lanes,
            "by_category": ordered_categories,
        }

    def build_recommendation_pool_summary(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> str:
        snap = self.build_recommendation_pool_snapshot(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        pool = snap.get("pool") or []
        if not pool:
            return "No upgrade is currently below your advisor targets."
        bits = [f"Top picks: **{snap['top_size']}** · Recommendation Pool: **{snap['pool_size']}**"]
        if snap.get("by_lane"):
            lane_bits = [f"{LANE_EMOJIS.get(lane, '📌')} {lane.title()} {count}" for lane, count in snap["by_lane"][:3]]
            bits.append("Lanes: " + " · ".join(lane_bits))
        if snap.get("by_category"):
            cat_bits = [f"{CATEGORY_EMOJIS.get(cat, '📌')} {cat.replace('_', ' ').title()} {count}" for cat, count in snap["by_category"][:3]]
            bits.append("Mix: " + " · ".join(cat_bits))
        return "\n".join(bits)

    def build_three_concepts_summary(self, user: dict[str, Any], requested_mode: str | None = None, builder_idle: bool | None = None, lab_idle: bool | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        account = self.build_account_completion_snapshot(user)
        pool = self.build_recommendation_pool_snapshot(user, requested_mode=requested_mode, builder_idle=builder_idle, lab_idle=lab_idle)
        return (
            f"**Advisor Progress** → **{progress['done']} / {progress['tracked']}** advisor targets done ({progress['percent']}%).\n"
            f"**Account Completion** → **{account['supported_complete']} / {account['supported_slots']}** modeled TH slots maxed ({account['percent_complete']}%).\n"
            f"**Recommendation Pool** → **{pool['pool_size']}** eligible upgrade options currently under target; top **{pool['top_size']}** are surfaced first."
        )

    def format_top_block(self, recs: list[dict[str, Any]]) -> str:
        chunks = []
        for rec in recs:
            chunks.append(
                f"**{rec['priority']}** - {rec['label']} → {rec['next_level']}  \n"
                f"Score: **{rec['score']}** | Current: {rec['current']} | Target: {rec['target']}\n"
                + "\n".join(f"• {reason}" for reason in rec["reasons"])
            )
        return "\n\n".join(chunks)

    def profile_summary(self, user: dict[str, Any]) -> str:
        role = user.get("role", DEFAULT_ROLE).title()
        player_name = user.get("player_name") or "Unknown"
        player_tag = user.get("player_tag") or "No account selected"
        th = user.get("town_hall") or "?"
        synced_at = user.get("last_synced_at")
        sync_text = "Never"
        if synced_at:
            try:
                sync_text = discord.utils.format_dt(datetime.fromisoformat(synced_at), style="R")
            except Exception:
                sync_text = synced_at
        return f"Account: **{player_name}** ({player_tag}) | TH **{th}** | Role: **{role}** | Last sync: {sync_text}"

    
    def build_progress_explainer(self, user: dict[str, Any]) -> str:
        progress = self.build_progress_snapshot(user)
        account = self.build_account_completion_snapshot(user)
        tracking = self.build_tracking_snapshot(user)
        return (
            f"**Advisor progress** is your curated upgrade-path score: **{progress['done']} / {progress['tracked']}** targets complete. "
            f"**Account completion** is separate: **{account['supported_complete']} / {account['supported_slots']}** modeled TH slots are maxed. "
            f"**Tracking coverage** is **{tracking['tracked']} / {tracking['total']}**, so the advisor is scoring from confirmed data. "
            f"Multi-copy buildings/traps only count fully once all copies are tracked manually."
        )
    
        
    def build_data_source_summary(self, user: dict[str, Any]) -> str:
        synced = len(user.get("synced_levels", {}))
        manual = len(user.get("manual_levels", {}))
        account = self.build_account_completion_snapshot(user)
        return (
            f"Auto-synced from Clash API: **{synced}** hero/lab/pet items\n"
            f"Manual entries: **{manual}** (used for buildings, copy tracking, and overrides)\n"
            f"Supported account-completion scope: **{account['supported_slots']}** TH slots modeled right now\n"
            f"Note: many buildings/defenses/traps still depend on manual entry until broader sync is added."
        )

    def build_milestone_status_block(self, user: dict[str, Any]) -> str:
        state = self.get_milestone_state(user)
        groups = state["group_status"]
        achieved = state["achieved"]
        progress = state["progress"]
        return (
            f"Overall advisor completion: **{progress['percent']}%**\n"
            f"Heroes confirmed at target: **{groups['heroes']['done']}/{groups['heroes']['total']}**\n"
            f"Offense core confirmed at target: **{groups['offense']['done']}/{groups['offense']['total']}**\n"
            f"Builder core confirmed at target: **{groups['builder']['done']}/{groups['builder']['total']}**\n"
            f"War-ready checkpoint: **{'Yes' if achieved.get('war_ready') else 'Not yet'}**\n"
            f"*Core milestone counts ignore untracked building/trap copies until you add them manually.*"
        )

    def _html_escape(self, value: Any) -> str:
        return html.escape(str(value if value is not None else ""))

    def _slugify_icon_name(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        for src, dest in (("&", " and "), (".", " "), ("-", " "), ("/", " "), ("'", "")):
            text = text.replace(src, dest)
        return "_".join(part for part in text.replace("__", "_").split() if part)

    def _ensure_asset_index(self) -> dict[str, str]:
        if self._asset_index is not None:
            return self._asset_index
        index: dict[str, str] = {}
        roots = [self.assets_dir]
        if self.assets_dir.name != "icons":
            roots.append(self.assets_dir / "icons")
        allowed_suffixes = {".png", ".webp", ".jpg", ".jpeg", ".svg"}
        for root in roots:
            if not root.exists():
                continue
            try:
                for file in root.rglob("*"):
                    if not file.is_file() or file.suffix.lower() not in allowed_suffixes:
                        continue
                    stem = self._slugify_icon_name(file.stem)
                    if stem and stem not in index:
                        index[stem] = file.resolve().as_posix()
            except Exception:
                continue
        self._asset_index = index
        return index

    def _find_icon_path(self, icon_key: Any, *, label: Any = None, category: Any = None, kind: str = "item") -> str | None:
        cache_key = (kind, str(icon_key or label or ""))
        if cache_key in self._icon_path_cache:
            return self._icon_path_cache[cache_key]

        candidates: list[str] = []
        raw_icon_key = str(icon_key or "")
        raw_label = str(label or "")
        icon_slug = self._slugify_icon_name(raw_icon_key)
        label_slug = self._slugify_icon_name(raw_label)

        if kind == "item":
            # Try explicit repo asset aliases first. This covers plural advisor keys
            # and labels that differ from normalized asset stems.
            for key in (raw_icon_key, icon_slug, raw_label, label_slug):
                if not key:
                    continue
                mapped_asset = ITEM_ICON_ASSET_MAP.get(key) or ITEM_ICON_NAME_ALIASES.get(key)
                if mapped_asset:
                    candidates.append(self._slugify_icon_name(mapped_asset))

        if icon_key:
            candidates.append(icon_slug)
        if label:
            candidates.append(label_slug)

        if kind == "item" and icon_key:
            mapped = TH_CAP_NAME_MAP.get(str(icon_key))
            if mapped:
                mapped_label = mapped[1]
                candidates.append(self._slugify_icon_name(mapped_label))
                alias_asset = ITEM_ICON_NAME_ALIASES.get(mapped_label)
                if alias_asset:
                    candidates.append(self._slugify_icon_name(alias_asset))
            if str(icon_key).endswith("_spell"):
                candidates.append(self._slugify_icon_name(str(icon_key).replace("_spell", "")))
            if str(icon_key).endswith("s"):
                singular_slug = self._slugify_icon_name(str(icon_key)[:-1])
                candidates.append(singular_slug)
                mapped_asset = ITEM_ICON_ASSET_MAP.get(singular_slug)
                if mapped_asset:
                    candidates.append(self._slugify_icon_name(mapped_asset))

        if kind == "ui":
            ui_aliases = {
                "hero": ["heroes", "hero"],
                "lab": ["laboratory", "lab"],
                "builder": ["builder", "buildings"],
                "troop": ["troops", "troop"],
                "spell": ["spells", "spell"],
                "siege": ["siege_machine", "siege"],
                "pet": ["pets", "pet"],
                "building": ["town_hall", "building"],
                "economy": ["gold_storage", "economy", "gold"],
                "defense": ["shield", "defense"],
                "trap": ["bomb", "trap"],
                "war": ["crossed_swords", "war"],
                "farm": ["elixir_collector", "farm"],
                "auto": ["brain", "auto"],
                "now": ["flame", "now"],
                "soon": ["lightning", "soon"],
                "save_for": ["coin", "save_for"],
                "wait": ["hourglass", "wait"],
            }
            candidates.extend(ui_aliases.get(str(icon_key or "").lower(), []))

        if category and kind == "item":
            candidates.append(self._slugify_icon_name(category))

        index = self._ensure_asset_index()
        seen: set[str] = set()
        match: str | None = None
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            match = index.get(candidate)
            if match:
                break

        self._icon_path_cache[cache_key] = match
        return match

    def _render_icon_html(self, *, icon_key: Any = None, label: Any = None, category: Any = None, fallback: str = "📌", kind: str = "item", css_class: str = "icon") -> str:
        path = self._find_icon_path(icon_key, label=label, category=category, kind=kind)
        if path:
            try:
                file_path = Path(path).resolve()
                mime_type, _ = mimetypes.guess_type(str(file_path))
                mime_type = mime_type or "image/png"
                encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
                src = f"data:{mime_type};base64,{encoded}"
            except Exception as exc:
                print(f"[ICON ERROR] Failed loading icon {path}: {exc}")
                src = None
            if src:
                alt = self._html_escape(label or icon_key or fallback)
                return f'<img src="{src}" alt="{alt}" class="{css_class}">'
        return f'<span class="{css_class} emoji-fallback">{self._html_escape(fallback)}</span>'
    def _truncate_for_embed(self, value: Any, limit: int = 1000) -> str:
        text = str(value if value is not None else "")
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def _safe_followup_embed_field(self, embed: discord.Embed, *, name: str, value: Any, inline: bool = False, limit: int = 1000) -> None:
        safe_value = self._truncate_for_embed(value or "—", limit=limit)
        embed.add_field(name=name, value=safe_value or "—", inline=inline)

    def _render_card_progress_bar(self, current: int, target: int) -> tuple[int, str]:
        target = max(1, int(target or 1))
        current = max(0, min(int(current or 0), target))
        pct = int(round((current / target) * 100))
        return max(0, min(100, pct)), f"{current}/{target}"

    def _render_metric_row_html(self, label: str, done: int, total: int, icon: str = "📌") -> str:
        pct, ratio = self._render_card_progress_bar(done, total)
        icon_html = self._render_icon_html(icon_key=icon, label=label, fallback=icon, kind="ui", css_class="metric-icon")
        return f'''
        <div class="metric-row">
            <div class="metric-label">{icon_html}<span>{self._html_escape(label)}</span></div>
            <div class="metric-bar"><div class="metric-fill" style="width: {pct}%"></div></div>
            <div class="metric-value">{self._html_escape(ratio)} · {pct}%</div>
        </div>
        '''

    def _render_summary_card_html(self, label: str, value: str, icon: str = "📌") -> str:
        icon_html = self._render_icon_html(icon_key=icon, label=label, fallback=icon, kind="ui", css_class="summary-icon")
        return (
            '<div class="summary-card">'
            f'<div class="label">{icon_html}{self._html_escape(label)}</div>'
            f'<div class="value">{self._html_escape(value)}</div>'
            '</div>'
        )

    def _priority_tone(self, rec: dict[str, Any], idx: int = 0) -> str:
        if idx == 1:
            return "top"
        score = float(rec.get("score", 0) or 0)
        priority = str(rec.get("priority", "")).lower()
        if priority == "high" or score >= 14:
            return "high"
        if priority == "medium" or score >= 9:
            return "medium"
        return "low"

    def _tone_meta(self, tone: str) -> tuple[str, str]:
        mapping = {
            "top": ("Top pick", "🔥"),
            "high": ("High value", "🟢"),
            "medium": ("Solid value", "🟡"),
            "low": ("Can wait", "🔴"),
        }
        return mapping.get(tone, ("Recommended", "📌"))

    def _format_days_eta_text(self, days_value: Any, *, empty: str = "Need more syncs") -> tuple[str, str]:
        """Return compact ETA value/subtitle for advisor-target completion."""
        try:
            if days_value is None:
                return empty, "sync a few more times"
            eta_days = max(0.0, float(days_value))
        except (TypeError, ValueError):
            return empty, "sync a few more times"
        days = int(eta_days)
        hours = int(round((eta_days - days) * 24))
        if hours == 24:
            days += 1
            hours = 0
        if days > 0 and hours > 0:
            return f"~{days}d {hours}h", "to advisor completion"
        if days > 0:
            return f"~{days}d", "to advisor completion"
        return f"~{max(hours, 1)}h", "to advisor completion"

    def _rec_identity(self, rec: dict[str, Any] | None) -> str:
        if not isinstance(rec, dict):
            return ""
        return str(rec.get("key") or rec.get("item_key") or rec.get("label") or "").strip().lower()

    def _war_ready_blocker_note(self, user: dict[str, Any], *, limit: int = 3) -> str:
        state = self.get_milestone_state(user)
        if dict(state.get("achieved") or {}).get("war_ready"):
            return "✅ War Ready complete."
        groups = dict(state.get("group_status") or {})
        labels = [("Heroes", "heroes"), ("Offense", "offense"), ("Core Buildings", "builder")]
        missing: list[str] = []
        for label, key in labels:
            row = dict(groups.get(key) or {})
            total = int(row.get("total", 0) or 0)
            done = int(row.get("done", 0) or 0)
            remain = max(0, total - done)
            if remain:
                missing.append(f"{remain} {label.lower()} goal(s)")
        if missing:
            return f"War Ready blockers: {', '.join(missing[:limit])}."
        return "War Ready blockers: advisor target requirements are still incomplete."

    def _lowest_account_category_note(self, account: dict[str, Any]) -> str:
        groups = dict(account.get("group_breakdown") or {})
        weakest: tuple[str, int, int, int] | None = None
        for key, row_any in groups.items():
            row = dict(row_any or {})
            total = int(row.get("supported", 0) or 0)
            if total <= 0:
                continue
            complete = int(row.get("complete", 0) or 0)
            pct = int(round((complete / max(1, total)) * 100))
            if weakest is None or pct < weakest[3]:
                weakest = (str(key), complete, total, pct)
        if not weakest:
            return "All supported categories are fully covered."
        key, complete, total, pct = weakest
        label = ACCOUNT_COMPLETION_CATEGORY_LABELS.get(key, key.replace("_", " ").title())
        return f"Lowest account category: {label} ({complete}/{total} · {pct}%)."

    def _render_status_note_html(self, text: str, icon: str = "ⓘ") -> str:
        return f'<div class="status-note"><span>{self._html_escape(icon)}</span><span>{self._html_escape(text)}</span></div>'

    def _render_upgrade_pick_row_html(self, rec: dict[str, Any], idx: int) -> str:
        meta = ITEMS.get(rec.get("key") or rec.get("item_key"))
        lane_key = rec.get("lane", "")
        category_key = getattr(meta, "category", "")
        timing_key = self.classify_recommendation_timing(rec)
        lane_emoji = LANE_EMOJIS.get(lane_key, "📌")
        category_emoji = CATEGORY_EMOJIS.get(category_key, "📌")
        timing_emoji = TIMING_EMOJIS.get(timing_key, "📌")
        current = int(rec.get("current", 0) or 0)
        target = int(rec.get("target", 1) or 1)
        pct, ratio = self._render_card_progress_bar(current, target)
        reason = (rec.get("reasons") or ["Good overall value right now."])[0]
        gap = max(0, target - current)
        score = rec.get("score", 0)
        label = rec.get("label", "Upgrade")
        next_level = rec.get("next_level", current + 1)
        tone = self._priority_tone(rec, idx)
        tone_label, tone_emoji = self._tone_meta(tone)
        highlight_class = " top-pick" if idx == 1 else ""
        item_icon_html = self._render_icon_html(icon_key=rec.get("key") or rec.get("item_key"), label=label, category=category_key, fallback=category_emoji, kind="item", css_class="unit-icon")
        lane_icon_html = self._render_icon_html(icon_key=lane_key, label=lane_key, fallback=lane_emoji, kind="ui", css_class="pill-icon")
        category_icon_html = self._render_icon_html(icon_key=category_key, label=category_key, fallback=category_emoji, kind="ui", css_class="pill-icon")
        timing_icon_html = self._render_icon_html(icon_key=timing_key, label=timing_key, fallback=timing_emoji, kind="ui", css_class="pill-icon")
        return f'''        <div class="donation-row upgrade-row tone-{tone}{highlight_class}">
            <div class="donation-rank">#{idx}</div>
            <div class="donation-main">
                <div class="donation-name">{item_icon_html}<span>{self._html_escape(label)}</span> <span class="pill">{lane_icon_html}{category_icon_html}{timing_icon_html}</span></div>
                <div class="upgrade-sub">Lvl {current} → {next_level} of {target} <span class="tone-badge">{tone_emoji} {self._html_escape(tone_label)}</span></div>
                <div class="donation-bar"><div class="donation-fill tone-{tone}" style="width: {pct}%"></div></div>
                <div class="upgrade-reason">{self._html_escape(reason)}</div>
            </div>
            <div class="donation-stats">
                <div><strong>{ratio}</strong> complete</div>
                <div>Gap <strong>{gap}</strong></div>
                <div>Score <strong>{self._html_escape(score)}</strong></div>
            </div>
        </div>
        '''

    def _render_lane_tiles_html(self, recs: list[dict[str, Any]]) -> str:
        lane_rows: dict[str, list[dict[str, Any]]] = {"hero": [], "lab": [], "builder": []}
        for rec in recs or []:
            lane_rows.setdefault(rec.get("lane", "builder"), []).append(rec)
        cards: list[str] = []
        for lane in ("hero", "lab", "builder"):
            items = lane_rows.get(lane) or []
            best = items[0] if items else None
            label = f"{LANE_EMOJIS.get(lane, '📌')} {lane.title()} Lane"
            value = "Quiet"
            if best:
                value = f"{best['label']} → {best['next_level']}"
            cards.append(self._render_summary_card_html(label, value))
        return ''.join(cards)

    def _base_upgrade_card_html(self, title: str, subtitle: str, summary_html: str, board_html: str) -> str:
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin: 0;
    background: #ececec;
    font-family: Arial, Helvetica, sans-serif;
    color: #202020;
}}

.icon, .unit-icon, .spotlight-icon, .summary-icon, .metric-icon {{
    width: 48px;
    height: 48px;
    object-fit: contain;
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
    border-radius: 8px;
}}
.pill-icon {{
    width: 20px;
    height: 20px;
    object-fit: contain;
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
}}
.emoji-fallback {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
}}
.wrap {{
    padding: 28px;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    box-sizing: border-box;
}}
.container {{
    width: 920px;
    padding: 24px 32px 44px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: white;
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}}
.title {{
    font-size: 44px;
    font-weight: 700;
    line-height: 1.05;
    margin-top: 0;
    margin-bottom: 8px;
    text-align: center;
}}
.subtitle {{
    font-size: 22px;
    color: #7f7f7f;
    margin-bottom: 24px;
    text-align: center;
}}
.summary {{
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin-bottom: 28px;
    text-align: center;
}}
.summary-card {{
    background: #f8f8f8;
    border: 1px solid #e8e8e8;
    border-radius: 16px;
    padding: 18px 16px;
}}
.summary-card .label {{
    font-size: 19px;
    color: #7b7b7b;
    margin-bottom: 6px;
    font-weight: 500;
}}
.summary-card .value {{
    font-size: 30px;
    font-weight: 700;
    color: #1f1f1f;
    line-height: 1.15;
}}
.board {{
    width: 100%;
    margin-top: 6px;
    padding-top: 20px;
    border-top: 1px solid #e3e3e3;
}}
.section-title {{
    font-size: 30px;
    font-weight: 700;
    text-align: center;
    margin: 0 0 18px;
}}
.donation-row {{
    display: grid;
    grid-template-columns: 90px 1fr 185px;
    gap: 16px;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid #ececec;
}}
.donation-rank {{
    font-size: 28px;
    font-weight: 700;
    text-align: center;
    color: #202020;
}}
.donation-main {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.donation-name {{
    font-size: 24px;
    font-weight: 700;
    color: #1f1f1f;
}}
.upgrade-sub {{
    font-size: 18px;
    color: #505050;
}}
.upgrade-reason {{
    font-size: 17px;
    color: #686868;
    line-height: 1.35;
}}
.donation-bar {{
    width: 100%;
    height: 14px;
    background: #dfdfe4;
    border-radius: 999px;
    overflow: hidden;
}}
.donation-fill {{
    height: 100%;
    background: #6fbf73;
    border-radius: 999px;
}}
.donation-stats {{
    text-align: right;
    font-size: 18px;
    color: #404040;
    line-height: 1.5;
}}
.pill {{
    display: inline-block;
    margin-left: 10px;
    padding: 6px 10px;
    border-radius: 999px;
    background: #f1f1f1;
    color: #515151;
    font-size: 15px;
    font-weight: 600;
    vertical-align: middle;
}}
.empty {{
    font-size: 22px;
    color: #777;
    text-align: center;
    padding: 40px 0;
}}
.note {{
    width: 100%;
    padding-top: 18px;
    text-align: center;
    font-size: 18px;
    color: #707070;
}}
.status-note {{
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: #f8fbff;
    border: 1px solid #dfe8f4;
    border-radius: 14px;
    padding: 12px 14px;
    color: #4b5563;
    font-size: 17px;
    line-height: 1.35;
    margin-top: 12px;
    text-align: left;
}}
.spotlight-card {{
    text-align: left;
}}
.metric-row {{
    display: grid;
    grid-template-columns: 220px 1fr 140px;
    gap: 14px;
    align-items: center;
    margin: 10px 0;
}}
.metric-label {{
    font-size: 20px;
    font-weight: 700;
    color: #2a2a2a;
}}
.metric-bar {{
    width: 100%;
    height: 14px;
    background: #dfdfe4;
    border-radius: 999px;
    overflow: hidden;
}}
.metric-fill {{
    height: 100%;
    background: #4f8df7;
    border-radius: 999px;
}}
.metric-value {{
    text-align: right;
    font-size: 18px;
    color: #404040;
    font-weight: 700;
}}
</style>
</head>
<body>
<div class="wrap">
<div class="container">
    <div class="title">{self._html_escape(title)}</div>
    <div class="subtitle">{self._html_escape(subtitle)}</div>
    <div class="summary">{summary_html}</div>
    <div class="board">{board_html}</div>
</div>
</div>
</body>
</html>
        '''



    def _base_compact_card_html(self, title: str, subtitle: str, body_html: str) -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin: 0;
    background: #eef1f6;
    font-family: Arial, Helvetica, sans-serif;
    color: #1f2937;
}}

.icon, .unit-icon, .spotlight-icon, .summary-icon, .metric-icon {{
    width: 48px;
    height: 48px;
    object-fit: contain;
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
    border-radius: 8px;
}}
.pill-icon {{
    width: 20px;
    height: 20px;
    object-fit: contain;
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
}}
.emoji-fallback {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
}}
.card-shell {{
    width: 920px;
    height: 980px;
    box-sizing: border-box;
    padding: 24px;
}}
.card {{
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border-radius: 18px;
    border: 1px solid #dfe5ee;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    padding: 28px;
}}
.header {{
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 14px;
    margin-bottom: 18px;
}}
.title {{
    font-size: 34px;
    font-weight: 700;
    line-height: 1.1;
    margin: 0 0 6px;
}}
.subtitle {{
    font-size: 18px;
    color: #6b7280;
    margin: 0;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}}
.stat {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px;
}}
.stat .label {{
    font-size: 13px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 6px;
}}
.stat .value {{
    font-size: 26px;
    font-weight: 700;
    color: #111827;
    line-height: 1.15;
}}
.section {{
    margin-top: 16px;
}}
.section-title {{
    font-size: 20px;
    font-weight: 700;
    margin: 0 0 10px;
    color: #111827;
}}
.progress-row {{
    margin: 10px 0 12px;
}}
.progress-meta {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    font-size: 16px;
    margin-bottom: 6px;
}}
.progress-label {{
    font-weight: 700;
    color: #374151;
}}
.progress-value {{
    color: #4b5563;
    font-weight: 700;
}}
.bar {{
    width: 100%;
    height: 14px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
}}
.fill {{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #4f8df7, #60a5fa);
}}
.pick {{
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
}}
.pick-title {{
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #111827;
}}
.pick-sub {{
    font-size: 15px;
    color: #4b5563;
    line-height: 1.4;
}}
.muted {{
    color: #6b7280;
    font-size: 15px;
    line-height: 1.45;
}}
</style>
</head>
<body>
<div class="card-shell">
  <div class="card">
    <div class="header">
      <div class="title">{self._html_escape(title)}</div>
      <div class="subtitle">{self._html_escape(subtitle)}</div>
    </div>
    {body_html}
  </div>
</div>
</body>
</html>
        """


    def _pick_spotlight_recommendations(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any] | None]:
        ranked = list(recs or [])
        extended = list(pool or [])
        combined: list[dict[str, Any]] = []
        seen: set[str] = set()
        for rec in ranked + extended:
            key = str(rec.get("key") or rec.get("item_key") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            combined.append(rec)

        best = combined[0] if combined else None

        quick = None
        progress = None

        def gap_of(rec: dict[str, Any]) -> int:
            return max(0, int(rec.get("target", 0) or 0) - int(rec.get("current", 0) or 0))

        if combined:
            quick_pool = [rec for rec in combined if gap_of(rec) > 0]
            if quick_pool:
                quick = min(
                    quick_pool,
                    key=lambda rec: (
                        gap_of(rec),
                        0 if rec.get("lane") == "hero" else 1,
                        -float(rec.get("score", 0) or 0),
                    ),
                )

            progress_pool = [rec for rec in combined if gap_of(rec) >= 2]
            if not progress_pool:
                progress_pool = quick_pool
            if progress_pool:
                progress = max(
                    progress_pool,
                    key=lambda rec: (
                        float(rec.get("score", 0) or 0),
                        gap_of(rec),
                        1 if rec.get("lane") == "hero" else 0,
                    ),
                )

        return {"best": best, "quick": quick, "progress": progress}

    def _format_spotlight_line(self, rec: dict[str, Any] | None, label: str, icon: str) -> str:
        if not rec:
            return f"{icon} **{label}:** No upgrade queued."
        reason = (rec.get("reasons") or ["Solid value right now."])[0]
        if len(reason) > 80:
            reason = reason[:77].rstrip() + "..."
        gap = max(0, int(rec.get("target", 0) or 0) - int(rec.get("current", 0) or 0))
        return (
            f"{icon} **{label}:** {rec.get('label', 'Upgrade')} → **{rec.get('next_level', '?')}**\n"
            f"`{self.build_mini_progress_bar(int(rec.get('current', 0) or 0), int(rec.get('target', 1) or 1))}` "
            f"Gap **{gap}** · Score **{rec.get('score', 0)}**\n"
            f"{reason}"
        )

    def build_nextupgrade_spotlight_block(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> str:
        picks = self._pick_spotlight_recommendations(recs, pool)
        lines = [
            self._format_spotlight_line(picks.get("best"), "Best Upgrade", "🔥"),
            self._format_spotlight_line(picks.get("quick"), "Quick Win", "⚡"),
            self._format_spotlight_line(picks.get("progress"), "Big Progress", "📈"),
        ]
        return "\n\n".join(lines)

    def _render_spotlight_tiles_html(self, recs: list[dict[str, Any]], pool: list[dict[str, Any]] | None = None) -> str:
        picks = self._pick_spotlight_recommendations(recs, pool)
        order = [
            ("best", "🔥 Best Upgrade"),
            ("quick", "⚡ Quick Win"),
            ("progress", "📈 Big Progress"),
        ]
        tiles: list[str] = []
        used: set[str] = set()
        fallback_pool = list(recs or []) + list(pool or [])
        for key, title in order:
            rec = picks.get(key)
            rec_id = self._rec_identity(rec)
            if rec_id and rec_id in used:
                rec = next((candidate for candidate in fallback_pool if self._rec_identity(candidate) and self._rec_identity(candidate) not in used), None)
                rec_id = self._rec_identity(rec)
            if rec_id:
                used.add(rec_id)

            if rec:
                reason = (rec.get("reasons") or ["Solid value right now."])[0]
                if len(reason) > 90:
                    reason = reason[:87].rstrip() + "..."
                item_icon_html = self._render_icon_html(icon_key=rec.get("key") or rec.get("item_key"), label=rec.get("label", "Upgrade"), fallback="📌", kind="item", css_class="spotlight-icon")
                line_1 = f"{item_icon_html}<span>{self._html_escape(str(rec.get('label', 'Upgrade')))} → {self._html_escape(str(rec.get('next_level', '?')))}</span>"
                line_2 = f"Lvl {int(rec.get('current', 0) or 0)} / {int(rec.get('target', 1) or 1)}"
                line_3 = f"Gap {max(0, int(rec.get('target', 0) or 0) - int(rec.get('current', 0) or 0))} · Score {self._html_escape(str(rec.get('score', 0)))}"
                detail = self._html_escape(reason)
            else:
                line_1 = "No unique upgrade queued"
                line_2 = "—"
                line_3 = "—"
                detail = "No separate recommendation for this spotlight right now."
            tiles.append(
                f'<div class="summary-card spotlight-card"><div class="label">{self._html_escape(title)}</div>'
                f'<div class="value spotlight-value" style="font-size:26px;">{line_1}</div>'
                f'<div class="sub">{line_2} · {line_3}</div>'
                f'<div class="sub" style="margin-top:8px; line-height:1.45;">{detail}</div></div>'
            )
        return ''.join(tiles)

    def build_nextupgrade_card_html(self, user, recs, pool, timing_context=None):
        return build_nextupgrade_card_html(self, user, recs, pool, timing_context)

    def build_upgradeprogress_card_html(self, user, timing_context=None):
        return build_upgradeprogress_card_html(self, user, timing_context)

    def _safe_rec_int(self, rec: dict[str, Any] | None, key: str, default: int = 0) -> int:
        if not isinstance(rec, dict):
            return default
        try:
            value = rec.get(key, default)
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_rec_label(self, rec: dict[str, Any] | None) -> str:
        if not isinstance(rec, dict):
            return "Upgrade"
        label = rec.get("label") or rec.get("key") or "Upgrade"
        return str(label)

    def _build_compact_progress_card_html(self, user: dict[str, Any], timing_context: dict[str, Any] | None = None) -> str:
        progress = self.build_progress_snapshot(user)
        account = self.build_account_completion_snapshot(user)
        player_name = user.get("player_name") or "Unknown"
        th = user.get("town_hall") or "?"
        role = str(user.get("role", DEFAULT_ROLE)).title()
        state = self.get_milestone_state(user)
        velocity = self.get_progress_velocity(user)
        eta_value, eta_sub = self._format_days_eta_text(velocity.get("days_to_target"))
        summary_html = ''.join([
            self._render_summary_card_html("Account", f"{player_name} · TH{th}", "🏰"),
            self._render_summary_card_html("Role", role, "⚔️"),
            self._render_summary_card_html("Advisor Progress", f"{progress['percent']}%", "🎯"),
            self._render_summary_card_html("Goals Complete", f"{progress['done']}/{progress['tracked']}", "✅"),
            self._render_summary_card_html("Data Coverage", f"{account.get('supported_known', 0)}/{account.get('supported_slots', 0)}", "🧭"),
            self._render_summary_card_html("TH Age", self.get_town_hall_age_text(user), "⏱️"),
            self._render_summary_card_html("ETA", f"{eta_value} {eta_sub}", "⚡"),
            self._render_summary_card_html("Efficiency", str(velocity.get("rating", "Unrated")), "⭐"),
        ])
        board_html = (
            '<div class="section-title">Progress Breakdown</div>'
            + ''.join([
                self._render_metric_row_html("Overall", int(progress["done"]), int(progress["tracked"]), "📊"),
                self._render_metric_row_html("Heroes", int(state["group_status"]["heroes"]["done"]), int(state["group_status"]["heroes"]["total"]), "👑"),
                self._render_metric_row_html("Offense", int(state["group_status"]["offense"]["done"]), int(state["group_status"]["offense"]["total"]), "⚔️"),
                self._render_metric_row_html("Core Buildings", int(state["group_status"]["builder"]["done"]), int(state["group_status"]["builder"]["total"]), "🛠️"),
            ])
            + '<div class="section-title" style="margin-top:18px;">Top Focus</div>'
            + f'<div class="note" style="text-align:left; line-height:1.45;">{self._html_escape(self.build_milestone_hint(user).replace("**", ""))}</div>'
            + self._render_status_note_html(self._war_ready_blocker_note(user), "✅")
            + self._render_status_note_html(self._lowest_account_category_note(account), "📉")
            + f"<div class=\"note\" style=\"margin-top:10px; text-align:left; line-height:1.45;\">Missing Account Data: {max(0, int(account.get('supported_slots', 0) or 0) - int(account.get('supported_known', 0) or 0))} supported TH slot(s) still need known levels. This is full-account coverage; /missinggoals only checks advisor-goal inputs.</div>"
            + f'<div class="note" style="margin-top:10px; text-align:left; line-height:1.45;">{self._html_escape(self.build_untracked_goal_callout(user))}</div>'
        )
        subtitle = f"Progress snapshot for {player_name}"
        return self._base_upgrade_card_html("Upgrade Progress", subtitle, summary_html, board_html)


    def _build_safe_nextupgrade_embed(self, user: dict[str, Any], recs: list[dict[str, Any]], pool: list[dict[str, Any]], timing_context: dict[str, Any] | None = None) -> discord.Embed:
        progress = self.build_progress_snapshot(user)
        account = self.build_account_completion_snapshot(user)
        timing_context = timing_context or self.get_timing_context(user)
        embed = discord.Embed(
            title=f"{BRAIN} Upgrade Advisor",
            color=0x5865F2,
            description=self.profile_summary(user),
        )
        self._safe_followup_embed_field(
            embed,
            name="Account Snapshot",
            value=self.build_quick_status_block(user, recs, timing_context=timing_context),
            inline=False,
            limit=900,
        )
        self._safe_followup_embed_field(
            embed,
            name="Upgrade Spotlights",
            value=self.build_nextupgrade_spotlight_block((recs or [])[:10], pool[:10] if pool else []),
            inline=False,
            limit=900,
        )
        picks = []
        for idx, rec in enumerate((recs or [])[:10], start=1):
            label = self._safe_rec_label(rec)
            current = self._safe_rec_int(rec, "current", 0)
            next_level = self._safe_rec_int(rec, "next_level", current + 1)
            target = self._safe_rec_int(rec, "target", next_level)
            gap = max(0, target - current)
            reason_list = rec.get("reasons") if isinstance(rec, dict) else None
            reason = (reason_list or ["Good overall value right now."])[0]
            picks.append(f"#{idx} **{label}**\nLvl **{current} → {next_level}** of **{target}** · Gap **{gap}**\n{self._truncate_for_embed(reason, limit=140)}")
        self._safe_followup_embed_field(embed, name="Top Upgrade Picks", value="\n\n".join(picks) or "Nothing urgent right now.", inline=False, limit=950)
        self._safe_followup_embed_field(embed, name="Lane Breakdown", value=self.build_lane_summary((recs or [])[:10]), inline=True, limit=400)
        tracked_goals = int(progress.get("tracked", 0) or 0)
        done_goals = int(progress.get("done", 0) or 0)
        percent = int(progress.get("percent", 0) or 0)

        self._safe_followup_embed_field(
            embed,
            name="Progress / Tracking",
            value=f"{percent}% complete\n{done_goals} / {tracked_goals} tracked goals complete",
            inline=True,
            limit=400,
        )
        self._safe_followup_embed_field(embed, name="Missing Input", value=self.build_untracked_goal_callout(user), inline=False, limit=500)
        self._safe_followup_embed_field(embed, name="Speed / ETA", value=self.build_velocity_summary(user), inline=False, limit=500)
        embed.set_footer(text="Compact advisor view shown.")
        return embed


    def _build_syncupgrades_card_html(
        self,
        user: dict[str, Any],
        *,
        synced_count: int,
        manual_count: int,
        account_snap: dict[str, Any],
        pool_snap: dict[str, Any],
        war_ready: str,
        mode_label: str,
        milestone_celebration: str,
        reward_text: str,
    ) -> str:
        return build_syncupgrades_card_html(
            self,
            user,
            synced_count=synced_count,
            manual_count=manual_count,
            account_snap=account_snap,
            pool_snap=pool_snap,
            war_ready=war_ready,
            mode_label=mode_label,
            milestone_celebration=milestone_celebration,
            reward_text=reward_text,
        )
    def _strip_markdown_for_html(self, value: Any) -> str:
        text = str(value if value is not None else "")
        for token in ("**", "__", "`"):
            text = text.replace(token, "")
        return text

    def _build_missing_tracker_card_html(
        self,
        *,
        title: str,
        subtitle: str,
        summary_cards: list[tuple[str, Any]],
        body: str,
        footer: str,
        theme: str = "gold",
    ) -> str:
        themes = {
            "gold": {
                "bg": "#fff8e6",
                "accent": "#f4b942",
                "accent_dark": "#8a5a00",
                "card": "#fffdf7",
                "chip": "#fff1c7",
            },
            "blue": {
                "bg": "#eef6ff",
                "accent": "#4f9cff",
                "accent_dark": "#195c9f",
                "card": "#f8fbff",
                "chip": "#ddecff",
            },
        }
        t = themes.get(theme, themes["gold"])
        cards_html = "".join(
            f'<div class="card"><div class="label">{self._html_escape(label)}</div><div class="value">{self._html_escape(value)}</div></div>'
            for label, value in summary_cards
        )
        return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body {{ margin:0; background:#ececec; font-family:Arial, Helvetica, sans-serif; color:#202020; }}
.container {{ width:1000px; min-height:760px; padding:30px 36px; box-sizing:border-box; background:{t["bg"]}; border-radius:18px; box-shadow:0 10px 30px rgba(0,0,0,.08); border:3px solid {t["accent"]}; }}
.title {{ font-size:44px; font-weight:900; line-height:1; color:{t["accent_dark"]}; }} .subtitle {{ font-size:21px; color:#666; margin-top:8px; }}
.summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:24px 0; }} .card {{ background:{t["card"]}; border:1px solid {t["accent"]}; border-radius:16px; padding:16px; text-align:center; box-shadow:0 4px 14px rgba(0,0,0,.04); }} .label {{ font-size:16px; color:#666; margin-bottom:4px; }} .value {{ font-size:30px; font-weight:900; color:{t["accent_dark"]}; }}
.content {{ border-top:2px solid {t["accent"]}; padding-top:16px; }} .section {{ margin:0 0 16px; padding:16px 18px; background:{t["card"]}; border:1px solid {t["accent"]}; border-radius:16px; }} .section-title {{ font-size:23px; font-weight:900; margin-bottom:8px; color:{t["accent_dark"]}; }} .section-title span {{ background:{t["chip"]}; color:{t["accent_dark"]}; border-radius:999px; padding:3px 10px; font-size:17px; font-weight:800; }}
ul {{ margin:0; padding-left:22px; font-size:18px; line-height:1.45; }} li {{ margin:4px 0; }} .muted {{ color:#777; }} .empty {{ font-size:25px; color:#777; text-align:center; padding:60px 20px; }} .good {{ color:#2f8f4e; }} .footer {{ margin-top:18px; padding-top:14px; border-top:2px solid {t["accent"]}; color:#555; font-size:18px; line-height:1.45; }}
</style></head><body><div class="container"><div class="title">{title}</div><div class="subtitle">{subtitle}</div><div class="summary">{cards_html}</div><div class="content">{body}</div><div class="footer">{footer}</div></div></body></html>'''

    def _build_missing_goals_card_html(self, user: dict[str, Any], snapshot: dict[str, Any] | None = None) -> str:
        snapshot = snapshot or self.build_untracked_goal_snapshot(user)
        player_name = self._html_escape(user.get("player_name") or "Unknown")
        town_hall = self._html_escape(user.get("town_hall") or "?")
        role = self._html_escape(str(user.get("role", DEFAULT_ROLE)).title())
        total_items = int(snapshot.get("items", 0) or 0)
        missing_items = int(snapshot.get("missing_items", 0) or 0)
        partial_items = int(snapshot.get("partial_items", 0) or 0)
        missing_slots = int(snapshot.get("missing_slots", 0) or 0)
        groups = snapshot.get("groups") or {}
        if total_items <= 0:
            body = '<div class="empty good">✅ All current advisor goals are already tracked.</div>'
        else:
            sections = []
            for category, items in list(groups.items())[:10]:
                emoji = CATEGORY_EMOJIS.get(category, "📌")
                label = category.replace("_", " ").title()
                rows = []
                for goal in items[:12]:
                    line = self._strip_markdown_for_html(self._format_untracked_goal_line(goal))
                    rows.append(f'<li>{self._html_escape(line)}</li>')
                if len(items) > 12:
                    rows.append(f'<li class="muted">…and {len(items) - 12} more in this category.</li>')
                sections.append(f'<div class="section"><div class="section-title">{self._html_escape(emoji)} {self._html_escape(label)} <span>{len(items)}</span></div><ul>{"".join(rows)}</ul></div>')
            body = "".join(sections) or '<div class="empty">No grouped missing goals found.</div>'

        return self._build_missing_tracker_card_html(
            title="🟧 Missing Goal Input",
            subtitle=f"{player_name} · TH{town_hall} · {role} · advisor target tracking",
            summary_cards=[
                ("Missing Items", total_items),
                ("Fully Missing", missing_items),
                ("Partial Items", partial_items),
                ("Missing Slots", missing_slots),
            ],
            body=body,
            footer="Goal Input is the manual upgrade-target side. Use /trackupgrade for single-value manual items. Use /trackcopies when a multi-copy building or trap has mixed levels.",
            theme="gold",
        )

    def _build_missing_data_card_html(self, user: dict[str, Any], account_snap: dict[str, Any] | None = None, missing_rows: list[dict[str, Any]] | None = None) -> str:
        account_snap = account_snap or self.build_account_completion_snapshot(user)
        missing_rows = missing_rows if missing_rows is not None else self.get_missing_account_data(user)
        player_name = self._html_escape(user.get("player_name") or "Unknown")
        town_hall = self._html_escape(user.get("town_hall") or "?")
        missing_slots = sum(int(row.get("missing", 0) or 0) for row in missing_rows)
        supported_known = int(account_snap.get("supported_known", 0) or 0)
        supported_slots = int(account_snap.get("supported_slots", 0) or 0)
        coverage_percent = account_snap.get("coverage_percent", 0)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in missing_rows:
            grouped.setdefault(str(row.get("category") or "other"), []).append(row)
        if missing_slots <= 0:
            body = '<div class="empty good">✅ All supported account-completion data is tracked.</div>'
        else:
            sections = []
            for category, rows in list(grouped.items())[:10]:
                emoji = CATEGORY_EMOJIS.get(category, "📌")
                category_label = ACCOUNT_COMPLETION_CATEGORY_LABELS.get(category, category.replace("_", " ").title())
                slot_count = sum(int(row.get("missing", 0) or 0) for row in rows)
                lines = []
                for row in rows[:10]:
                    line = self._strip_markdown_for_html(self._format_missing_account_data_line(row))
                    lines.append(f'<li>{self._html_escape(line)}</li>')
                if len(rows) > 10:
                    lines.append(f'<li class="muted">…and {len(rows) - 10} more item(s) in this category.</li>')
                sections.append(f'<div class="section"><div class="section-title">{self._html_escape(emoji)} {self._html_escape(category_label)} <span>{slot_count} slots</span></div><ul>{"".join(lines)}</ul></div>')
            body = "".join(sections) or '<div class="empty">No grouped missing data found.</div>'

        return self._build_missing_tracker_card_html(
            title="🟦 Missing Account Data",
            subtitle=f"{player_name} · TH{town_hall} · full account-completion audit",
            summary_cards=[
                ("Known Slots", supported_known),
                ("Supported Slots", supported_slots),
                ("Coverage", f"{coverage_percent}%"),
                ("Missing Slots", missing_slots),
            ],
            body=body,
            footer="Account Data is the full completion/audit side. Use /trackupgrade for one current level. Use /trackcopies for mixed-level multi-copy items like walls, traps, or defenses.",
            theme="blue",
        )

    async def render_html_card_to_file(
        self,
        html_content: str,
        filename: str,
        width: int = 920,
        height: int = 980,
        wait_ms: int = 900,
    ) -> discord.File:
        """Render advisor card output as a PNG using the shared Playwright renderer."""
        return await render_advisor_html_card_to_file(
            html_content,
            filename,
            width=width,
            height=height,
            wait_ms=wait_ms,
        )



    def register(self):
        from advisor.commands import register_advisor_commands

        register_advisor_commands(self)


def register_upgrade_advisor(tree, deps):
    advisor = UpgradeAdvisor(tree, deps)
    advisor.register()
    return advisor
