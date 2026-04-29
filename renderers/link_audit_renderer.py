from __future__ import annotations

import html as html_lib

from html_renderer import render_html_to_png_buffer


def _get_value(data: dict, *keys, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


async def create_link_audit_image(audit_data: dict):
    total = int(_get_value(audit_data, "total", "total_members", default=0) or 0)
    linked = int(_get_value(audit_data, "linked", "linked_count", default=0) or 0)
    unlinked = int(_get_value(audit_data, "unlinked", "unlinked_count", default=max(total - linked, 0)) or 0)
    linked_pct = round((linked / total) * 100, 1) if total else 0

    unlinked_players = (
        audit_data.get("unlinked_players")
        or audit_data.get("unlinked")
        or audit_data.get("missing")
        or []
    )
    linked_players = (
        audit_data.get("linked_players")
        or audit_data.get("linked_members")
        or []
    )

    if isinstance(unlinked_players, int):
        unlinked_players = []
    if isinstance(linked_players, int):
        linked_players = []

    unlinked_rows = ""
    for player in unlinked_players[:24]:
        if isinstance(player, str):
            name = html_lib.escape(player)
            tag = ""
            th = "?"
        else:
            name = html_lib.escape(str(player.get("name", "Unknown")))
            tag = html_lib.escape(str(player.get("tag", "")))
            th = html_lib.escape(str(player.get("townHallLevel", player.get("townhallLevel", "?"))))

        unlinked_rows += f"""
        <div class="row warn">
            <div class="main">
                <span class="name">{name}</span>
                <span class="tag">{tag}</span>
            </div>
            <div class="th">TH{th}</div>
        </div>
        """

    linked_rows = ""
    for player in linked_players[:12]:
        if isinstance(player, str):
            name = html_lib.escape(player)
            tag = ""
            user = "Linked"
        else:
            name = html_lib.escape(str(player.get("name", "Unknown")))
            tag = html_lib.escape(str(player.get("tag", "")))
            user = html_lib.escape(str(
                player.get("discord")
                or player.get("discord_name")
                or player.get("discord_user")
                or "Linked"
            ))

        linked_rows += f"""
        <div class="row good">
            <div class="main">
                <span class="name">{name}</span>
                <span class="tag">{tag}</span>
            </div>
            <div class="discord">{user}</div>
        </div>
        """

    if not unlinked_rows:
        unlinked_rows = '<div class="empty">Everyone is linked ✅</div>'

    if not linked_rows:
        linked_rows = '<div class="empty">No linked players found.</div>'

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      padding: 28px;
      background: #0b1020;
      font-family: Arial, Helvetica, sans-serif;
      color: #f8fafc;
    }}
    .container {{
      width: 920px;
      border-radius: 28px;
      padding: 28px;
      background:
        radial-gradient(circle at top left, rgba(56,189,248,.25), transparent 35%),
        linear-gradient(135deg, #111827, #020617);
      box-shadow: 0 24px 80px rgba(0,0,0,.45);
      border: 1px solid rgba(148,163,184,.25);
    }}
    .title {{
      font-size: 38px;
      font-weight: 900;
      letter-spacing: .5px;
      margin-bottom: 8px;
    }}
    .subtitle {{
      color: #94a3b8;
      font-size: 18px;
      margin-bottom: 24px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 24px;
    }}
    .stat {{
      background: rgba(15,23,42,.76);
      border: 1px solid rgba(148,163,184,.18);
      border-radius: 18px;
      padding: 18px;
    }}
    .num {{
      font-size: 30px;
      font-weight: 900;
    }}
    .label {{
      color: #94a3b8;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .8px;
      margin-top: 4px;
    }}
    .section {{
      margin-top: 20px;
    }}
    .section h2 {{
      margin: 0 0 12px;
      font-size: 22px;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 13px 15px;
      margin-bottom: 9px;
      border-radius: 15px;
      background: rgba(15,23,42,.72);
      border: 1px solid rgba(148,163,184,.16);
    }}
    .row.warn {{
      border-left: 5px solid #f97316;
    }}
    .row.good {{
      border-left: 5px solid #22c55e;
    }}
    .main {{
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .name {{
      font-size: 17px;
      font-weight: 800;
    }}
    .tag {{
      color: #94a3b8;
      font-size: 13px;
    }}
    .th, .discord {{
      color: #e2e8f0;
      font-size: 15px;
      font-weight: 800;
    }}
    .empty {{
      padding: 22px;
      border-radius: 16px;
      background: rgba(15,23,42,.7);
      color: #94a3b8;
      text-align: center;
    }}
    .footer {{
      margin-top: 22px;
      color: #64748b;
      font-size: 13px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="title">🔗 Link Audit</div>
    <div class="subtitle">Discord account linking status for the clan</div>

    <div class="stats">
      <div class="stat"><div class="num">{total}</div><div class="label">Total</div></div>
      <div class="stat"><div class="num">{linked}</div><div class="label">Linked</div></div>
      <div class="stat"><div class="num">{unlinked}</div><div class="label">Unlinked</div></div>
      <div class="stat"><div class="num">{linked_pct}%</div><div class="label">Complete</div></div>
    </div>

    <div class="section">
      <h2>Needs Linking</h2>
      {unlinked_rows}
    </div>

    <div class="section">
      <h2>Recently Linked</h2>
      {linked_rows}
    </div>

    <div class="footer">Generated by AM Allegiance bot</div>
  </div>
</body>
</html>
"""

    return await render_html_to_png_buffer(
        html,
        width=980,
        height=1300,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )