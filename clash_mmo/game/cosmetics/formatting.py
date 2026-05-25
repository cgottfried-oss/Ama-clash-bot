from __future__ import annotations

from .catalog import COSMETIC_CATALOG


RARITY_ICONS = {
    "common": "⚪",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
}



def format_cosmetic_line(cosmetic_id: str):
    cosmetic = COSMETIC_CATALOG.get(cosmetic_id)

    if not cosmetic:
        return f"❓ Unknown Cosmetic ({cosmetic_id})"

    rarity = cosmetic.get("rarity", "common")
    icon = RARITY_ICONS.get(rarity, "⚪")
    animated = " ✨" if cosmetic.get("animated") else ""

    return (
        f"{icon} **{cosmetic.get('name')}**"
        f" ({rarity.title()}){animated}"
    )



def format_equipped_cosmetics(profile: dict):
    cosmetics = profile.get("cosmetics", {})
    equipped = cosmetics.get("equipped", {})

    lines = []

    for slot, cosmetic_id in equipped.items():
        if not cosmetic_id:
            lines.append(f"**{slot.title()}** — None")
            continue

        cosmetic = COSMETIC_CATALOG.get(cosmetic_id, {})
        lines.append(
            f"**{slot.title()}** — {cosmetic.get('name', cosmetic_id)}"
        )

    return "\n".join(lines)