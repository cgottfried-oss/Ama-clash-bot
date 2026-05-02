from __future__ import annotations

import html as html_lib
import os
from pathlib import Path

from renderers.icon_resolver import asset_to_data_uri


DEFAULT_ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))

# Generic, easy-to-replace filenames for render icons.
# Add any of these to assets/icons as .png, .webp, .jpg, or .jpeg.
EMOJI_ICON_NAMES: dict[str, str] = {
    "🥇": "gold_medal",
    "🥈": "silver_medal",
    "🥉": "bronze_medal",
    "🏆": "trophy",
    "💰": "coin",
    "📦": "loot_box",
    "📥": "received",
    "📊": "stats",
    "🛒": "shop",
    "🎒": "inventory",
    "🔁": "reroll",
    "🏴": "war_banner",
    "🛡️": "shield",
    "🛡": "shield",
    "✨": "lucky_charm",
    "🎲": "high_roller",
    "⭐": "star",
    "⚔️": "swords",
    "⚔": "swords",
    "🔥": "fire",
    "✅": "success",
    "❌": "error",
    "ℹ️": "info",
    "ℹ": "info",
}


def icon_uri(name: str, assets_dir: str | Path | None = None) -> str | None:
    """Return a data URI for assets/icons/<name>.* when it exists."""
    icons_dir = Path(assets_dir or DEFAULT_ASSETS_DIR) / "icons"

    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        uri = asset_to_data_uri(icons_dir / f"{name}{ext}")
        if uri:
            return uri

    return None


def emoji_icon(
    emoji: str,
    name: str | None = None,
    *,
    assets_dir: str | Path | None = None,
    class_name: str = "render-icon",
    alt: str = "",
) -> str:
    """Render an icon image with a silent emoji fallback.

    Example:
        emoji_icon("🏆", "trophy")

    Looks for:
        assets/icons/trophy.png
        assets/icons/trophy.webp
        assets/icons/trophy.jpg
        assets/icons/trophy.jpeg

    If no file exists, the original emoji is returned so renders do not break.
    """
    icon_name = name or EMOJI_ICON_NAMES.get(emoji)
    if icon_name:
        uri = icon_uri(icon_name, assets_dir)
        if uri:
            safe_class = html_lib.escape(str(class_name), quote=True)
            safe_alt = html_lib.escape(str(alt or icon_name), quote=True)
            return f'<img class="{safe_class}" src="{uri}" alt="{safe_alt}">'

    return html_lib.escape(str(emoji))
