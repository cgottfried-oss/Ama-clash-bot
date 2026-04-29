from __future__ import annotations

import discord

from html_renderer import render_html_to_discord_file


def ensure_full_html_document(content: str) -> str:
    """Return a complete HTML document for Playwright rendering.

    Most advisor cards already pass a full document. This guard keeps malformed
    fragments from turning into blank screenshots and makes the issue visible.
    """
    content = content or ""
    stripped = content.lstrip()
    lowered = stripped[:500].lower()

    if "<html" in lowered or stripped.lower().startswith("<!doctype html"):
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
{content}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"container\">
      <div class=\"title\">Render Debug</div>
      <div class=\"subtitle\">CSS was generated without a visible HTML body.</div>
    </div>
  </div>
</body>
</html>
"""

    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
</head>
<body>
{content}
</body>
</html>
"""


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
