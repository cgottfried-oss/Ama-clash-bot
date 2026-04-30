from __future__ import annotations

import re

import discord

from html_renderer import render_html_to_discord_file


ADVISOR_SHELL_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1000px; min-height: 1220px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .advisor-shell { width: 948px; min-height: 1168px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }
  .advisor-shell-header { position: relative; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 18px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }
  .advisor-shell-header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }
  .advisor-shell-title { position: relative; z-index: 1; font-size: 40px; line-height: 1.05; font-weight: 900; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }
  .advisor-shell-subtitle { position: relative; z-index: 1; font-size: 17px; margin-top: 7px; font-weight: 900; opacity: .92; text-shadow: 0 2px 0 rgba(0,0,0,.30); }
  .advisor-shell-content { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 16px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }
  .advisor-shell-content .wrap { padding: 0 !important; display: block !important; background: transparent !important; }
  .advisor-shell-content .container, .advisor-shell-content .card, .advisor-shell-content .card-shell { max-width: 100% !important; width: 100% !important; background: transparent !important; border: 0 !important; box-shadow: none !important; color: #fff !important; padding: 0 !important; }
  .advisor-shell-content .header { display: none !important; }
  .advisor-shell-content .title, .advisor-shell-content .section-title, .advisor-shell-content h1, .advisor-shell-content h2, .advisor-shell-content .pool-head { color: #fff !important; text-shadow: 0 3px 0 rgba(0,0,0,.42); font-weight: 900 !important; }
  .advisor-shell-content .subtitle, .advisor-shell-content .tile-title, .advisor-shell-content .tile-sub, .advisor-shell-content .footer-note, .advisor-shell-content .note, .advisor-shell-content p, .advisor-shell-content .pool-sub { color: rgba(255,255,255,.78) !important; }
  .advisor-shell-content .hero-grid, .advisor-shell-content .info-grid, .advisor-shell-content .stats-grid { gap: 12px !important; }
  .advisor-shell-content .info-tile, .advisor-shell-content .metric-card, .advisor-shell-content .spotlight-card, .advisor-shell-content .pick-row, .advisor-shell-content .ac-row, .advisor-shell-content .pool-box, .advisor-shell-content .pool-stat, .advisor-shell-content .notice, .advisor-shell-content .focus-card { background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)) !important; border: 1px solid rgba(255,255,255,.12) !important; box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08) !important; color: #fff !important; }
  .advisor-shell-content .info-tile, .advisor-shell-content .metric-card { min-height: 98px !important; }
  .advisor-shell-content .tile-value, .advisor-shell-content .ac-row-label, .advisor-shell-content .ac-row-ratio, .advisor-shell-content .stat-value, .advisor-shell-content strong, .advisor-shell-content .pick-title, .advisor-shell-content .spotlight-title { color: #fff !important; text-shadow: 0 2px 0 rgba(0,0,0,.28); }
  .advisor-shell-content .section { border-color: rgba(255,255,255,.13) !important; margin-top: 16px !important; padding-top: 16px !important; }
  .advisor-shell-content .ac-row-bar, .advisor-shell-content .bar, .advisor-shell-content .progress-track, .advisor-shell-content .track { background: rgba(10,14,27,.70) !important; box-shadow: inset 0 2px 2px rgba(0,0,0,.48) !important; }
  .advisor-shell-content .ac-row-fill, .advisor-shell-content .fill, .advisor-shell-content .progress-fill { background: linear-gradient(90deg, #45d5ff, #8f7dff 55%, #ffe05f) !important; box-shadow: 0 0 11px rgba(85,213,255,.35); }
  .advisor-shell-content .th-panel { background: radial-gradient(circle at 50% 38%, #74829f 0%, #3c496b 56%, #1d263e 100%) !important; border: 1px solid rgba(255,255,255,.14) !important; box-shadow: 0 4px 0 rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.16) !important; }
  .advisor-shell-content .th-pill { background: linear-gradient(180deg, rgba(72,76,139,.95), rgba(38,42,89,.95)) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 3px 0 rgba(0,0,0,.24) !important; }
  .advisor-shell-content img { filter: saturate(.96) contrast(.97) brightness(.94); }
  .advisor-shell-content .emoji-fallback { text-shadow: 0 2px 0 rgba(0,0,0,.30); }
"""


def _extract_body_inner(content: str) -> str:
    match = re.search(r"<body[^>]*>(.*?)</body>", content or "", flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else content


def _extract_title(content: str, fallback: str) -> str:
    match = re.search(r'<div class=["\']title["\']>(.*?)</div>', content or "", flags=re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r'<h1[^>]*>(.*?)</h1>', content or "", flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return fallback
    text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return text or fallback


def _extract_subtitle(content: str, fallback: str) -> str:
    match = re.search(r'<div class=["\']subtitle["\']>(.*?)</div>', content or "", flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return fallback
    text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return text or fallback


def _looks_like_css_only(content: str) -> bool:
    stripped = (content or "").lstrip().lower()
    if stripped.startswith(("<!doctype html", "<html", "<body", "<div", "<section")):
        return False
    return stripped.startswith("body {") or ("{" in stripped[:500] and "}" in stripped[:2000] and "<" not in stripped[:500])


def _wrap_in_clash_shell(content: str, *, title: str = "Upgrade Advisor", subtitle: str = "Personalized village recommendations") -> str:
    body = _extract_body_inner(content)
    title = _extract_title(content, title)
    subtitle = _extract_subtitle(content, subtitle)
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <style>
{ADVISOR_SHELL_CSS}
  </style>
</head>
<body>
  <div class=\"advisor-shell\">
    <div class=\"advisor-shell-header\">
      <div class=\"advisor-shell-title\">{title}</div>
      <div class=\"advisor-shell-subtitle\">{subtitle}</div>
    </div>
    <div class=\"advisor-shell-content\">
{body}
    </div>
  </div>
</body>
</html>
"""


def ensure_full_html_document(content: str) -> str:
    content = content or ""

    if _looks_like_css_only(content):
        print("[ADVISOR_RENDER_WARNING] CSS-only render payload received; wrapping CSS in a minimal visible body.", flush=True)
        return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <style>
{ADVISOR_SHELL_CSS}
{content}
  </style>
</head>
<body>
  <div class=\"advisor-shell\">
    <div class=\"advisor-shell-header\">
      <div class=\"advisor-shell-title\">Upgrade Advisor</div>
      <div class=\"advisor-shell-subtitle\">Render payload contained CSS only</div>
    </div>
    <div class=\"advisor-shell-content\">
      <div class=\"container\">
        <div class=\"title\">No visible HTML body was generated</div>
        <div class=\"subtitle\">The command returned stylesheet text instead of a full HTML document. Check the HTML builder return string.</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

    return _wrap_in_clash_shell(content)


async def render_advisor_card_to_file(
    html_content: str,
    filename: str,
    *,
    width: int = 1000,
    height: int = 1220,
    wait_ms: int = 900,
) -> discord.File:
    html = ensure_full_html_document(html_content)
    print(f"[ADVISOR_RENDER] filename={filename} html_len={len(html)}", flush=True)

    return await render_html_to_discord_file(
        html,
        filename,
        width=width,
        height=height,
        selector="body",
        wait_ms=wait_ms,
        device_scale_factor=2,
        timeout_ms=15000,
    )
