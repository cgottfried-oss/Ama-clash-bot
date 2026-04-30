from __future__ import annotations

import html as html_lib

from html_renderer import render_html_to_png_buffer


def _fmt_num(value: int) -> str:
    return f"{int(value):,}"


async def create_donation_image(
    leaderboard,
    *,
    template_path: str | None = None,
    width: int = 1000,
    height: int = 1400,
):
    """Render the monthly donation leaderboard with the shared Clash-style visual language."""
    leaderboard = leaderboard or []

    total_donations = sum(int(p.get("donations", 0) or 0) for p in leaderboard)
    total_received = sum(int(p.get("donationsReceived", 0) or 0) for p in leaderboard)
    total_players = len(leaderboard)
    max_donated = max((int(p.get("donations", 0) or 0) for p in leaderboard), default=0)

    rows_html = ""

    for idx, player in enumerate(leaderboard[:15], start=1):
        name = html_lib.escape(str(player.get("name", "Unknown")))
        donated = int(player.get("donations", 0) or 0)
        received = int(player.get("donationsReceived", 0) or 0)
        ratio = "∞" if received == 0 and donated > 0 else f"{(donated / received):.2f}" if received else "0.00"
        bar_pct = 0 if max_donated <= 0 else max(3, min(100, round((donated / max_donated) * 100)))
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        row_class = " donation-row-top" if idx <= 3 else ""

        rows_html += f"""
        <div class="donation-row{row_class}">
          <div class="donation-rank">{medal}</div>
          <div class="donation-main">
            <div class="donation-name">{name}</div>
            <div class="donation-bar"><div class="donation-fill" style="width:{bar_pct}%"></div></div>
          </div>
          <div class="donation-stats">
            <div><span>📦</span> {_fmt_num(donated)}</div>
            <div><span>📥</span> {_fmt_num(received)}</div>
            <div><span>📊</span> {ratio}</div>
          </div>
        </div>
        """

    if not rows_html:
        rows_html = '<div class="donation-empty">No donation data available yet.</div>'

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 26px; width: 1000px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }}
  .container {{ width: 948px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }}
  .header {{ position: relative; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 18px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }}
  .header::after {{ content:""; position:absolute; inset:0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events:none; }}
  .title {{ position: relative; z-index: 1; font-size: 42px; font-weight: 900; line-height: 1; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }}
  .subtitle {{ position: relative; z-index: 1; font-size: 17px; margin-top: 8px; font-weight: 900; opacity: .92; text-shadow: 0 2px 0 rgba(0,0,0,.30); }}
  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 18px; }}
  .stat {{ border-radius: 15px; background: linear-gradient(180deg, rgba(72,76,139,.90), rgba(38,42,89,.86)); border: 2px solid rgba(255,255,255,.13); padding: 13px 12px; box-shadow: inset 0 2px 0 rgba(255,255,255,.14), 0 5px 0 rgba(0,0,0,.20); text-align: center; }}
  .num {{ font-size: 30px; font-weight: 900; line-height: 1; text-shadow: 0 3px 0 rgba(0,0,0,.36); }}
  .label {{ margin-top: 6px; font-size: 12px; font-weight: 900; opacity: .88; text-transform: uppercase; letter-spacing: .7px; }}
  .leaderboard {{ border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 14px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }}
  .leaderboard h2 {{ margin: 0 0 12px; font-size: 27px; font-weight: 900; text-shadow: 0 3px 0 rgba(0,0,0,.48); }}
  .donation-row {{ display: grid; grid-template-columns: 70px 1fr 170px; gap: 12px; align-items: center; padding: 12px 14px; margin-bottom: 10px; border-radius: 15px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.11); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); }}
  .donation-row-top {{ border: 2px solid rgba(255,221,89,.36); box-shadow: 0 3px 0 rgba(0,0,0,.22), 0 0 14px rgba(255,221,89,.13), inset 0 1px 0 rgba(255,255,255,.12); }}
  .donation-rank {{ font-size: 24px; font-weight: 900; text-align: center; text-shadow: 0 3px 0 rgba(0,0,0,.34); }}
  .donation-name {{ font-size: 20px; font-weight: 900; margin-bottom: 8px; text-shadow: 0 2px 0 rgba(0,0,0,.25); }}
  .donation-bar {{ height: 9px; border-radius: 999px; background: rgba(10,14,27,.70); overflow: hidden; box-shadow: inset 0 2px 2px rgba(0,0,0,.48); border: 1px solid rgba(255,255,255,.08); }}
  .donation-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, #45d5ff, #8f7dff 55%, #ffe05f); box-shadow: 0 0 11px rgba(85,213,255,.38); }}
  .donation-stats {{ font-size: 14px; line-height: 1.45; font-weight: 900; text-align: right; text-shadow: 0 2px 0 rgba(0,0,0,.25); }}
  .donation-empty {{ padding: 26px; border-radius: 15px; background: rgba(18,24,43,.62); color: rgba(255,255,255,.76); text-align: center; font-weight: 900; }}
  .footer {{ margin-top: 18px; color: rgba(255,255,255,.64); font-size: 13px; text-align: center; font-weight: 800; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">📦 Donation Leaderboard</div>
      <div class="subtitle">Monthly clan donation snapshot</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="num">{_fmt_num(total_donations)}</div><div class="label">Donated</div></div>
      <div class="stat"><div class="num">{_fmt_num(total_received)}</div><div class="label">Received</div></div>
      <div class="stat"><div class="num">{total_players}</div><div class="label">Players</div></div>
    </div>
    <div class="leaderboard">
      <h2>🏆 Top Donators</h2>
      {rows_html}
    </div>
    <div class="footer">Generated by AM Allegiance bot</div>
  </div>
</body>
</html>"""

    return await render_html_to_png_buffer(html, width=width, height=height, selector="body", wait_ms=700, timeout_ms=15000)
