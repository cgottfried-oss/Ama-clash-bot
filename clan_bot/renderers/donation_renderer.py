from __future__ import annotations

import html
from typing import Any

from clan_bot.renderers.html_renderer import render_html_to_png_buffer


def _fmt_num(value: int) -> str:
    return f"{int(value):,}"


def _build_rows_html(leaderboard: list[dict[str, Any]]) -> str:
    if not leaderboard:
        return '<div class="donation-empty">No donation data yet.</div>'

    top_donated = max(
        [int(player.get("donations", 0) or 0) for player in leaderboard],
        default=0,
    )

    rows = []
    for idx, player in enumerate(leaderboard[:15], start=1):
        name = html.escape(str(player.get("name", "Unknown")))
        donated = int(player.get("donations", 0) or 0)
        received = int(player.get("received", 0) or 0)
        percent = 0 if top_donated <= 0 else max(4, min(100, round((donated / top_donated) * 100)))

        rows.append(
            f"""
            <div class="donation-row">
                <div class="donation-rank">#{idx}</div>
                <div class="donation-main">
                    <div class="donation-name">{name}</div>
                    <div class="donation-bar">
                        <div class="donation-fill" style="width: {percent}%"></div>
                    </div>
                </div>
                <div class="donation-stats">
                    <div><strong>{_fmt_num(donated)}</strong> donated</div>
                    <div>{_fmt_num(received)} received</div>
                </div>
            </div>
            """
        )

    return "\n".join(rows)


async def create_donation_image(
    leaderboard,
    *,
    template_path: str | None = None,
    width: int = 1000,
    height: int = 1400,
):
    leaderboard = leaderboard or []

    total_donated = sum(int(player.get("donations", 0) or 0) for player in leaderboard)
    total_received = sum(int(player.get("received", 0) or 0) for player in leaderboard)
    rows_html = _build_rows_html(leaderboard)

    if not template_path:
        raise ValueError("Donation template path is required")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    rendered_html = (
        template
        .replace("{{TOTAL_DONATIONS}}", _fmt_num(total_donated))
        .replace("{{TOTAL_RECEIVED}}", _fmt_num(total_received))
        .replace("{{ROWS_HTML}}", rows_html)
    )

    return await render_html_to_png_buffer(
        rendered_html,
        width=width,
        height=height,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )