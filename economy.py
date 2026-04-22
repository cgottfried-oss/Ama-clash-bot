from __future__ import annotations

from typing import Any, Callable
import asyncio
import json
import os


def normalize_tag(tag: str) -> str:
    return str(tag or "").strip().upper().replace("O", "0")


def normalize_linked_data(data):
    """Normalize linked-player data into a tag-keyed mapping.

    Supports both of these shapes:
    1) {discord_id: [{"tag": "#ABC", "name": "Player"}, ...]}
    2) {player_tag: "discord_id"} or {player_tag: {"discord_id": "..."}}
    """
    if not isinstance(data, dict):
        return {}

    normalized = {}
    for key, value in data.items():
        key_str = str(key)

        # Primary/current bot format: discord user id -> linked entries
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, str):
                    player_tag = normalize_tag(entry)
                    if player_tag:
                        normalized[player_tag] = {
                            "player_tag": player_tag,
                            "discord_id": key_str,
                            "name": "Unknown",
                        }
                elif isinstance(entry, dict):
                    player_tag = normalize_tag(entry.get("tag") or entry.get("player_tag"))
                    if player_tag:
                        normalized[player_tag] = {
                            "player_tag": player_tag,
                            "discord_id": key_str,
                            "name": entry.get("name", "Unknown"),
                        }
            continue

        # Single-entry current format: discord user id -> {tag/name}
        if isinstance(value, dict) and ("tag" in value or "player_tag" in value) and not value.get("discord_id"):
            player_tag = normalize_tag(value.get("tag") or value.get("player_tag"))
            if player_tag:
                normalized[player_tag] = {
                    "player_tag": player_tag,
                    "discord_id": key_str,
                    "name": value.get("name", "Unknown"),
                }
            continue

        # Legacy/inverted format: player tag -> {discord_id/user_id/...}
        if isinstance(value, dict):
            entry = dict(value)
            player_tag = normalize_tag(entry.get("player_tag") or entry.get("tag") or key_str)
            discord_id = entry.get("discord_id", entry.get("user_id"))
            if player_tag and discord_id is not None:
                normalized[player_tag] = {
                    "player_tag": player_tag,
                    "discord_id": str(discord_id),
                    "name": entry.get("name", "Unknown"),
                }
            continue

        # Legacy/simple format: player tag -> discord id
        if isinstance(value, str):
            player_tag = normalize_tag(key_str)
            if player_tag:
                normalized[player_tag] = {
                    "player_tag": player_tag,
                    "discord_id": str(value),
                    "name": "Unknown",
                }

    return normalized


def build_tag_to_discord_map(linked_data):
    normalized = normalize_linked_data(linked_data)
    return {
        tag: str(entry.get("discord_id"))
        for tag, entry in normalized.items()
        if isinstance(entry, dict) and entry.get("discord_id")
    }


