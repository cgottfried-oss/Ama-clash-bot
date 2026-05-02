from __future__ import annotations

import html as html_lib
import os
from pathlib import Path

from renderers.icon_resolver import asset_to_data_uri


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))

# Generic, easy-to-replace filenames for render icons.
# Add any of these to assets/icons as .png, .webp, .jpg, or .jpeg.
EMOJI_ICON_NAMES: dict[str, str] = {
    "🥇": "gold_medal",
    "🥈": "silver_medal",
    "🥉": "bronze_medal",
    "🏆": "trophy",
    "👑": "crown",
    "💰": "coin",
    "🪙": "coins",
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
    "⚔️": "attack",
    "⚔": "attack",
    "🗡️": "sword",
    "🗡": "sword",
    "💣": "bomb",
    "🔥": "rage",
    "✅": "success",
    "❌": "error",
    "ℹ️": "info",
    "ℹ": "info",
}

# Aliases keep old/generic render names working even if the uploaded file uses
# the cleaner master icon-map name.
ICON_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "donation": ("loot_box", "coin"),
    "donated": ("loot_box", "coin"),
    "loot": ("loot_box",),
    "loot_drop": ("loot_box",),
    "box": ("loot_box",),
    "ratio": ("stats", "destruction"),
    "percent": ("destruction", "stats"),
    "received": ("elixir_bottle", "elixir", "loot_box"),
    "gold": ("coin",),
    "money": ("coin",),
    "medal_gold": ("gold_medal",),
    "medal_silver": ("silver_medal",),
    "medal_bronze": ("bronze_medal",),
    "swords": ("attack",),
    "crossed_swords": ("attack",),
    "fire": ("rage",),
    "high_roller": ("rage", "bomb"),
    "lucky_charm": ("coin_special", "coin"),
}


def _candidate_asset_dirs(assets_dir: str | Path | None = None) -> list[Path]:
    dirs = [Path(assets_dir)] if assets_dir else [DEFAULT_ASSETS_DIR, REPO_ROOT / "assets"]
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in dirs:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def icon_uri(name: str, assets_dir: str | Path | None = None) -> str | None:
    """Return a data URI for assets/icons/<name>.* when it exists."""
    names = [str(name)]
    names.extend(ICON_NAME_ALIASES.get(str(name), ()))

    seen_names: set[str] = set()
    for asset_dir in _candidate_asset_dirs(assets_dir):
        icons_dir = Path(asset_dir) / "icons"
        for icon_name in names:
            if not icon_name or icon_name in seen_names:
                continue
            seen_names.add(icon_name)
            for ext in (".png", ".webp", ".jpg", ".jpeg"):
                uri = asset_to_data_uri(icons_dir / f"{icon_name}{ext}")
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
