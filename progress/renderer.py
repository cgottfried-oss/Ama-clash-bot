from __future__ import annotations

import html as html_lib
from pathlib import Path
from typing import Any

import discord

from renderers.icon_resolver import find_icon_uri
from renderers.emoji_icons import render_icon
from renderers.theme import CURRENT_PROGRESS_CSS
from html_renderer import render_html_to_png_buffer

TEMPLATE_PATH = Path(__file__).parent / "templates" / "current_progress.html"

SECTION_ICONS = {
    "Heroes": "hero_crown",
    "Pets": "pet_coin",
    "Troops": "troops",
    "Spells": "spells",
    "Siege Machines": "siege_machines",
}


def _progress_class(percent: int) -> str:
    if percent >= 90:
        return "progress-high"
    if percent >= 60:
        return "progress-mid"
    return "progress-low"


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

    icon_name = SECTION_ICONS.get(title, "")
    icon_html = render_icon(
        icon_name,
        fallback="",
        assets_dir=assets_dir,
        class_name="render-icon progress-section-icon",
        alt=title,
    ) if icon_name else ""

    return f"""
    <section class="panel progress-section progress-section-{html_lib.escape(title.lower().replace(' ', '-'))}">
      <h2>{icon_html}{html_lib.escape(title)}</h2>
      <div class="grid">{body}</div>
    </section>
    """


def _render_summary_row(row: dict[str, Any]) -> str:
    label = html_lib.escape(str(row.get("label")))
    value = html_lib.escape(str(row.get("value")))
    percent = int(row.get("percent") or 0)
    percent = max(0, min(100, percent))
    highlight = " summary-highlight" if "Snapshot" in str(row.get("label")) else ""
    progress_class = _progress_class(percent)

    return f"""
    <div class="summary-card{highlight} {progress_class}">
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

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    league_icon_html = ""
    if player.get("league_icon"):
        league_icon_html = render_icon(
            player.get("league_icon"),
            fallback="",
            assets_dir=assets_dir,
            class_name="render-icon",
            alt=player.get("league", ""),
        )

    html_doc = template.format(
        css=CURRENT_PROGRESS_CSS,
        player_name=html_lib.escape(str(player.get("name", "Unknown"))),
        player_tag=html_lib.escape(str(player.get("tag", ""))),
        clan_name=html_lib.escape(str(player.get("clan", "No Clan"))),
        league=html_lib.escape(str(player.get("league", "Unranked"))),
        league_icon_html=league_icon_html,
        th=html_lib.escape(str(player.get("town_hall", "?"))),
        exp=html_lib.escape(str(player.get("exp_level", "?"))),
        heroes_section=_render_section("Heroes", sections.get("Heroes", []), assets_dir),
        pets_section=_render_section("Pets", sections.get("Pets", []), assets_dir),
        troops_section=_render_section("Troops", sections.get("Troops", []), assets_dir),
        siege_section=_render_section("Siege Machines", sections.get("Siege Machines", []), assets_dir),
        spells_section=_render_section("Spells", sections.get("Spells", []), assets_dir),
        summary_html="".join(_render_summary_row(row) for row in summary),
    )

    buffer = await render_html_to_png_buffer(
        html_doc,
        width=1200,
        height=980,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )

    return discord.File(buffer, filename=filename)
