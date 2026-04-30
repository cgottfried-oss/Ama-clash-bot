from __future__ import annotations

import discord

from html_renderer import render_html_to_discord_file


ADVISOR_SHELL_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px; width: 920px; min-height: 980px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .advisor-shell { width: 872px; min-height: 932px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 20px; }
  .advisor-shell-header { position: relative; padding: 17px 20px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 18px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }
  .advisor-shell-header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }
  .advisor-shell-title { position: relative; z-index: 1; font-size: 34px; line-height: 1; font-weight: 900; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }
  .advisor-shell-subtitle { position: relative; z-index: 1; font-size: 15px; margin-top: 6px; font-weight: 900; opacity: .92; text-shadow: 0 2px 0 rgba(0,0,0,.30); }
  .advisor-shell-content { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 14px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }
  .advisor-shell-content .card, .advisor-shell-content .container, .advisor-shell-content .wrap { max-width: 100%; }
"""


def _looks_like_full_html(content: str) -> bool:
    stripped = (content or "").lstrip()
    lowered = stripped[:500].lower()
    return "<html" in lowered or stripped.lower().startswith("<!doctype html")


def _wrap_fragment_in_clash_shell(content: str) -> str:
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
      <div class=\"advisor-shell-title\">Upgrade Advisor</div>
      <div class=\"advisor-shell-subtitle\">Personalized village recommendations</div>
    </div>
    <div class=\"advisor-shell-content\">
{content}
    </div>
  </div>
</body>
</html>
"""


def ensure_full_html_document(content: str) -> str:
    """Return a complete HTML document for Playwright rendering."""
    content = content or ""
    stripped = content.lstrip()

    if _looks_like_full_html(content):
        return content

    if stripped.startswith("body {") or ".container" in content[:2500]:
        print(
            "[ADVISOR_RENDER_WARNING] Received CSS-like content without a full HTML body.",
            flush=True,
        )
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
      <div class=\"advisor-shell-title\">Render Debug</div>
      <div class=\"advisor-shell-subtitle\">CSS was generated without a visible HTML body.</div>
    </div>
    <div class=\"advisor-shell-content\">
      <div class=\"container\">
        <div class=\"title\">Render Debug</div>
        <div class=\"subtitle\">CSS was generated without a visible HTML body.</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

    return _wrap_fragment_in_clash_shell(content)


async def render_advisor_card_to_file(
    html_content: str,
    filename: str,
    *,
    width: int = 920,
    height: int = 980,
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
