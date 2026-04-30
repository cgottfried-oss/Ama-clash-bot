from __future__ import annotations

import html as html_lib


def progress_class(percent: int | float | None) -> str:
    try:
        pct = int(percent or 0)
    except (TypeError, ValueError):
        pct = 0
    if pct >= 90:
        return "progress-high"
    if pct >= 60:
        return "progress-mid"
    return "progress-low"


def progress_bar(percent: int | float | None) -> str:
    try:
        pct = max(0, min(100, int(percent or 0)))
    except (TypeError, ValueError):
        pct = 0
    return f'<div class="summary-track"><div class="summary-fill" style="width:{pct}%"></div></div>'


def summary_card(label: str, value: str, percent: int | float | None = 0, *, highlight: bool = False) -> str:
    pct = max(0, min(100, int(percent or 0)))
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


def panel(title: str, content: str) -> str:
    return f"""
    <section class="panel">
      <h2>{html_lib.escape(str(title))}</h2>
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
