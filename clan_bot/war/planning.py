from __future__ import annotations

from collections import defaultdict


def build_war_plan_data(war, data):
    assignments = data.get("assignments", [])
    hit_order = data.get("hit_order", [])
    captain_calls = data.get("captain_calls", [])

    filtered_assignments = []
    for a in assignments:
        target = next(
            (
                t
                for t in war.get("opponent", {}).get("members", [])
                if t.get("mapPosition") == a["primary"]
            ),
            None,
        )
        if not target:
            continue

        best = target.get("bestOpponentAttack")
        if best and best.get("stars") == 3:
            continue

        filtered_assignments.append(a)

    target_map = defaultdict(list)
    for a in filtered_assignments:
        target_map[a["primary"]].append(a)

    plan_targets = []
    for target_num, attackers in sorted(target_map.items()):
        attackers_sorted = sorted(
            attackers,
            key=lambda x: (
                hit_order.index(x["player"]) if x["player"] in hit_order else 999
            ),
        )

        target_attackers = []
        for i, atk in enumerate(attackers_sorted):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "•"
            line = atk["player"]

            if atk.get("backup"):
                backups = ", ".join(f"#{b}" for b in atk["backup"])
                line += f" ↪ Backup: {backups}"

            target_attackers.append(
                {
                    "medal": medal,
                    "text": line,
                }
            )

        plan_targets.append(
            {
                "target": target_num,
                "attackers": target_attackers,
            }
        )

    return {
        "targets": plan_targets,
        "captain_calls": captain_calls,
    }


def render_war_plan_html(plan_data):
    targets = plan_data.get("targets", [])
    captain_calls = plan_data.get("captain_calls", [])

    target_cards = []
    for t in targets:
        attackers_html = "".join(
            f'<div class="plan-attacker"><span class="plan-medal">{a["medal"]}</span> <span>{a["text"]}</span></div>'
            for a in t["attackers"]
        )

        target_cards.append(
            f"""
        <div class="plan-card">
            <div class="plan-card-title">Target #{t["target"]}</div>
            {attackers_html}
        </div>
        """
        )

    calls_html = (
        "".join(f"<li>{call}</li>" for call in captain_calls)
        or "<li>No captain calls</li>"
    )

    if not target_cards:
        target_cards_html = '<div class="plan-empty">No suggestions available.</div>'
    else:
        target_cards_html = "".join(target_cards)

    return f"""
    <div class="war-plan-section">
        <div class="war-plan-title">War Plan</div>
        <div class="war-plan-layout">
            <div class="war-plan-grid">
                {target_cards_html}
            </div>
            <div class="captain-panel">
                <div class="captain-title">Captain Calls</div>
                <ul class="captain-list">
                    {calls_html}
                </ul>
            </div>
        </div>
    </div>
    """


def inject_large_war_plan_css(html: str, target_count: int) -> str:
    """Let the current-war render fit 15v15/20v20 war plans without clipping."""
    if target_count <= 10:
        return html

    compact_css = """
    <style id="large-war-plan-overrides">
      body, html { height: auto !important; min-height: 100% !important; overflow: visible !important; }
      .container, .card, .war-card, .battle-card, .dashboard-card, .wrap, .wrapper {
        height: auto !important; max-height: none !important; overflow: visible !important;
      }
      .war-plan-section { height: auto !important; max-height: none !important; overflow: visible !important; margin-top: 14px !important; }
      .war-plan-layout { display: block !important; height: auto !important; max-height: none !important; overflow: visible !important; }
      .war-plan-grid {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        gap: 8px !important;
        width: 100% !important;
        height: auto !important; max-height: none !important; overflow: visible !important;
      }
      .plan-card { min-height: 54px !important; padding: 8px 10px !important; box-sizing: border-box !important; }
      .plan-card-title { font-size: 12px !important; line-height: 1.15 !important; margin-bottom: 5px !important; }
      .plan-attacker { font-size: 10.5px !important; line-height: 1.2 !important; white-space: normal !important; overflow-wrap: anywhere !important; }
      .captain-panel { width: auto !important; margin-top: 10px !important; padding: 10px 12px !important; height: auto !important; max-height: none !important; overflow: visible !important; }
      .captain-title { font-size: 12px !important; margin-bottom: 4px !important; }
      .captain-list { font-size: 10.5px !important; line-height: 1.25 !important; margin: 0 !important; }
    </style>
    """

    if "</head>" in html:
        return html.replace("</head>", compact_css + "\n</head>", 1)

    return compact_css + html