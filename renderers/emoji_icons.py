from __future__ import annotations

import html as html_lib
import os
from pathlib import Path

from renderers.icon_resolver import asset_to_data_uri


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))

ICON_NAMES: dict[str, str] = {
    "coin": "coin",
    "coins": "coins",
    "coin_special": "coin_special",
    "pet_coin": "pet_coin",
    "wallet": "wallet",
    "loot_box": "loot_box",
    "loot_chest": "loot_chest",
    "reward": "reward",
    "elixir": "elixir",
    "elixir_bottle": "elixir_bottle",
    "dark_elixir": "dark_elixir",
    "dark_elixir_stack": "dark_elixir_stack",
    "attack": "attack",
    "sword": "sword",
    "swords": "attack",
    "troops": "clancastle",
    "troop": "clancastle",
    "clancastle": "clancastle",
    "clan_castle": "clancastle",
    "axes": "axes",
    "bomb": "bomb",
    "rage": "rage",
    "scattershot": "scattershot",
    "star": "star",
    "stars": "stars",
    "ratio": "ratio",
    "destruction": "destruction",
    "trophy": "trophy",
    "crown": "crown",
    "hero_crown": "hero_crown",
    "trophy_statue": "trophy_statue",
    "trophy_pedestal": "trophy_pedestal",
    "badge": "badge",
    "rank": "rank",
    "gold_medal": "gold_medal",
    "silver_medal": "silver_medal",
    "bronze_medal": "bronze_medal",
    "shield": "shield",
    "defense": "defense",
    "inventory": "inventory",
    "shop": "shop",
    "reroll": "reroll",
    "structure": "structure",
    "ruins": "ruins",
    "builder_hut": "builder_hut",
    "utility": "utility",
    "shovel": "shovel",
    "siege": "siege_machines",
    "siege_machines": "siege_machines",
    "donations": "clancastle",
    "donation": "clancastle",
    "donated": "clancastle",
    "received": "clancastle",
    "spells": "spells",
    "success": "success",
    "error": "error",
    "warning": "warning",
    "info": "info",
    "link": "link",
}

EMOJI_ICON_NAMES: dict[str, str] = {
    "🥇": "gold_medal",
    "🥈": "silver_medal",
    "🥉": "bronze_medal",
    "🏆": "trophy",
    "👑": "hero_crown",
    "💰": "coin",
    "🪙": "coins",
    "📦": "clancastle",
    "🎁": "reward",
    "📥": "clancastle",
    "📊": "ratio",
    "🛒": "shop",
    "🎒": "inventory",
    "🔁": "reroll",
    "🏴": "war_banner",
    "🛡️": "shield",
    "✨": "lucky_charm",
    "🎲": "high_roller",
    "⭐": "star",
    "⚔️": "attack",
    "🗡️": "sword",
    "💣": "bomb",
    "🔥": "rage",
    "✅": "success",
    "❌": "error",
    "⚠️": "warning",
    "ℹ️": "info",
    "🔗": "link",
    "🐾": "pet_coin",
    "🧪": "spells",
    "⚙️": "siege_machines",
    "🏰": "clancastle",
}

ICON_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "donation": ("clancastle", "loot_box", "coin"),
    "donations": ("clancastle", "loot_box", "coin"),
    "donated": ("clancastle", "loot_box", "coin"),
    "received": ("clancastle", "elixir_bottle", "elixir", "loot_box"),
    "clancastle": ("clancastle", "clan_castle"),
    "clan_castle": ("clancastle", "clan_castle"),
    "loot": ("loot_box",),
    "loot_drop": ("loot_box",),
    "box": ("loot_box",),
    "ratio": ("ratio", "stats", "destruction"),
    "stats": ("ratio", "destruction", "axes"),
    "percent": ("ratio", "destruction", "stats", "axes"),
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
    "war_banner": ("attack", "sword"),
    "warning": ("error", "shield"),
    "link": ("badge", "shield"),
    "pet": ("pet_coin", "coin_special", "coin"),
    "pets": ("pet_coin", "coin_special", "coin"),
    "heroes": ("hero_crown", "crown", "trophy"),
    "hero": ("hero_crown", "crown", "trophy"),
    "crown": ("hero_crown", "crown"),
    "troops": ("clancastle", "clan_castle", "attack", "sword"),
    "troop": ("clancastle", "clan_castle", "attack", "sword"),
    "spells": ("spells", "elixir_bottle", "elixir"),
    "spell": ("spells", "elixir_bottle", "elixir"),
    "siege": ("siege_machines", "builder_hut", "structure"),
    "siege_machines": ("siege_machines", "builder_hut", "structure"),
}

RARITY_ICON_ALIASES: dict[str, tuple[str, ...]] = {
    "common": ("loot_box_common", "loot_box"),
    "rare": ("loot_box_rare", "loot_box"),
    "epic": ("loot_box_epic", "loot_chest", "loot_box"),
    "legendary": ("loot_chest_legendary", "loot_chest", "trophy"),
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


def _candidate_names(name: str) -> list[str]:
    raw = str(name or "").strip()
    if not raw:
        return []
    normalized = raw.lower().replace(" ", "_").replace("-", "_")
    title_case = normalized.title().replace("_", "_")
    names = [raw, normalized, title_case, ICON_NAMES.get(normalized, normalized)]
    names.extend(ICON_NAME_ALIASES.get(normalized, ()))
    names.extend(RARITY_ICON_ALIASES.get(normalized, ()))

    unique: list[str] = []
    seen: set[str] = set()
    for item in names:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def icon_uri(name: str, assets_dir: str | Path | None = None) -> str | None:
    for asset_dir in _candidate_asset_dirs(assets_dir):
        icons_dir = Path(asset_dir) / "icons"
        for icon_name in _candidate_names(name):
            for ext in (".png", ".webp", ".jpg", ".jpeg"):
                uri = asset_to_data_uri(icons_dir / f"{icon_name}{ext}")
                if uri:
                    return uri
    return None


def _icon_class_name(name: str) -> str:
    safe = str(name or "icon").strip().lower().replace(" ", "_").replace("-", "_")
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in safe)
    return safe or "icon"


def render_icon(
    name: str,
    fallback: str = "",
    *,
    assets_dir: str | Path | None = None,
    class_name: str = "render-icon",
    alt: str = "",
    rarity: str | None = None,
) -> str:
    uri = icon_uri(name, assets_dir)
    if uri:
        icon_class = _icon_class_name(name)
        safe_class = html_lib.escape(f"{class_name} icon-{icon_class}", quote=True)
        if rarity:
            safe_rarity = html_lib.escape(str(rarity).lower(), quote=True)
            safe_class = f"{safe_class} rarity-icon rarity-{safe_rarity}"
        safe_alt = html_lib.escape(str(alt or name), quote=True)
        return f'<img class="{safe_class}" src="{uri}" alt="{safe_alt}">'
    return html_lib.escape(str(fallback or ""))


def emoji_icon(
    emoji: str,
    name: str | None = None,
    *,
    assets_dir: str | Path | None = None,
    class_name: str = "render-icon",
    alt: str = "",
    rarity: str | None = None,
) -> str:
    icon_name = name or EMOJI_ICON_NAMES.get(emoji)
    if icon_name:
        return render_icon(
            icon_name,
            fallback=emoji,
            assets_dir=assets_dir,
            class_name=class_name,
            alt=alt or icon_name,
            rarity=rarity,
        )
    return html_lib.escape(str(emoji))


def rarity_icon(
    rarity: str,
    *,
    fallback: str = "📦",
    assets_dir: str | Path | None = None,
    class_name: str = "render-icon",
) -> str:
    tier = str(rarity or "common").strip().lower()
    return render_icon(
        tier,
        fallback=fallback,
        assets_dir=assets_dir,
        class_name=class_name,
        alt=f"{tier} rarity",
        rarity=tier,
    )


def rarity_class(rarity: str | None) -> str:
    tier = str(rarity or "common").strip().lower()
    if tier not in {"common", "rare", "epic", "legendary"}:
        tier = "common"
    return f"rarity-{tier}"


def render_icon_css() -> str:
    return """
.render-icon { width: 1em; height: 1em; object-fit: contain; vertical-align: -0.14em; display: inline-block; }
.render-icon.icon-clancastle {
  width: 1.75em !important;
  height: 1.75em !important;
  max-width: none !important;
  max-height: none !important;
  vertical-align: -0.35em;
}
.rank-icon { width: 34px; height: 34px; object-fit: contain; display: inline-block; }
.stat-icon { width: 18px; height: 18px; object-fit: contain; vertical-align: -0.18em; display: inline-block; }
.title-icon { width: 1.4em; height: 1.4em; object-fit: contain; vertical-align: -0.2em; display: inline-block; margin-right: 8px; filter: drop-shadow(0 2px 3px rgba(0,0,0,.4)); }
.progress-section h2 {
  display: flex;
  align-items: center;
  gap: 18px;
  line-height: 1;
  min-height: 72px;
  overflow: visible;
}
.progress-section-icon {
  flex: 0 0 38px;
  width: 38px !important;
  height: 38px !important;
  object-fit: contain;
  margin: 0 !important;
  vertical-align: 0;
  transform-origin: center center;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.42));
}
.progress-section-icon.icon-hero_crown { transform: translate(0, 1px) scale(1.00); }
.progress-section-icon.icon-pet_coin { transform: scale(.82); }
.progress-section-icon.icon-clancastle {
  flex: 0 0 58px !important;
  width: 58px !important;
  height: 58px !important;
  transform: translate(0, 1px);
}
.progress-section-icon.icon-spells { transform: scale(1.45); }
.progress-section-icon.icon-siege_machines { transform: scale(1.55); }
.rarity-icon { filter: drop-shadow(0 3px 3px rgba(0,0,0,.35)); }
.rarity-common { --rarity-glow: rgba(219,231,255,.22); --rarity-border: rgba(219,231,255,.36); }
.rarity-rare { --rarity-glow: rgba(69,213,255,.32); --rarity-border: rgba(69,213,255,.48); }
.rarity-epic { --rarity-glow: rgba(190,108,255,.38); --rarity-border: rgba(190,108,255,.56); }
.rarity-legendary { --rarity-glow: rgba(255,214,74,.46); --rarity-border: rgba(255,214,74,.70); }
.rarity-card { border-color: var(--rarity-border, rgba(255,255,255,.14)) !important; box-shadow: 0 0 22px var(--rarity-glow, rgba(255,255,255,.12)), inset 0 1px 0 rgba(255,255,255,.14), 0 8px 18px rgba(0,0,0,.24) !important; }
"""


def inject_render_icon_css(html: str) -> str:
    css = render_icon_css()
    if "</style>" in html:
        return html.replace("</style>", css + "\n</style>", 1)
    if "</head>" in html:
        return html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)
    return f"<style>\n{css}\n</style>\n{html}"


def replace_known_emojis(html: str, *, assets_dir: str | Path | None = None) -> str:
    output = html or ""
    for emoji in sorted(EMOJI_ICON_NAMES, key=len, reverse=True):
        if emoji not in output:
            continue
        output = output.replace(
            emoji,
            emoji_icon(emoji, assets_dir=assets_dir, class_name="render-icon"),
        )
    return output


def prepare_render_html(html: str, *, assets_dir: str | Path | None = None) -> str:
    return inject_render_icon_css(replace_known_emojis(html or "", assets_dir=assets_dir))