class EconomyManager:
    def __init__(
        self,
        *,
        coins_file: str,
        shop_file: str,
        linked_file: str,
        shop_items: dict[str, dict[str, Any]],
        star_coin_reward: int = 10,
        war_mvp_bonus: int = 150,
        clutch_coin_reward: int = 50,
        clutch_reward_tiers: dict[str, int] | None = None,
        advisor_progress_rewards: dict[int, int] | None = None,
        advisor_group_rewards: dict[str, int] | None = None,
        advisor_sync_reward: int = 10,
    ):
        self.coins_file = coins_file
        self.shop_file = shop_file
        self.linked_file = linked_file
        self.shop_items = shop_items
        self.star_coin_reward = int(star_coin_reward)
        self.war_mvp_bonus = int(war_mvp_bonus)
        self.clutch_coin_reward = int(clutch_coin_reward)
        self.clutch_reward_tiers = {
            "top_base": 75,
            "lead_flip": 125,
            "keep_alive": 100,
            "last_stand": 60,
        }
        if clutch_reward_tiers:
            self.clutch_reward_tiers.update({str(k): int(v) for k, v in clutch_reward_tiers.items()})
        self.advisor_progress_rewards = advisor_progress_rewards or {25: 50, 50: 100, 75: 200, 100: 500}
        self.advisor_group_rewards = advisor_group_rewards or {
            "heroes_complete": 75,
            "offense_core_complete": 100,
            "builder_core_complete": 100,
            "war_ready": 150,
        }
        self.advisor_sync_reward = int(advisor_sync_reward)
        self._file_lock = asyncio.Lock()

    async def safe_load_json(self, path: str, default: Any | None = None):
        async with self._file_lock:
            if not os.path.exists(path):
                return {} if default is None else default

            def _read():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return {} if default is None else default

            return await asyncio.to_thread(_read)

    async def safe_save_json(self, path: str, data: Any):
        async with self._file_lock:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

            def _write():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            await asyncio.to_thread(_write)

    async def update_json_file(self, path: str, update_fn: Callable[[Any], Any], default: Any | None = None):
        async with self._file_lock:
            if not os.path.exists(path):
                data = {} if default is None else default
            else:
                def _read():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception:
                        return {} if default is None else default
                data = await asyncio.to_thread(_read)

            new_data = update_fn(data)
            if new_data is None:
                new_data = data

            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            def _write():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
            await asyncio.to_thread(_write)
            return new_data

    def normalize_tag(self, tag: str) -> str:
        return normalize_tag(tag)

    def normalize_linked_data(self, linked: dict) -> dict:
        return normalize_linked_data(linked)

    def build_tag_to_discord_map(self, linked: dict) -> dict:
        return build_tag_to_discord_map(linked)

    async def load_coins(self):
        stored = await self.safe_load_json(self.coins_file)
        if not isinstance(stored, dict):
            stored = {}
        stored.setdefault("users", {})
        stored.setdefault("processed_wars", [])
        stored.setdefault("processed_clutches", [])
        stored.setdefault("advisor_claims", {})
        return stored

    async def load_shop_data(self):
        stored = await self.safe_load_json(self.shop_file)
        if not isinstance(stored, dict):
            stored = {}
        stored.setdefault("users", {})
        return stored

    async def get_user_shop_entry(self, user_id: str):
        stored = await self.load_shop_data()
        users = stored.setdefault("users", {})
        entry = users.setdefault(str(user_id), {"inventory": {}})
        return stored, entry

    async def add_shop_item(self, user_id: str, item_key: str, amount: int = 1):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {"inventory": {}})
            inventory = entry.setdefault("inventory", {})
            inventory[item_key] = inventory.get(item_key, 0) + amount
            return stored

        await self.update_json_file(self.shop_file, _update)

    async def consume_shop_item(self, user_id: str, item_key: str):
        consumed = {"ok": False}

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {"inventory": {}})
            inventory = entry.setdefault("inventory", {})
            current = inventory.get(item_key, 0)
            if current > 0:
                inventory[item_key] = current - 1
                if inventory[item_key] <= 0:
                    inventory.pop(item_key, None)
                consumed["ok"] = True
            return stored

        await self.update_json_file(self.shop_file, _update)
        return consumed["ok"]

    async def spend_coins(self, user_id: str, amount: int):
        result = {"ok": False, "balance": 0}

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            user_entry = users.setdefault(
                str(user_id),
                {"balance": 0, "lifetime_earned": 0, "name": "Unknown"},
            )
            current_balance = user_entry.get("balance", 0)
            result["balance"] = current_balance
            if current_balance < amount:
                return stored
            user_entry["balance"] = current_balance - amount
            result["ok"] = True
            result["balance"] = user_entry["balance"]
            return stored

        await self.update_json_file(self.coins_file, _update)
        return result

    async def get_inventory_text(self, user_id: str):
        stored = await self.load_shop_data()
        entry = stored.get("users", {}).get(str(user_id), {})
        inventory = entry.get("inventory", {})
        if not inventory:
            return "Empty"
        lines = []
        for item_key, qty in inventory.items():
            item = self.shop_items.get(item_key)
            if not item:
                continue
            lines.append(f"• {item['name']} x{qty}")
        return "\n".join(lines) if lines else "Empty"

    async def award_loot_drop_coins(self, user_id: str, player_name: str, reward: int):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})
            user_entry = users.setdefault(
                str(user_id),
                {"balance": 0, "lifetime_earned": 0, "name": player_name or "Unknown"},
            )
            user_entry["balance"] += reward
            user_entry["lifetime_earned"] += reward
            user_entry["name"] = player_name or user_entry.get("name", "Unknown")
            return stored

        await self.update_json_file(self.coins_file, _update)

    async def reward_war_coins(self, war, get_war_id: Callable, get_war_mvp_member: Callable):
        if war.get("state") != "warEnded":
            return {
                "ok": False,
                "reason": "war_not_ended",
                "war_id": None,
                "already_processed": False,
                "mvp": None,
                "rewards": {},
            }

        linked_raw = await self.safe_load_json(self.linked_file)
        linked = self.normalize_linked_data(linked_raw)
        tag_to_discord = self.build_tag_to_discord_map(linked)

        war_id = get_war_id(war)
        mvp_member = get_war_mvp_member(war)
        mvp_tag = self.normalize_tag(mvp_member.get("tag", "")) if mvp_member else None
        clan_members = war.get("clan", {}).get("members", [])

        mvp_shop_bonus = 0
        if mvp_tag:
            mvp_bonus_user_id = tag_to_discord.get(mvp_tag)
            if mvp_bonus_user_id and await self.consume_shop_item(str(mvp_bonus_user_id), "mvp_token"):
                mvp_shop_bonus = self.shop_items.get("mvp_token", {}).get("bonus", 0)

        result = {
            "ok": True,
            "reason": None,
            "war_id": war_id,
            "already_processed": False,
            "mvp": None,
            "rewards": {},
        }

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            processed_wars = stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})

            if war_id in processed_wars:
                result["already_processed"] = True
                return stored

            for member in clan_members:
                player_tag = self.normalize_tag(member.get("tag", ""))
                discord_id = tag_to_discord.get(player_tag)

                attacks = member.get("attacks", [])
                if not attacks:
                    continue

                stars = sum(a.get("stars", 0) for a in attacks)
                star_reward = stars * self.star_coin_reward
                mvp_bonus = self.war_mvp_bonus + mvp_shop_bonus if player_tag == mvp_tag else 0
                coins_earned = star_reward + mvp_bonus

                reward_entry = {
                    "player_tag": player_tag,
                    "player_name": member.get("name", "Unknown"),
                    "discord_id": str(discord_id) if discord_id else None,
                    "stars": stars,
                    "star_reward": star_reward,
                    "mvp_bonus": mvp_bonus,
                    "mvp_shop_bonus": mvp_shop_bonus if player_tag == mvp_tag else 0,
                    "total_reward": coins_earned,
                }
                result["rewards"][player_tag] = reward_entry

                if player_tag == mvp_tag:
                    result["mvp"] = reward_entry

                if not discord_id or coins_earned <= 0:
                    continue

                user_entry = users.setdefault(
                    str(discord_id),
                    {"balance": 0, "lifetime_earned": 0, "name": member.get("name", "Unknown")},
                )
                user_entry["balance"] += coins_earned
                user_entry["lifetime_earned"] += coins_earned
                user_entry["name"] = member.get("name", user_entry.get("name", "Unknown"))

            processed_wars.append(war_id)
            return stored

        await self.update_json_file(self.coins_file, _update)
        return result

    async def reward_clutch_coins(self, member_tag, member_name, attack_id, clutch_type: str | None = None):
        linked_raw = await self.safe_load_json(self.linked_file)
        linked = self.normalize_linked_data(linked_raw)
        tag_to_discord = self.build_tag_to_discord_map(linked)
        normalized_tag = self.normalize_tag(member_tag)
        discord_id = tag_to_discord.get(normalized_tag)
        if not discord_id:
            return {
                "ok": False,
                "reason": "unlinked",
                "discord_id": None,
                "reward": 0,
                "base_reward": 0,
                "bonus_reward": 0,
                "member_tag": normalized_tag,
            }

        bonus_reward = 0
        if await self.consume_shop_item(str(discord_id), "clutch_boost"):
            bonus_reward = int(self.shop_items.get("clutch_boost", {}).get("bonus", 0) or 0)

        result = {
            "ok": False,
            "reason": "unknown",
            "discord_id": str(discord_id),
            "reward": 0,
            "base_reward": int(self.clutch_reward_tiers.get(str(clutch_type or ""), self.clutch_coin_reward)),
            "bonus_reward": bonus_reward,
            "member_tag": normalized_tag,
        }

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            processed_clutches = stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})

            if attack_id in processed_clutches:
                result["reason"] = "duplicate"
                return stored

            user_entry = users.setdefault(
                str(discord_id),
                {"balance": 0, "lifetime_earned": 0, "name": member_name or "Unknown"},
            )
            total_reward = result["base_reward"] + bonus_reward
            user_entry["balance"] += total_reward
            user_entry["lifetime_earned"] += total_reward
            user_entry["name"] = member_name or user_entry.get("name", "Unknown")
            processed_clutches.append(attack_id)
            result["ok"] = True
            result["reason"] = "awarded"
            result["reward"] = total_reward
            return stored

        await self.update_json_file(self.coins_file, _update)
        return result

    async def award_advisor_sync_rewards(
        self,
        *,
        user_id: str,
        player_tag: str,
        player_name: str,
        reward_breakdown: dict[str, Any],
    ):
        claims_key = f"{str(user_id)}::{self.normalize_tag(player_tag)}"
        progress_marks = [int(mark) for mark in reward_breakdown.get("new_progress_marks", [])]
        group_keys = [str(key) for key in reward_breakdown.get("new_group_milestones", [])]
        should_reward_sync = bool(reward_breakdown.get("should_reward_sync", False))
        result = {"awarded": 0, "lines": [], "balance": 0}

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            advisor_claims = stored.setdefault("advisor_claims", {})
            claim_entry = advisor_claims.setdefault(
                claims_key,
                {"progress_marks": [], "group_milestones": [], "sync_days": []},
            )
            user_entry = users.setdefault(
                str(user_id),
                {"balance": 0, "lifetime_earned": 0, "name": player_name or "Unknown"},
            )

            claim_entry["progress_marks"] = [int(v) for v in claim_entry.get("progress_marks", [])]
            claim_entry["group_milestones"] = [str(v) for v in claim_entry.get("group_milestones", [])]
            claim_entry["sync_days"] = [str(v) for v in claim_entry.get("sync_days", [])]

            total = 0
            lines: list[str] = []

            for mark in sorted(set(progress_marks)):
                if mark in claim_entry["progress_marks"]:
                    continue
                reward = int(self.advisor_progress_rewards.get(mark, 0))
                if reward <= 0:
                    continue
                claim_entry["progress_marks"].append(mark)
                total += reward
                lines.append(f"📈 {mark}% advisor progress: +{reward}")

            for key in group_keys:
                if key in claim_entry["group_milestones"]:
                    continue
                reward = int(self.advisor_group_rewards.get(key, 0))
                if reward <= 0:
                    continue
                claim_entry["group_milestones"].append(key)
                total += reward
                pretty = key.replace("_", " ").title()
                lines.append(f"🏆 {pretty}: +{reward}")

            sync_day = reward_breakdown.get("sync_day")
            if should_reward_sync and sync_day and sync_day not in claim_entry["sync_days"]:
                claim_entry["sync_days"].append(sync_day)
                total += self.advisor_sync_reward
                lines.append(f"🔄 Daily sync bonus: +{self.advisor_sync_reward}")

            if total > 0:
                user_entry["balance"] += total
                user_entry["lifetime_earned"] += total
                user_entry["name"] = player_name or user_entry.get("name", "Unknown")

            result["awarded"] = total
            result["lines"] = lines
            result["balance"] = user_entry.get("balance", 0)
            return stored

        await self.update_json_file(self.coins_file, _update)
        return result
