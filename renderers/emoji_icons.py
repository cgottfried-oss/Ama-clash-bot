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
    "troops": "troops",
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
    "donations": "donations",
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
    "📦": "loot_box",
    "🎁": "reward",
    "📥": "received",
    "📊": "ratio",
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
    "⚠️": "warning",
    "⚠": "warning",
    "ℹ️": "info",
    "ℹ": "info",
    "🔗": "link",
    "🐾": "pet_coin",
    "🧪": "spells",
    "⚙️": "siege_machines",
    "⚙": "siege_machines",
    "🏰": "defense",
}

# (rest unchanged)

def render_icon_css() -> str:
    return """
.render-icon { width: 1em; height: 1em; object-fit: contain; vertical-align: -0.14em; display: inline-block; }
.rank-icon { width: 34px; height: 34px; object-fit: contain; display: inline-block; }
.stat-icon { width: 18px; height: 18px; object-fit: contain; vertical-align: -0.18em; display: inline-block; }
.title-icon { width: 1.4em; height: 1.4em; object-fit: contain; vertical-align: -0.2em; display: inline-block; margin-right: 8px; filter: drop-shadow(0 2px 3px rgba(0,0,0,.4)); }
.progress-section h2 {
  display: flex;
  align-items: center;
  gap: 12px;
  line-height: 1;
  min-height: 42px;
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
.progress-section-icon.icon-hero_crown { transform: translate(0, 1px) scale(2.20); }
.progress-section-icon.icon-pet_coin { transform: scale(.82); }
.progress-section-icon.icon-troops { transform: scale(2.35); }
.progress-section-icon.icon-spells { transform: scale(2.45); }
.progress-section-icon.icon-siege_machines { transform: scale(1.55); }
"""
