from __future__ import annotations

import html
from typing import Any


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def summary_card(label: str, value: str, icon: str = "") -> str:
    icon_html = f'<div class="summary-icon">{esc(icon)}</div>' if icon else ""
    return f"""
    <div class="summary-card">
      {icon_html}
      <div class="summary-label">{esc(label)}</div>
      <div class="summary-value">{esc(value)}</div>
    </div>
    """


def summary_card_raw(label: str, value: str, icon_html: str = "") -> str:
    """Summary card variant that accepts trusted pre-rendered icon HTML."""
    wrapped_icon = f'<div class="summary-icon summary-icon-raw">{icon_html}</div>' if icon_html else ""
    return f"""
    <div class="summary-card">
      {wrapped_icon}
      <div class="summary-label">{esc(label)}</div>
      <div class="summary-value">{esc(value)}</div>
    </div>
    """


def townhall_summary_card(advisor: Any, player_name: str, town_hall: Any) -> str:
    th_text = str(town_hall or "?").replace("TH", "").replace("th", "").strip()
    icon_html = ""
    if th_text and th_text != "?":
        for key in (
            f"th_{th_text}",
            f"townhall_{th_text}",
            f"town_hall_{th_text}",
            f"th{th_text}",
            f"townhall{th_text}",
        ):
            icon_html = advisor._render_icon_html(
                icon_key=key,
                label=f"TH{th_text}",
                fallback="",
                kind="item",
                css_class="summary-icon-img",
            )
            if "summary-icon-img" in icon_html and "span" not in icon_html[:20].lower():
                break
    return summary_card_raw("Account", f"{player_name} · TH{town_hall or '?'}", icon_html or '<span>🏰</span>')


def metric_row(label: str, current: int, total: int, icon: str = "") -> str:
    total = max(1, int(total or 1))
    current = max(0, int(current or 0))
    pct = max(0, min(100, round((current / total) * 100)))
    return f"""
    <div class="metric-row">
      <div class="metric-name"><span>{esc(icon)}</span>{esc(label)}</div>
      <div class="metric-track"><div class="metric-fill" style="width:{pct}%"></div></div>
      <div class="metric-value">{current}/{total} · {pct}%</div>
    </div>
    """


def status_note(text: str, icon: str = "✅") -> str:
    return f"""
    <div class="status-note">
      <span class="status-icon">{esc(icon)}</span>
      <span>{esc(text)}</span>
    </div>
    """


def base_upgrade_card_html(title: str, subtitle: str, summary_html: str, board_html: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 26px; width: 1000px; min-height: 1220px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }}
.shell {{ width: 948px; min-height: 1168px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }}
.header {{ position: relative; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 18px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }}
.header::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); }}
.title {{ position: relative; z-index: 1; font-size: 42px; line-height: 1.05; font-weight: 900; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }}
.subtitle {{ position: relative; z-index: 1; font-size: 17px; margin-top: 7px; font-weight: 900; opacity: .92; text-shadow: 0 2px 0 rgba(0,0,0,.30); }}
.panel {{ border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 16px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }}
.summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }}
.summary-card {{ min-height: 98px; border-radius: 15px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.12); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); padding: 13px; }}
.summary-icon {{ font-size: 22px; line-height: 1; margin-bottom: 6px; text-shadow: 0 2px 0 rgba(0,0,0,.35); min-height: 28px; display: flex; align-items: center; }}
.summary-icon-img {{ width: 42px !important; height: 42px !important; max-width: 42px !important; max-height: 42px !important; object-fit: contain !important; display: block; border-radius: 8px; }}
.summary-label {{ font-size: 15px; font-weight: 900; color: rgba(255,255,255,.72); }}
.summary-value {{ margin-top: 6px; font-size: 22px; font-weight: 900; color: #fff; text-shadow: 0 2px 0 rgba(0,0,0,.32); line-height: 1.08; }}
.board {{ width: 100%; }}
.section-title {{ font-size: 27px; font-weight: 900; text-align: center; margin: 20px 0 14px; color: #fff; text-shadow: 0 3px 0 rgba(0,0,0,.42); }}
.note {{ border-radius: 15px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.12); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); padding: 14px 16px; font-size: 17px; line-height: 1.55; color: rgba(255,255,255,.82); }}
.note strong {{ color: #fff; text-shadow: 0 2px 0 rgba(0,0,0,.28); }}
.metric-row {{ display: grid; grid-template-columns: 230px 1fr 150px; gap: 14px; align-items: center; border-radius: 15px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.12); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); padding: 14px 16px; margin: 11px 0; }}
.metric-name {{ font-size: 18px; font-weight: 900; color: #fff; display: flex; gap: 8px; align-items: center; text-shadow: 0 2px 0 rgba(0,0,0,.28); }}
.metric-track {{ height: 12px; border-radius: 999px; background: rgba(10,14,27,.70); overflow: hidden; box-shadow: inset 0 2px 2px rgba(0,0,0,.48); }}
.metric-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #45d5ff, #8f7dff 55%, #ffe05f); box-shadow: 0 0 11px rgba(85,213,255,.35); }}
.metric-value {{ text-align: right; font-size: 16px; font-weight: 900; color: #fff; text-shadow: 0 2px 0 rgba(0,0,0,.28); }}
.status-note {{ display: flex; gap: 10px; align-items: flex-start; border-radius: 15px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.12); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); padding: 14px 16px; margin-top: 12px; font-size: 17px; color: rgba(255,255,255,.86); }}
.status-icon {{ font-size: 20px; }}
img.nu-icon, img.nu-spot-icon, img.summary-icon-img {{ object-fit: contain !important; }}
</style>
</head>
<body>
<div class="shell">
  <div class="header">
    <div class="title">{esc(title)}</div>
    <div class="subtitle">{esc(subtitle)}</div>
  </div>
  <div class="panel">
    <div class="summary">{summary_html}</div>
    <div class="board">{board_html}</div>
  </div>
</div>
</body>
</html>
"""
