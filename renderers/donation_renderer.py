from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageFont


def _fmt_num(value: int) -> str:
    return f"{int(value):,}"


async def create_donation_image(
    leaderboard,
    *,
    template_path: str | None = None,
    width: int = 1000,
    height: int = 1400,
):
    leaderboard = leaderboard or []

    # Create a simple image instead of using Playwright
    img = Image.new("RGB", (width, height), (25, 30, 50))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except Exception:
        font_title = font = ImageFont.load_default()

    y = 40

    draw.text((40, y), "Donation Leaderboard", fill=(255, 255, 255), font=font_title)
    y += 80

    for idx, player in enumerate(leaderboard[:15], start=1):
        name = str(player.get("name", "Unknown"))
        donated = _fmt_num(player.get("donations", 0))
        received = _fmt_num(player.get("received", 0))

        line = f"#{idx} {name} | Donated: {donated} | Received: {received}"
        draw.text((40, y), line, fill=(200, 220, 255), font=font)
        y += 40

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
