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

    perk = format_cosmetic_bonus_text(cosmetic)
    return (
        f"{icon} **{cosmetic.get('name')}**"
        f" ({rarity.title()}){animated} — {perk}"
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

def format_cosmetic_bonus_text(cosmetic: dict) -> str:
    bonuses = cosmetic.get("bonuses") or {}
    if not bonuses:
        return "No active perk"
    labels = []
    for key, value in bonuses.items():
        nice = str(key).replace("_", " ").title()
        suffix = "%" if key.endswith("_pct") else ""
        labels.append(f"{nice}: +{value}{suffix}")
    return ", ".join(labels)
