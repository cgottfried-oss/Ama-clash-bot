from __future__ import annotations

import html as html_lib

from html_renderer import render_html_to_png_buffer


async def create_donation_image(
    leaderboard,
    *,
    template_path: str,
    width: int = 1000,
    height: int = 1400,
):
    """
    Render the monthly donation leaderboard using templates/donation_template.html.

    Expected template placeholders:
      {{TOTAL_DONATIONS}}
      {{TOTAL_RECEIVED}}
      {{ROWS_HTML}}
    """
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    leaderboard = leaderboard or []

    total_donations = sum(int(p.get("donations", 0) or 0) for p in leaderboard)
    total_received = sum(int(p.get("donationsReceived", 0) or 0) for p in leaderboard)
    max_donated = max((int(p.get("donations", 0) or 0) for p in leaderboard), default=0)

    rows_html = ""

    for idx, player in enumerate(leaderboard[:15], start=1):
        name = html_lib.escape(str(player.get("name", "Unknown")))
        donated = int(player.get("donations", 0) or 0)
        received = int(player.get("donationsReceived", 0) or 0)
        ratio = "∞" if received == 0 and donated > 0 else f"{(donated / received):.2f}" if received else "0.00"
        bar_pct = 0 if max_donated <= 0 else max(3, min(100, round((donated / max_donated) * 100)))

        rows_html += f"""
        <div class="donation-row">
            <div class="donation-rank">#{idx}</div>
            <div class="donation-main">
                <div class="donation-name">{name}</div>
                <div class="donation-bar">
                    <div class="donation-fill" style="width: {bar_pct}%"></div>
                </div>
            </div>
            <div class="donation-stats">
                📦 {donated:,} donated<br>
                📥 {received:,} received<br>
                📊 {ratio} ratio
            </div>
        </div>
        """

    if not rows_html:
        rows_html = '<div class="donation-empty">No donation data available yet.</div>'

    html = (
        template
        .replace("{{TOTAL_DONATIONS}}", f"{total_donations:,}")
        .replace("{{TOTAL_RECEIVED}}", f"{total_received:,}")
        .replace("{{ROWS_HTML}}", rows_html)
        # Backwards compatibility for older template variants.
        .replace("{{ total_donations }}", f"{total_donations:,}")
        .replace("{{ total_received }}", f"{total_received:,}")
        .replace("{{ rows }}", rows_html)
        .replace("{{ROWS}}", rows_html)
        .replace("{{rows}}", rows_html)
    )

    return await render_html_to_png_buffer(
        html,
        width=width,
        height=height,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )
