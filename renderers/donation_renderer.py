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
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    rows_html = ""
    for idx, player in enumerate(leaderboard[:15], start=1):
        name = html_lib.escape(str(player.get("name", "Unknown")))
        donated = int(player.get("donations", 0) or 0)
        received = int(player.get("donationsReceived", player.get("received", 0)) or 0)
        ratio = donated / received if received else donated

        if idx == 1:
            rank_class = "gold"
        elif idx == 2:
            rank_class = "silver"
        elif idx == 3:
            rank_class = "bronze"
        else:
            rank_class = ""

        rows_html += f"""
        <tr>
            <td class=\"rank {rank_class}\">#{idx}</td>
            <td class=\"player\">{name}</td>
            <td class=\"donated\">{donated:,}</td>
            <td class=\"received\">{received:,}</td>
            <td class=\"ratio\">{ratio:.2f}</td>
        </tr>
        """

    html = (
        template
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

