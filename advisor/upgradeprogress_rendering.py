from __future__ import annotations

from typing import Any

from advisor.constants import DEFAULT_ROLE
from advisor.upgrade_cards import base_upgrade_card_html, metric_row, summary_card, townhall_summary_card


def build_upgradeprogress_card_html(
    advisor: Any,
    user: dict[str, Any],
    timing_context: dict[str, Any] | None = None,
) -> str:
    progress = advisor.build_progress_snapshot(user)
    player_name = user.get("player_name") or "Unknown"
    th = user.get("town_hall") or "?"
    role = str(user.get("role", DEFAULT_ROLE)).title()

    state = advisor.get_milestone_state(user)
    achieved = state["achieved"]
    groups = state["group_status"]
    last_sync = str(user.get("last_synced_at") or "Never")[:16].replace("T", " ")

    summary_html = "".join([
        townhall_summary_card(advisor, player_name, th),
        summary_card("Role", role, "⚔️"),
        summary_card("Progress", f"{progress['percent']}%", "📈"),
        summary_card("Goals", f"{progress['done']}/{progress['tracked']}", "🎯"),
        summary_card("War Ready", "Yes" if achieved.get("war_ready") else "No", "✅"),
        summary_card("Last Sync", last_sync, "🕒"),
    ])

    breakdown_html = "".join([
        metric_row("Overall", int(progress["done"]), int(progress["tracked"]), "📊"),
        metric_row("Heroes", int(groups["heroes"]["done"]), int(groups["heroes"]["total"]), "👑"),
        metric_row("Offense", int(groups["offense"]["done"]), int(groups["offense"]["total"]), "⚔️"),
        metric_row("Core Buildings", int(groups["builder"]["done"]), int(groups["builder"]["total"]), "🛠️"),
    ])

    board_html = (
        '<div class="section-title">Progress Breakdown</div>'
        + breakdown_html
        + '<div class="section-title">Next Focus</div>'
        + f'<div class="note">{advisor._html_escape(advisor.build_milestone_hint(user).replace("**", ""))}</div>'
    )

    return base_upgrade_card_html(
        "Upgrade Progress",
        f"Progress snapshot for {player_name}",
        summary_html,
        board_html,
    )
