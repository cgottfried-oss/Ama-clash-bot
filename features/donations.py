from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import discord

from config import DONATION_FILE, LEADERBOARD_MESSAGE_FILE, DONATION_TEMPLATE_PATH
from storage import update_json_file
from renderers.donation_renderer import create_donation_image


async def get_saved_message(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            return int(raw) if raw else None
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[DONATIONS] Could not read saved message id from {file_path}: {e}")
        return None


async def save_message(file_path: str, message_id: int):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(message_id))
    except Exception as e:
        print(f"[DONATIONS] Could not save message id to {file_path}: {e}")


def get_current_monthly_mvp(stored_donations: dict[str, Any]):
    players = (stored_donations or {}).get("players", {})
    if not isinstance(players, dict) or not players:
        return None, None

    best_tag, best_data = max(
        players.items(),
        key=lambda item: (
            item[1].get("donations", 0),
            -item[1].get("received", 0),
            item[1].get("name", ""),
        ),
    )
    return best_data.get("name") or best_tag, best_data


async def update_donation_leaderboard(
    members: list[dict[str, Any]],
    channel: discord.TextChannel,
) -> None:
    if not channel:
        return

    season_key = datetime.now(timezone.utc).strftime("%Y-%m")

    def _update_donations(stored):
        if not isinstance(stored, dict):
            stored = {}

        previous_season = stored.get("season")
        if previous_season != season_key:
            print(
                f"[DONATIONS] New month detected. Resetting donations "
                f"from {previous_season} to {season_key}"
            )

        # Rebuild from CURRENT clan members only so stale / feeder / departed
        # accounts do not remain eligible for the monthly donation MVP.
        current_players = {}
        for m in members:
            tag = m.get("tag")
            if not tag:
                continue

            current_players[tag] = {
                "tag": tag,
                "name": m.get("name", "")[:12],
                "donations": int(m.get("donations", 0) or 0),
                "received": int(m.get("donationsReceived", 0) or 0),
            }

        return {
            "season": season_key,
            "players": current_players,
        }

    stored = await update_json_file(DONATION_FILE, _update_donations)

    leaderboard = sorted(
        stored.get("players", {}).values(),
        key=lambda x: x["donations"],
        reverse=True,
    )

    monthly_mvp_name, monthly_mvp_data = get_current_monthly_mvp(stored)

    buffer = await create_donation_image(
        leaderboard,
        template_path=DONATION_TEMPLATE_PATH,
    )
    if buffer is None:
        print("[DONATIONS] create_donation_image returned None; skipping image upload")
        return

    file = discord.File(fp=buffer, filename="donations.png")

    embed = discord.Embed(
        title=f"Monthly Donations - {season_key}",
        color=0x2C2F33,
    )

    if monthly_mvp_name and monthly_mvp_data:
        donated = int(monthly_mvp_data.get("donations", 0) or 0)
        received = int(monthly_mvp_data.get("received", 0) or 0)
        embed.description = (
            f"🏆 **Top Donor This Month:** {monthly_mvp_name}\n"
            f"📦 {donated:,} donated"
            f" • 📥 {received:,} received"
        )

    embed.set_image(url="attachment://donations.png")

    mid = await get_saved_message(LEADERBOARD_MESSAGE_FILE)
    msg = None
    if mid:
        try:
            msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            msg = None

    if msg:
        try:
            await msg.edit(embeds=[embed], attachments=[file])
        except discord.HTTPException as e:
            print(f"[DONATIONS] Failed to edit leaderboard message: {e}")
    else:
        new_msg = await asyncio.wait_for(
            channel.send(embed=embed, file=file), timeout=10
        )
        await save_message(LEADERBOARD_MESSAGE_FILE, new_msg.id)
