from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


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
        "role_id": str(role_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "prior": prior_state,
    }
    await safe_save_json(state_file, state)
    return {"ok": True, "added": added, "removed": removed, "state": state}
