from __future__ import annotations

from typing import Any

from advisor.constants import DEFAULT_ROLE
from advisor.upgrade_cards import (
    base_upgrade_card_html,
    status_note,
    summary_card,
    townhall_summary_card,
)


def build_syncupgrades_card_html(
    advisor: Any,
    user: dict[str, Any],
    *,
    synced_count: int,
    manual_count: int,
    account_snap: dict[str, Any],
    pool_snap: dict[str, Any],
    war_ready: str,
    mode_label: str,
    milestone_celebration: str,
    reward_text: str,
) -> str:
    player_name = user.get("player_name") or "Unknown"
    th = user.get("town_hall") or "?"
    role = str(user.get("role", DEFAULT_ROLE)).title()
    synced_at = user.get("last_synced_at") or user.get("last_upgrade_sync")

    sync_text = "Never"
    if synced_at:
        sync_text = str(synced_at).replace("T", " ")[:16]

    percent_complete = int(account_snap.get("percent_complete", 0) or 0)
    coverage_percent = int(account_snap.get("coverage_percent", 0) or 0)
    pool_size = int(pool_snap.get("pool_size", 0) or 0)

    summary_html = "".join([
        townhall_summary_card(advisor, player_name, th),
        summary_card("Role", role, "⚔️"),
        summary_card("Mode", mode_label, "🧠"),
        summary_card("Completion", f"{percent_complete}%", "📈"),
        summary_card("Coverage", f"{coverage_percent}%", "🧭"),
        summary_card("API Synced", str(synced_count), "🔄"),
        summary_card("Manual", str(manual_count), "📝"),
        summary_card("Recs", str(pool_size), "🔥"),
    ])

    changed_html = ""
    if ("No new milestone" not in str(milestone_celebration)) or ("No active" not in str(reward_text)):
        changed_html = (
            '<div class="section-title">What Changed</div>'
            + '<div class="note">'
            + f'Milestones: <strong>{advisor._html_escape(str(milestone_celebration))}</strong><br>'
            + f'Rewards: <strong>{advisor._html_escape(str(reward_text))}</strong>'
            + '</div>'
        )

    board_html = (
        '<div class="section-title">Sync Receipt</div>'
        + '<div class="note">'
        + f'Last sync: <strong>{advisor._html_escape(sync_text)}</strong><br>'
        + f'API synced: <strong>{int(synced_count)}</strong> hero/lab/pet items<br>'
        + f'Manual tracked entries: <strong>{int(manual_count)}</strong><br>'
        + f'Account completion: <strong>{percent_complete}%</strong> · Coverage: <strong>{coverage_percent}%</strong><br>'
        + f'Recommendations available: <strong>{pool_size}</strong>'
        + '</div>'
        + status_note("Use /currentprogress for progress details or /nextupgrade for recommendations.", "✅")
        + changed_html
    )

    return base_upgrade_card_html(
        "Upgrade Sync Complete",
        f"Sync snapshot for {player_name}",
        summary_html,
        board_html,
    )
