from __future__ import annotations

from typing import Any, Callable

import discord
from discord import app_commands

from .builder import build_current_progress_data
from .renderer import create_current_progress_file


def _normalize_tag_fallback(tag: str) -> str:
    tag = str(tag or "").strip().upper()
    if tag and not tag.startswith("#"):
        tag = f"#{tag}"
    return tag


def _get_linked_entries(linked_raw: Any, discord_user_id: int | str) -> list[dict[str, Any]]:
    if not isinstance(linked_raw, dict):
        return []

    entries = linked_raw.get(str(discord_user_id), [])
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return []

    out = []
    for entry in entries:
        if isinstance(entry, str):
            out.append({"tag": entry, "name": "Linked Account"})
        elif isinstance(entry, dict) and entry.get("tag"):
            out.append(entry)
    return out


async def _resolve_player_tag(
    *,
    interaction: discord.Interaction,
    account: str | None,
    safe_load_json: Callable,
    linked_file: str,
    normalize_tag: Callable,
) -> str:
    if account:
        raw = account.strip()
        if raw.startswith("#") or raw.upper().startswith("P") or raw.upper().startswith("L") or raw.upper().startswith("Q"):
            return normalize_tag(raw)

    linked_raw = await safe_load_json(linked_file)
    entries = _get_linked_entries(linked_raw, interaction.user.id)

    if account:
        hint = account.strip().lower()
        for entry in entries:
            tag = normalize_tag(entry.get("tag", ""))
            name = str(entry.get("name", "")).lower()
            if hint in name or hint in tag.lower():
                return tag

    if entries:
        return normalize_tag(entries[0].get("tag", ""))

    raise ValueError("You need to link a Clash account first with `/link`, or pass a player tag.")


def register_current_progress_command(
    tree: app_commands.CommandTree,
    *,
    get_cached_or_fetch: Callable,
    normalize_tag: Callable = _normalize_tag_fallback,
    safe_load_json: Callable,
    linked_file: str,
    assets_dir: str,
    clash_api_base: str = "https://api.clashofclans.com/v1",
):
    @tree.command(name="currentprogress", description="Show your current Clash account progress as an image")
    @app_commands.describe(account="Optional linked account name or player tag")
    async def currentprogress(interaction: discord.Interaction, account: str | None = None):
        await interaction.response.defer(thinking=True)

        try:
            player_tag = await _resolve_player_tag(
                interaction=interaction,
                account=account,
                safe_load_json=safe_load_json,
                linked_file=linked_file,
                normalize_tag=normalize_tag,
            )

            encoded_tag = player_tag.replace("#", "%23")
            url = f"{clash_api_base}/players/{encoded_tag}"

            # Keep this short so profile changes and league placement are not stuck behind stale cache.
            player = await get_cached_or_fetch(f"player_{player_tag}", url, ttl=30)

            if not player:
                await interaction.followup.send("❌ Could not fetch that player from the Clash API right now.", ephemeral=True)
                return

            print(f"[CURRENTPROGRESS] tag={player_tag}", flush=True)
            print(f"[CURRENTPROGRESS] league={player.get('league')!r}", flush=True)
            print(f"[CURRENTPROGRESS] trophies={player.get('trophies')!r}", flush=True)
            print(f"[CURRENTPROGRESS] keys={sorted(player.keys())}", flush=True)

            progress_data = build_current_progress_data(player)
            file = await create_current_progress_file(
                progress_data,
                assets_dir=assets_dir,
                filename="currentprogress.png",
            )

            player_info = progress_data.get("player", {})
            embed = discord.Embed(
                title=f"{player_info.get('name', 'Player')} — Current Progress",
                description=f"{player_info.get('tag', '')} • TH{player_info.get('town_hall', '?')}",
                color=discord.Color.blurple(),
            )
            embed.set_image(url="attachment://currentprogress.png")

            await interaction.followup.send(embed=embed, file=file)

        except ValueError as exc:
            await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            print(f"[CURRENTPROGRESS ERROR] {type(exc).__name__}: {exc}", flush=True)
            await interaction.followup.send("❌ Something went wrong building your progress image.", ephemeral=True)

    return currentprogress
