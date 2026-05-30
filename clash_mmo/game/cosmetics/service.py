from __future__ import annotations

from .catalog import COSMETIC_CATALOG
from ..core.cosmetics import equip_cosmetic, unlock_cosmetic



def get_player_cosmetics(profile: dict):
    return profile.setdefault("cosmetics", {})



def list_cosmetics_by_type(cosmetic_type: str):
    return {
        cosmetic_id: cosmetic
        for cosmetic_id, cosmetic in COSMETIC_CATALOG.items()
        if cosmetic.get("type") == cosmetic_type
    }



def grant_cosmetic(profile: dict, cosmetic_id: str):
    """Grant a cosmetic and return a command-friendly result dict.

    Older code returned True/False here, while the slash command expected
    {"ok": bool, ...}.  Returning a consistent dict makes /grantcosmetic usable.
    """
    cosmetic_id = str(cosmetic_id or "").strip().lower()
    cosmetic = COSMETIC_CATALOG.get(cosmetic_id)

    if not cosmetic:
        return {
            "ok": False,
            "error": "Cosmetic does not exist.",
        }

    cosmetics = get_player_cosmetics(profile)

    unlock_cosmetic(
        cosmetics,
        f"{cosmetic['type']}s",
        cosmetic_id,
    )

    return {
        "ok": True,
        "cosmetic": cosmetic,
        "cosmetic_id": cosmetic_id,
    }



def equip_owned_cosmetic(profile: dict, cosmetic_id: str):
    cosmetic = COSMETIC_CATALOG.get(cosmetic_id)

    if not cosmetic:
        return {
            "ok": False,
            "error": "Cosmetic does not exist.",
        }

    cosmetics = get_player_cosmetics(profile)

    owned = cosmetics.get("owned", {}).get(
        f"{cosmetic['type']}s",
        [],
    )

    if cosmetic_id not in owned:
        return {
            "ok": False,
            "error": "You do not own this cosmetic.",
        }

    equip_cosmetic(
        cosmetics,
        cosmetic["type"],
        cosmetic_id,
    )

    return {
        "ok": True,
        "cosmetic": cosmetic,
    }

def get_equipped_cosmetic_bonuses(profile: dict) -> dict:
    """Return the gameplay-flavored bonuses from equipped cosmetics.

    These are intentionally small; cosmetics should mostly be flex/identity,
    but they can still show meaningful utility in /cosmetics.
    """
    cosmetics = get_player_cosmetics(profile)
    equipped = cosmetics.get("equipped", {}) if isinstance(cosmetics, dict) else {}
    bonuses: dict[str, float] = {}

    for cosmetic_id in equipped.values():
        cosmetic = COSMETIC_CATALOG.get(str(cosmetic_id or ""))
        if not cosmetic:
            continue
        for key, value in (cosmetic.get("bonuses") or {}).items():
            bonuses[key] = bonuses.get(key, 0) + value

    return bonuses
