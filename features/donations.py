from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable

import discord


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
    *,
    members: list[dict[str, Any]],
    channel: discord.TextChannel,
    donation_file: str,
    leaderboard_message_file: str,
    update_json_file: Callable[..., Any],
    create_donation_image: Callable[..., Any],
    get_saved_message: Callable[..., Any],
    save_message: Callable[..., Any],
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

    stored = await update_json_file(donation_file, _update_donations)

    leaderboard = sorted(
        stored.get("players", {}).values(),
        key=lambda x: x["donations"],
        reverse=True,
    )

    monthly_mvp_name, monthly_mvp_data = get_current_monthly_mvp(stored)

    buffer = await create_donation_image(leaderboard)
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
        ratio_text = "∞" if received == 0 and donated > 0 else (
            f"{(donated / received):.2f}x" if received > 0 else "0.00x"
        )
        embed.description = (
            f"🏆 **Top Donor This Month:** {monthly_mvp_name}\n"
            f"📦 {donated} donated"
            f" • 📥 {received} received"
            f" • 📊 {ratio_text} ratio"
        )

    embed.set_image(url="attachment://donations.png")

    mid = await get_saved_message(leaderboard_message_file)
    msg = None
    if mid:
        try:
            msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            msg = None

    if msg:
        try:
            await msg.edit(embeds=[embed], attachments=[file])
        except discord.HTTPException:
            pass
    else:
        new_msg = await asyncio.wait_for(
            channel.send(embed=embed, file=file), timeout=10
        )
        await save_message(leaderboard_message_file, new_msg.id)
