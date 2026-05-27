from __future__ import annotations

import html as html_lib
from typing import Any


def clamp_percent(percent: int | float | None) -> int:
    try:
        return max(0, min(100, int(round(float(percent or 0)))))
    except (TypeError, ValueError):
        return 0


def progress_class(percent: int | float | None) -> str:
    pct = clamp_percent(percent)
    if pct >= 90:
        return "progress-high"
    if pct >= 60:
        return "progress-mid"
    return "progress-low"


def progress_bar(percent: int | float | None, *, class_name: str = "summary") -> str:
    pct = clamp_percent(percent)
    return f'<div class="{class_name}-track"><div class="{class_name}-fill" style="width:{pct}%"></div></div>'


def summary_card(label: str, value: str, percent: int | float | None = 0, *, highlight: bool = False) -> str:
    pct = clamp_percent(percent)
    cls = f"summary-card {progress_class(pct)}"
    if highlight:
        cls += " summary-highlight"
    return f"""
    <div class="{cls}">
      <div class="summary-top">
        <div class="summary-label">{html_lib.escape(str(label))}</div>
        <div class="summary-value">{html_lib.escape(str(value))}</div>
      </div>
      {progress_bar(pct)}
    </div>
    """


def stat_tile(label: str, value: str, *, sub: str = "", icon: str = "", percent: int | float | None = None) -> str:
    sub_html = f'<div class="tile-sub">{html_lib.escape(str(sub))}</div>' if sub else ""
    icon_html = f'<span class="tile-emoji">{html_lib.escape(str(icon))}</span>' if icon else ""
    bar_html = progress_bar(percent, class_name="summary") if percent is not None else ""
    return f"""
    <div class="info-tile {progress_class(percent) if percent is not None else ''}">
      <div class="tile-head">{icon_html}<div class="tile-title">{html_lib.escape(str(label))}</div></div>
      <div class="tile-value">{html_lib.escape(str(value))}</div>
      {sub_html}
      {bar_html}
    </div>
    """


def panel(title: str, content: str, *, icon: str = "") -> str:
    display = f"{icon} {title}" if icon else str(title)
    return f"""
    <section class="panel">
      <h2>{html_lib.escape(display)}</h2>
      {content or ''}
    </section>
    """


def clash_document(title: str, subtitle: str, content: str, *, css: str, width: int = 1200) -> str:
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
{css}
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <div class="player-name">{html_lib.escape(str(title))}</div>
        <div class="player-sub">{html_lib.escape(str(subtitle))}</div>
      </div>
    </div>
    {content or ''}
  </div>
</body>
</html>
"""


def replace_tokens(template: str, values: dict[str, Any]) -> str:
    """Safely replace {{TOKEN}} placeholders in HTML templates."""
    html = template or ""
    for key, value in values.items():
        token = key if str(key).startswith("{{") else "{{" + str(key) + "}}"
        html = html.replace(token, str(value if value is not None else ""))
    return html


def render_dependency_summary(**deps: Any) -> dict[str, bool]:
    """Small helper for debugging injected renderer dependencies."""
    return {name: value is not None for name, value in deps.items()}
