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
    cosmetic = COSMETIC_CATALOG.get(cosmetic_id)

    if not cosmetic:
        return False

    cosmetics = get_player_cosmetics(profile)

    unlock_cosmetic(
        cosmetics,
        f"{cosmetic['type']}s",
        cosmetic_id,
    )

    return True



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
