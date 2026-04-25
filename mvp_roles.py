from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import discord


# Keep the actual Discord role mostly stable, then use these titles in the
# announcement/state so the MVP feels fresh without creating role clutter.
WAR_MVP_TITLES = [
    "The Closer",
    "Warbringer",
    "Apex Raider",
    "Clutch God",
    "Triple Crown 👑",
    "Final Blow",
    "Siege Master",
    "Base Breaker",
    "Three-Star Reaper",
    "Clan Executioner",
]

WAR_MVP_FLAVOR_LINES = [
    "Dominating the battlefield with precision and power.",
    "No base was safe. No defense held.",
    "A war-winning performance worthy of legend.",
    "Striking when it mattered most.",
    "The kind of hit list that makes enemy clans nervous.",
    "Clean attacks, huge impact, and certified MVP energy.",
    "Showed up, swung the war, and left no doubt.",
]


def generate_war_mvp_title() -> tuple[str, str]:
    """Return a rotating MVP title and flavor line for the announcement."""
    return random.choice(WAR_MVP_TITLES), random.choice(WAR_MVP_FLAVOR_LINES)


def get_war_mvp_role_color(stars: int | float = 0, destruction: int | float = 0) -> discord.Color:
    """Choose role color by MVP performance.

    Two perfect attacks normally equals 6 stars, so that gets gold.
    Destruction is used as a tie-breaker for strong non-perfect wars.
    """
    stars = float(stars or 0)
    destruction = float(destruction or 0)

    if stars >= 6:
        return discord.Color.gold()
    if stars >= 5 or destruction >= 180:
        return discord.Color.purple()
    if stars >= 4 or destruction >= 150:
        return discord.Color.blue()
    return discord.Color.red()


async def update_war_mvp_role_presentation(
    *,
    guild: Any,
    role_id: int | None,
    stars: int | float = 0,
    destruction: int | float = 0,
    title: str | None = None,
    rename_role: bool = False,
) -> dict[str, Any]:
    """Update the single War MVP role color, and optionally its name.

    By default this does NOT rename the role. Keeping the role name stable avoids
    audit-log spam while announcements can still use rotating titles.
    """
    if not role_id:
        return {"ok": False, "skipped": True, "reason": "WAR_MVP_ROLE_ID not configured"}
    if guild is None:
        return {"ok": False, "skipped": True, "reason": "No guild available"}

    role = guild.get_role(int(role_id))
    if role is None:
        return {"ok": False, "skipped": True, "reason": f"Role {role_id} not found"}

    edit_kwargs = {"color": get_war_mvp_role_color(stars, destruction)}
    if rename_role and title:
        edit_kwargs["name"] = f"👑 {title}"

    try:
        await role.edit(**edit_kwargs, reason="War MVP performance update")
        return {"ok": True, "color": str(edit_kwargs["color"]), "renamed": bool(rename_role and title)}
    except Exception as exc:
        return {"ok": False, "skipped": False, "reason": f"Could not update MVP role presentation: {exc}"}


async def rotate_war_mvp_role(
    *,
    guild: Any,
    role_id: int | None,
    mvp_discord_id: int | str | None,
    state_file: str,
    war_id: str,
    player_name: str,
    player_tag: str,
    safe_load_json: Callable[[str, Any], Awaitable[Any]],
    safe_save_json: Callable[[str, Any], Awaitable[None]],
    mvp_title: str | None = None,
) -> dict[str, Any]:
    """Give the current War MVP role to one member and remove it from prior holders.

    Safe to call even when WAR_MVP_ROLE_ID is not configured; it returns a skipped result.
    """
    if not role_id:
        return {"ok": False, "skipped": True, "reason": "WAR_MVP_ROLE_ID not configured"}
    if guild is None:
        return {"ok": False, "skipped": True, "reason": "No guild available"}
    if not mvp_discord_id:
        return {"ok": False, "skipped": True, "reason": "MVP is not linked to Discord"}

    role = guild.get_role(int(role_id))
    if role is None:
        return {"ok": False, "skipped": True, "reason": f"Role {role_id} not found"}

    mvp_id = int(mvp_discord_id)
    prior_state = await safe_load_json(state_file, default={})
    if not isinstance(prior_state, dict):
        prior_state = {}

    removed = []
    for member in list(getattr(role, "members", []) or []):
        if int(member.id) == mvp_id:
            continue
        try:
            await member.remove_roles(role, reason="New War MVP announced")
            removed.append(str(member.id))
        except Exception as exc:
            print(f"[WAR MVP ROLE] Could not remove role from {member.id}: {exc}")

    member = guild.get_member(mvp_id)
    if member is None:
        try:
            member = await guild.fetch_member(mvp_id)
        except Exception as exc:
            return {"ok": False, "skipped": True, "reason": f"MVP member not found: {exc}"}

    added = False
    if role not in getattr(member, "roles", []):
        try:
            await member.add_roles(role, reason="Current War MVP")
            added = True
        except Exception as exc:
            return {"ok": False, "skipped": False, "reason": f"Could not add MVP role: {exc}"}

    state = {
        "war_id": war_id,
        "discord_id": str(mvp_id),
        "player_name": player_name,
        "player_tag": player_tag,
        "mvp_title": mvp_title,
        "role_id": str(role_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "prior": prior_state,
    }
    await safe_save_json(state_file, state)
    return {"ok": True, "added": added, "removed": removed, "state": state}
