"""Loot drop service helpers.

Patch 60 audit: this file was reviewed during the untouched-file pass.
Loot drops should award MMO-profile Gold/resources through the economy bridge instead of reintroducing legacy-only progression.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.state import update_mmo_state


def choose_weighted_loot_style(*, loot_drop_styles):
    total_weight = sum(style["weight"] for style in loot_drop_styles)
    roll = random.uniform(0, total_weight)
    current = 0

    for style in loot_drop_styles:
        current += style["weight"]
        if roll <= current:
            return style

    return loot_drop_styles[0]


async def load_loot_drop(*, safe_load_json, loot_drop_file, clash_mmo_channel_id):
    stored = await safe_load_json(loot_drop_file)

    if not isinstance(stored, dict):
        stored = {}

    stored.setdefault("active", False)
    stored.setdefault("drop_id", None)
    stored.setdefault("channel_id", clash_mmo_channel_id)
    stored.setdefault("reward", 0)
    stored.setdefault("style", None)
    stored.setdefault("claimed_by", None)
    stored.setdefault("message_id", None)
    stored.setdefault("next_drop_at", None)
    return stored


async def schedule_next_loot_drop(
    *,
    safe_load_json,
    safe_save_json,
    loot_drop_file,
    clash_mmo_channel_id,
    loot_drop_min_minutes,
    loot_drop_max_minutes,
):
    drop = await load_loot_drop(
        safe_load_json=safe_load_json,
        loot_drop_file=loot_drop_file,
        clash_mmo_channel_id=clash_mmo_channel_id,
    )

    delay_minutes = random.randint(loot_drop_min_minutes, loot_drop_max_minutes)
    next_drop_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

    drop["next_drop_at"] = next_drop_at.isoformat()
    await safe_save_json(loot_drop_file, drop)


async def create_loot_drop(
    *,
    bot,
    economy,
    safe_load_json,
    safe_save_json,
    loot_drop_file,
    clash_mmo_channel_id,
    loot_drop_styles,
    loot_drop_lock,
):
    channel = bot.get_channel(clash_mmo_channel_id)
    if not channel:
        return False

    async with loot_drop_lock:
        current = await load_loot_drop(
            safe_load_json=safe_load_json,
            loot_drop_file=loot_drop_file,
            clash_mmo_channel_id=clash_mmo_channel_id,
        )

        if current.get("active"):
            return False

        style = choose_weighted_loot_style(loot_drop_styles=loot_drop_styles)
        reward = random.choice(style["rewards"])
        spawn_text = random.choice(style["spawn_messages"]).format(reward=reward)
        drop_id = f"loot_{int(datetime.now(timezone.utc).timestamp())}_{random.randint(1000, 9999)}"

        reserved_data = {
            "active": True,
            "drop_id": drop_id,
            "channel_id": clash_mmo_channel_id,
            "reward": reward,
            "style": style["name"],
            "claimed_by": None,
            "message_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_drop_at": None,
        }

        await safe_save_json(loot_drop_file, reserved_data)

        try:
            msg = await channel.send(spawn_text)
        except Exception:
            reserved_data["active"] = False
            await safe_save_json(loot_drop_file, reserved_data)
            raise

        reserved_data["message_id"] = msg.id
        await safe_save_json(loot_drop_file, reserved_data)
        return True


async def claim_loot_drop(
    message,
    *,
    economy,
    safe_load_json,
    safe_save_json,
    normalize_linked_data,
    linked_file,
    loot_drop_file,
    clash_mmo_channel_id,
    loot_drop_styles,
    loot_drop_lock,
    shop_items,
    schedule_next_loot_drop_func,
    ctx=None,
):
    if message.author.bot:
        return False

    if message.channel.id != clash_mmo_channel_id:
        return False

    if message.content.strip().lower() != "claim":
        return False

    async with loot_drop_lock:
        drop = await load_loot_drop(
            safe_load_json=safe_load_json,
            loot_drop_file=loot_drop_file,
            clash_mmo_channel_id=clash_mmo_channel_id,
        )

        if not drop.get("active"):
            return False

        if drop.get("claimed_by"):
            return False

        linked_raw = await safe_load_json(linked_file)
        linked = normalize_linked_data(linked_raw)
        user_entries = linked.get(str(message.author.id), [])

        if not user_entries:
            await message.reply(
                "❌ You need to link your Clash account first with `/link` before claiming loot.",
                mention_author=False,
            )
            return True

        reward = int(drop.get("reward", 0))
        bonus_text = ""
        style_name = drop.get("style")
        player_name = user_entries[0].get("name", message.author.display_name)

        if await economy.consume_shop_item(str(message.author.id), "lucky_charm"):
            reward += shop_items["lucky_charm"]["bonus"]
            bonus_text = f"\n✨ Lucky Charm activated: +{shop_items['lucky_charm']['bonus']} Gold"

        if await economy.consume_shop_item(str(message.author.id), "high_roller"):
            high_roller = shop_items["high_roller"]
            if random.random() < float(high_roller.get("bust_chance", 0.25)):
                reward = 0
                bonus_text += "\n🎲 High Roller busted: reward dropped to 0 Gold."
            else:
                reward *= int(high_roller.get("multiplier", 2))
                bonus_text += f"\n🎲 High Roller hit: reward doubled to {reward} Gold."

        if ctx is None:
            raise RuntimeError("claim_loot_drop requires ctx so loot rewards can be written to MMO state")

        def _grant_loot_gold(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(message.author.id),
                player_name,
            )

            profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + int(reward))

            stats = profile.setdefault("stats", {})
            if int(reward) > 0:
                stats["lifetime_gold"] = int(stats.get("lifetime_gold", 0) or 0) + int(reward)
            stats["loot_drops_claimed"] = int(stats.get("loot_drops_claimed", 0) or 0) + 1

            identity = profile.setdefault("identity", {})
            identity["display_name"] = player_name
            profile["name"] = player_name

            return state

        await update_mmo_state(ctx, _grant_loot_gold)

        drop["active"] = False
        drop["claimed_by"] = str(message.author.id)
        await safe_save_json(loot_drop_file, drop)

        await schedule_next_loot_drop_func()

    style = next(
        (s for s in loot_drop_styles if s["name"] == style_name),
        loot_drop_styles[0],
    )

    win_text = random.choice(style["claim_messages"]).format(
        user=message.author.mention,
        reward=reward,
    )

    await message.reply(f"{win_text}{bonus_text}", mention_author=False)
    return True


def normalize_loot_drop_reward(reward):
    """Normalize a loot drop reward payload for logging/display code.

    This is intentionally small and side-effect free. It helps future code treat
    string/int/dict reward payloads consistently without touching persistence.
    """
    if isinstance(reward, dict):
        return dict(reward)
    if isinstance(reward, int):
        return {"gold": max(0, reward)}
    if isinstance(reward, str):
        return {"label": reward}
    return {}
