from __future__ import annotations

import base64
import html as html_lib
import mimetypes
from pathlib import Path
from typing import Any

import discord

from advisor.icon_mappings import ITEM_ICON_ASSET_MAP, ITEM_ICON_NAME_ALIASES
from html_renderer import render_html_to_png_buffer


STAT_EMOJIS = {
    "Attack Wins": "⚔️",
    "Defense Wins": "🛡️",
    "War Stars": "⭐",
    "Donations": "🏰",
    "Received": "📦",
    "Gold Grab": "🪙",
    "Elixir Escapade": "💧",
    "Heroic Heist": "🛢️",
    "Games Champion": "🏋️",
}


def _asset_to_data_uri(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _normalize_icon_name(name: str) -> str:
    return (
        str(name or "")
        .strip()
        .lower()
        .replace("&", " and ")
        .replace(".", "")
        .replace("'", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_icon_uri(row: dict[str, Any], assets_dir: str | Path) -> str | None:
    assets_dir = Path(assets_dir)
    icons_dir = assets_dir / "icons"

    key = str(row.get("key") or "").strip()
    name = str(row.get("name") or "").strip()

    candidates: list[str] = []

    if key:
        candidates.append(ITEM_ICON_ASSET_MAP.get(key, key))

    alias = ITEM_ICON_NAME_ALIASES.get(name)
    if alias:
        candidates.append(alias)

    if name:
        candidates.append(_normalize_icon_name(name))

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        for ext in (".png", ".webp", ".jpg", ".jpeg"):
            uri = _asset_to_data_uri(icons_dir / f"{candidate}{ext}")
            if uri:
                return uri

    return None


def _render_item(row: dict[str, Any], assets_dir: str | Path) -> str:
    level = html_lib.escape(str(row.get("level", "?")))
    name = html_lib.escape(str(row.get("name", "Unknown")))
    max_level = row.get("max_level")
    is_max = bool(row.get("is_max"))

    icon = find_icon_uri(row, assets_dir)
    if not icon:
        return ""

    icon_html = f'<img class="item-icon" src="{icon}" alt="{name}">'

    max_badge = '<div class="max-badge">MAX</div>' if is_max else ""
    level_title = f"{level}/{max_level}" if max_level else level

    return f"""
    <div class="item" title="{name} {html_lib.escape(str(level_title))}">
      {icon_html}
      <div class="level">{level}</div>
      {max_badge}
    </div>
    """


def _render_section(title: str, rows: list[dict[str, Any]], assets_dir: str | Path) -> str:
    if not rows:
        body = '<div class="empty">No data</div>'
    else:
        rendered_items = [item_html for row in rows if (item_html := _render_item(row, assets_dir))]
        body = "".join(rendered_items) if rendered_items else '<div class="empty">No data</div>'

    return f"""
    <section class="panel">
      <h2>{html_lib.escape(title)}</h2>
      <div class="grid">{body}</div>
    </section>
    """


def _format_stat_value(value: Any) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,}".replace(",", " ")


def _render_stat(label: str, value: Any) -> str:
    emoji = STAT_EMOJIS.get(str(label), "⭐")
    return f"""
    <div class="stat-card">
      <div class="stars">★★★</div>
      <div class="stat-icon">{emoji}</div>
      <div class="stat-copy">
        <div class="stat-label">{html_lib.escape(str(label))}</div>
        <div class="stat-value">{html_lib.escape(_format_stat_value(value))}</div>
      </div>
    </div>
    """


async def create_current_progress_file(
    progress_data: dict[str, Any],
    *,
    assets_dir: str | Path,
    filename: str = "currentprogress.png",
) -> discord.File:
    player = progress_data.get("player", {})
    sections = progress_data.get("sections", {})
    stats = progress_data.get("stats", {})

    player_name = html_lib.escape(str(player.get("name", "Unknown")))
    player_tag = html_lib.escape(str(player.get("tag", "")))
    clan_name = html_lib.escape(str(player.get("clan", "No Clan")))
    league = html_lib.escape(str(player.get("league", "Unranked")))
    th = html_lib.escape(str(player.get("town_hall", "?")))
    exp = html_lib.escape(str(player.get("exp_level", "?")))
    trophies = html_lib.escape(str(player.get("trophies", 0)))

    stat_html = "".join(_render_stat(label, value) for label, value in stats.items())

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; width: 1200px; background: linear-gradient(135deg, #6d7b98, #56647f); color: #fff; font-family: Arial, Helvetica, sans-serif; }}
  .card {{ width: 1144px; border-radius: 18px; background: rgba(35, 42, 68, .35); border: 2px solid rgba(255,255,255,.18); box-shadow: 0 18px 50px rgba(0,0,0,.28); padding: 24px; }}
  .header {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 18px; border-radius: 16px; background: rgba(20, 25, 45, .28); margin-bottom: 22px; }}
  .player-name {{ font-size: 42px; font-weight: 900; }}
  .player-sub {{ font-size: 20px; opacity: .92; margin-top: 4px; font-weight: 800; }}
  .th-box {{ text-align: right; font-size: 22px; font-weight: 900; }}
  .layout {{ display: grid; grid-template-columns: 280px 1fr 280px; gap: 18px; }}
  .left-col,.right-col,.middle-col {{ display: flex; flex-direction: column; gap: 18px; }}
  .panel {{ border-radius: 12px; background: rgba(35, 42, 68, .42); padding: 12px; }}
  h2 {{ margin: 0 0 10px; font-size: 28px; font-weight: 900; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }}
  .item {{ position: relative; width: 58px; height: 58px; border-radius: 8px; background: rgba(13, 18, 35, .42); overflow: hidden; }}
  .item-icon {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .level {{ position: absolute; left: 0; bottom: 0; padding: 1px 4px; background: rgba(15,15,20,.88); font-size: 13px; font-weight: 900; }}
  .max-badge {{ position: absolute; right: 2px; top: 2px; font-size: 9px; background: rgba(255,219,77,.92); color: #2c1b00; border-radius: 4px; padding: 1px 3px; font-weight: 900; }}
  .stats-panel {{ margin-top: 18px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
  .stat-card {{ min-height: 64px; border-radius: 10px; background: linear-gradient(180deg, rgba(230,237,245,.45), rgba(145,158,178,.48)); border: 2px solid rgba(255,255,255,.72); box-shadow: inset 0 2px 0 rgba(255,255,255,.32), 0 2px 0 rgba(0,0,0,.20); display: grid; grid-template-columns: 86px 46px 1fr; align-items: center; padding: 8px 10px; overflow: hidden; }}
  .stars {{ color: #ffd85a; font-size: 25px; letter-spacing: -2px; text-shadow: 0 2px 0 rgba(0,0,0,.45), -1px -1px 0 #fff3a8; white-space: nowrap; }}
  .stat-icon {{ font-size: 34px; text-align: center; filter: drop-shadow(0 2px 1px rgba(0,0,0,.35)); }}
  .stat-copy {{ min-width: 0; }}
  .stat-label {{ display: inline-block; min-width: 150px; padding: 2px 9px; border-radius: 7px 7px 2px 2px; background: rgba(239,246,255,.24); color: #fff; font-size: 14px; line-height: 1; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.45); }}
  .stat-value {{ margin-top: -1px; display: inline-block; min-width: 108px; padding: 3px 10px 4px; border-radius: 2px 6px 6px 2px; background: rgba(45,42,93,.78); color: #fff; font-size: 22px; line-height: 1; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.55); }}
  .empty {{ color: rgba(255,255,255,.72); font-weight: 800; font-size: 14px; padding: 10px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <div class="player-name">{player_name}</div>
        <div class="player-sub">{player_tag} • {clan_name} • {league} • 🏆 {trophies}</div>
      </div>
      <div class="th-box">TH {th}<br>XP {exp}</div>
    </div>

    <div class="layout">
      <div class="left-col">
        {_render_section("Heroes", sections.get("Heroes", []), assets_dir)}
        {_render_section("Pets", sections.get("Pets", []), assets_dir)}
      </div>
      <div class="middle-col">
        {_render_section("Troops", sections.get("Troops", []), assets_dir)}
        {_render_section("Siege Machines", sections.get("Siege Machines", []), assets_dir)}
      </div>
      <div class="right-col">
        {_render_section("Spells", sections.get("Spells", []), assets_dir)}
      </div>
    </div>

    <div class="stats-panel">{stat_html}</div>
  </div>
</body>
</html>"""

    buffer = await render_html_to_png_buffer(
        html_doc,
        width=1200,
        height=1050,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )

    return discord.File(buffer, filename=filename)
