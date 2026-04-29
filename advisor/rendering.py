from __future__ import annotations

import discord

from renderers.advisor_renderer import render_advisor_card_to_file


async def render_html_card_to_file(
    html_content: str,
    filename: str,
    *,
    width: int = 920,
    height: int = 980,
    wait_ms: int = 900,
) -> discord.File:
    return await render_advisor_card_to_file(
        html_content,
        filename,
        width=width,
        height=height,
        wait_ms=wait_ms,
    )
