from __future__ import annotations

import html as html_lib
import os
import re
from pathlib import Path

from renderers.icon_resolver import asset_to_data_uri

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))

# (unchanged code above omitted for brevity)

# 🔥 UPDATED CSS FIX
def render_icon_css() -> str:
    return """
.render-icon { width: 1em; height: 1em; object-fit: contain; vertical-align: -0.14em; display: inline-block; }
.rank-icon { width: 34px; height: 34px; object-fit: contain; display: inline-block; }
.stat-icon { width: 18px; height: 18px; object-fit: contain; vertical-align: -0.18em; display: inline-block; }

/* 🚀 FIX: Make header icons (like hero crown) bigger */
.title-icon { 
  width: 1.4em; 
  height: 1.4em; 
  object-fit: contain; 
  vertical-align: -0.2em; 
  display: inline-block; 
  margin-right: 8px;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.4));
}

.section-title .render-icon {
  width: 1.35em;
  height: 1.35em;
  vertical-align: -0.18em;
}

.rarity-icon { filter: drop-shadow(0 3px 3px rgba(0,0,0,.35)); }
.rarity-common { --rarity-glow: rgba(219,231,255,.22); --rarity-border: rgba(219,231,255,.36); }
.rarity-rare { --rarity-glow: rgba(69,213,255,.32); --rarity-border: rgba(69,213,255,.48); }
.rarity-epic { --rarity-glow: rgba(190,108,255,.38); --rarity-border: rgba(190,108,255,.56); }
.rarity-legendary { --rarity-glow: rgba(255,214,74,.46); --rarity-border: rgba(255,214,74,.70); }
.rarity-card { border-color: var(--rarity-border, rgba(255,255,255,.14)) !important; box-shadow: 0 0 22px var(--rarity-glow, rgba(255,255,255,.12)), inset 0 1px 0 rgba(255,255,255,.14), 0 8px 18px rgba(0,0,0,.24) !important; }
"""
