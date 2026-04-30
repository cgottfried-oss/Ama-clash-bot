from __future__ import annotations

import base64
import html as html_lib
import mimetypes
from pathlib import Path
from typing import Any

import discord

from advisor.icon_mappings import ITEM_ICON_ASSET_MAP, ITEM_ICON_NAME_ALIASES
from html_renderer import render_html_to_png_buffer

SECTION_ICONS = {
    "Heroes": "👑",
    "Pets": "🐾",
    "Troops": "⚔️",
    "Spells": "🧪",
    "Siege Machines": "⚙️",
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

    item_class = "item item-max" if is_max else "item"
    icon_html = f'<img class="item-icon" src="{icon}" alt="{name}">'
    max_badge = '<div class="max-badge">MAX</div>' if is_max else ""
    level_title = f"{level}/{max_level}" if max_level else level

    return f"""
    <div class="{item_class}" title="{name} {html_lib.escape(str(level_title))}">
      <div class="icon-backplate">{icon_html}</div>
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

    section_icon = SECTION_ICONS.get(title, "")
    display_title = f"{section_icon} {title}" if section_icon else title

    return f"""
    <section class="panel">
      <h2>{html_lib.escape(display_title)}</h2>
      <div class="grid">{body}</div>
    </section>
    """


def _render_summary_row(row: dict[str, Any]) -> str:
    label = html_lib.escape(str(row.get("label")))
    value = html_lib.escape(str(row.get("value")))
    percent = int(row.get("percent") or 0)
    percent = max(0, min(100, percent))
    highlight = " summary-highlight" if "Snapshot" in str(row.get("label")) else ""

    return f"""
    <div class="summary-card{highlight}">
      <div class="summary-top">
        <div class="summary-label">{label}</div>
        <div class="summary-value">{value}</div>
      </div>
      <div class="summary-track"><div class="summary-fill" style="width:{percent}%"></div></div>
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
    summary = progress_data.get("summary", [])

    player_name = html_lib.escape(str(player.get("name", "Unknown")))
    player_tag = html_lib.escape(str(player.get("tag", "")))
    clan_name = html_lib.escape(str(player.get("clan", "No Clan")))
    league = html_lib.escape(str(player.get("league", "Unranked")))
    th = html_lib.escape(str(player.get("town_hall", "?")))
    exp = html_lib.escape(str(player.get("exp_level", "?")))
    trophies = html_lib.escape(str(player.get("trophies", 0)))

    summary_html = "".join(_render_summary_row(row) for row in summary)

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; width: 1200px; background: radial-gradient(circle at top left, #8491ad 0%, #54627e 48%, #46536d 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }}
  .card {{ width: 1144px; border-radius: 20px; background: linear-gradient(145deg, rgba(56,67,98,.55), rgba(33,41,66,.40)); border: 2px solid rgba(255,255,255,.22); box-shadow: 0 20px 55px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.16); padding: 24px; }}
  .header {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px; border-radius: 18px; background: linear-gradient(135deg, rgba(33,42,70,.86), rgba(56,66,102,.78)); margin-bottom: 22px; box-shadow: inset 0 1px 0 rgba(255,255,255,.12); }}
  .player-name {{ font-size: 44px; line-height: 1; font-weight: 900; letter-spacing: .3px; text-shadow: 0 3px 0 rgba(0,0,0,.32); }}
  .player-sub {{ font-size: 20px; opacity: .95; margin-top: 8px; font-weight: 800; }}
  .th-box {{ text-align: right; font-size: 22px; font-weight: 900; line-height: 1.25; text-shadow: 0 2px 0 rgba(0,0,0,.32); }}
  .layout {{ display: grid; grid-template-columns: 280px 1fr 280px; gap: 18px; align-items:start; }}
  .left-col,.right-col,.middle-col {{ display: flex; flex-direction: column; gap: 18px; }}
  .panel {{ border-radius: 14px; background: linear-gradient(145deg, rgba(34,43,72,.67), rgba(45,55,88,.55)); padding: 13px; box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 6px 14px rgba(0,0,0,.10); }}
  h2 {{ margin: 0 0 12px; font-size: 28px; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.42); }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }}
  .item {{ position: relative; width: 58px; height: 58px; border-radius: 9px; background: linear-gradient(145deg, #2c344e, #1e263d); overflow: hidden; box-shadow: 0 3px 0 rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.10); }}
  .item-max {{ box-shadow: 0 3px 0 rgba(0,0,0,.38), 0 0 0 2px rgba(255,218,82,.45), 0 0 13px rgba(255,218,82,.25); }}
  .icon-backplate {{ width: 100%; height: 100%; background: radial-gradient(circle at 50% 42%, #6f7b96 0%, #3f4965 55%, #273049 100%); display: flex; align-items: center; justify-content: center; }}
  .item-icon {{ width: 100%; height: 100%; object-fit: cover; display: block; mix-blend-mode: normal; }}
  .level {{ position: absolute; left: 0; bottom: 0; min-width: 21px; padding: 1px 4px; background: rgba(13,14,22,.92); border-top-right-radius: 5px; font-size: 13px; font-weight: 900; text-shadow: 0 1px 0 #000; }}
  .max-badge {{ position: absolute; right: 2px; top: 2px; font-size: 9px; background: linear-gradient(180deg, #ffe981, #e6b92d); color: #2c1b00; border-radius: 4px; padding: 1px 3px; font-weight: 900; box-shadow: 0 1px 0 rgba(0,0,0,.35); }}
  .summary-panel {{ margin-top: 18px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
  .summary-card {{ border-radius: 12px; background: linear-gradient(145deg, rgba(52,54,111,.82), rgba(41,44,91,.78)); border: 1px solid rgba(255,255,255,.11); padding: 11px 13px; box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 4px 10px rgba(0,0,0,.16); }}
  .summary-highlight {{ background: linear-gradient(145deg, rgba(83,68,140,.92), rgba(47,45,101,.86)); box-shadow: inset 0 1px 0 rgba(255,255,255,.15), 0 0 18px rgba(145,125,255,.18); }}
  .summary-top {{ display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }}
  .summary-label {{ font-size: 14px; font-weight: 900; opacity: .92; white-space: nowrap; }}
  .summary-value {{ font-size: 24px; font-weight: 900; line-height: 1; text-shadow: 0 2px 0 rgba(0,0,0,.35); }}
  .summary-track {{ margin-top: 9px; height: 7px; border-radius: 999px; background: rgba(18,22,42,.62); overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,.45); }}
  .summary-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #77e3ff, #9b8cff, #ffd866); box-shadow: 0 0 10px rgba(119,227,255,.35); }}
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

    <div class="summary-panel">{summary_html}</div>
  </div>
</body>
</html>"""

    buffer = await render_html_to_png_buffer(
        html_doc,
        width=1200,
        height=980,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )

    return discord.File(buffer, filename=filename)
