from __future__ import annotations

import html as html_lib

from html_renderer import render_html_to_png_buffer


def _get_value(data: dict, *keys, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


async def create_link_audit_image(audit_data: dict):
    main = audit_data.get("main", {}) if isinstance(audit_data, dict) else {}
    feeder = audit_data.get("feeder", {}) if isinstance(audit_data, dict) else {}

    if main or feeder:
        main_linked = main.get("linked", []) if isinstance(main.get("linked", []), list) else []
        feeder_linked = feeder.get("linked", []) if isinstance(feeder.get("linked", []), list) else []
        main_unlinked = main.get("unlinked", []) if isinstance(main.get("unlinked", []), list) else []
        feeder_unlinked = feeder.get("unlinked", []) if isinstance(feeder.get("unlinked", []), list) else []

        linked_players = []
        for section_name, rows in (("Main", main_linked), ("Feeder", feeder_linked)):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                discord_name = row.get("discord_name") or row.get("display_name") or f"Discord ID {row.get('discord_id', '')}"
                accounts = row.get("accounts", [])
                if accounts:
                    for account in accounts:
                        if not isinstance(account, dict):
                            continue
                        linked_players.append({"name": account.get("player_name") or account.get("name") or "Unknown", "tag": account.get("tag", ""), "discord_name": f"{discord_name} • {section_name}"})
                else:
                    linked_players.append({"name": discord_name, "tag": "", "discord_name": section_name})

        unlinked_players = []
        for section_name, rows in (("Main", main_unlinked), ("Feeder", feeder_unlinked)):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                unlinked_players.append({"name": row.get("player_name") or row.get("name") or "Unknown", "tag": row.get("tag", ""), "clan_label": section_name})

        linked = len(main_linked) + len(feeder_linked)
        unlinked = len(unlinked_players)
        total = linked + unlinked
        linked_pct = round((linked / total) * 100, 1) if total else 0
    else:
        total = int(_get_value(audit_data, "total", "total_members", default=0) or 0)
        linked = int(_get_value(audit_data, "linked", "linked_count", default=0) or 0)
        unlinked = int(_get_value(audit_data, "unlinked", "unlinked_count", default=max(total - linked, 0)) or 0)
        linked_pct = round((linked / total) * 100, 1) if total else 0
        unlinked_players = audit_data.get("unlinked_players") or audit_data.get("unlinked") or audit_data.get("missing") or []
        linked_players = audit_data.get("linked_players") or audit_data.get("linked_members") or []

    if isinstance(unlinked_players, int):
        unlinked_players = []
    if isinstance(linked_players, int):
        linked_players = []

    unlinked_rows = ""
    for player in unlinked_players[:24]:
        if isinstance(player, str):
            name = html_lib.escape(player)
            tag = ""
            side = ""
        else:
            name = html_lib.escape(str(player.get("name", "Unknown")))
            tag = html_lib.escape(str(player.get("tag", "")))
            side = html_lib.escape(str(player.get("clan_label") or player.get("townHallLevel", player.get("townhallLevel", "?"))))

        unlinked_rows += f"""
        <div class="row warn">
            <div class="main"><span class="name">{name}</span><span class="tag">{tag}</span></div>
            <div class="pill warn-pill">{side}</div>
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
            user = html_lib.escape(str(player.get("discord") or player.get("discord_name") or player.get("discord_user") or "Linked"))

        linked_rows += f"""
        <div class="row good">
            <div class="main"><span class="name">{name}</span><span class="tag">{tag}</span></div>
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
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 26px; width: 980px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); font-family: Arial, Helvetica, sans-serif; color: #fff; }}
    .container {{ width: 928px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }}
    .header {{ position: relative; padding: 19px 22px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 18px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }}
    .header::after {{ content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }}
    .title {{ position: relative; z-index: 1; font-size: 40px; font-weight: 900; line-height: 1; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }}
    .subtitle {{ position: relative; z-index: 1; font-size: 17px; margin-top: 8px; font-weight: 900; opacity: .92; text-shadow: 0 2px 0 rgba(0,0,0,.30); }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 18px; }}
    .stat {{ border-radius: 15px; background: linear-gradient(180deg, rgba(72,76,139,.90), rgba(38,42,89,.86)); border: 2px solid rgba(255,255,255,.13); padding: 13px 12px; box-shadow: inset 0 2px 0 rgba(255,255,255,.14), 0 5px 0 rgba(0,0,0,.20); text-align: center; }}
    .num {{ font-size: 31px; font-weight: 900; line-height: 1; text-shadow: 0 3px 0 rgba(0,0,0,.36); }}
    .label {{ margin-top: 6px; font-size: 12px; font-weight: 900; opacity: .88; text-transform: uppercase; letter-spacing: .7px; }}
    .section {{ margin-top: 16px; border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 14px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }}
    .section h2 {{ margin: 0 0 12px; font-size: 25px; font-weight: 900; text-shadow: 0 3px 0 rgba(0,0,0,.48); }}
    .row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; margin-bottom: 9px; border-radius: 14px; background: linear-gradient(145deg, rgba(38,48,79,.84), rgba(23,30,52,.82)); border: 1px solid rgba(255,255,255,.11); box-shadow: 0 3px 0 rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08); }}
    .row.warn {{ border-left: 6px solid #ffb13d; }}
    .row.good {{ border-left: 6px solid #45e18d; }}
    .main {{ display: flex; flex-direction: column; gap: 3px; min-width: 0; }}
    .name {{ font-size: 18px; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.25); }}
    .tag {{ color: rgba(226,232,240,.82); font-size: 13px; font-weight: 800; }}
    .pill, .discord {{ color: #fff; font-size: 14px; font-weight: 900; text-align: right; max-width: 290px; text-shadow: 0 2px 0 rgba(0,0,0,.25); }}
    .warn-pill {{ padding: 5px 9px; border-radius: 999px; background: rgba(255,177,61,.20); border: 1px solid rgba(255,216,130,.35); }}
    .empty {{ padding: 20px; border-radius: 15px; background: rgba(18,24,43,.62); color: rgba(255,255,255,.76); text-align: center; font-weight: 900; }}
    .footer {{ margin-top: 18px; color: rgba(255,255,255,.64); font-size: 13px; text-align: center; font-weight: 800; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">🔗 Link Audit</div>
      <div class="subtitle">Discord account linking status for AM Allegiance</div>
    </div>

    <div class="stats">
      <div class="stat"><div class="num">{total}</div><div class="label">Total</div></div>
      <div class="stat"><div class="num">{linked}</div><div class="label">Linked</div></div>
      <div class="stat"><div class="num">{unlinked}</div><div class="label">Unlinked</div></div>
      <div class="stat"><div class="num">{linked_pct}%</div><div class="label">Complete</div></div>
    </div>

    <div class="section">
      <h2>⚠️ Needs Linking</h2>
      {unlinked_rows}
    </div>

    <div class="section">
      <h2>✅ Recently Linked</h2>
      {linked_rows}
    </div>

    <div class="footer">Generated by AM Allegiance bot</div>
  </div>
</body>
</html>
"""

    return await render_html_to_png_buffer(html, width=980, height=1300, selector="body", wait_ms=700, timeout_ms=15000)
