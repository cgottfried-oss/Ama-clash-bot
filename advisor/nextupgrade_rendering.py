from __future__ import annotations

from typing import Any

from advisor.constants import DEFAULT_ROLE, LANE_EMOJIS, MODE_EMOJIS
from advisor.upgrade_cards import base_upgrade_card_html, summary_card


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def build_nextupgrade_card_html(
    advisor: Any,
    user: dict[str, Any],
    recs: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    timing_context: dict[str, Any] | None = None,
) -> str:
    progress = advisor.build_progress_snapshot(user)
    tracking = advisor.build_tracking_snapshot(user)
    tracked_count = _safe_int(tracking.get("tracked", tracking.get("known", tracking.get("complete", 0))))
    tracking_total = _safe_int(tracking.get("total", tracking.get("supported", tracking.get("slots", 0))))

    role = str(user.get("role", DEFAULT_ROLE)).title()
    player_name = user.get("player_name") or "Unknown"
    th = user.get("town_hall") or "?"

    state = advisor.get_milestone_state(user)
    war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"

    lane_snapshot = advisor.build_lane_snapshot(user)
    pressure_lane = min(
        ((lane, float(data.get("percent", 100.0))) for lane, data in lane_snapshot.items()),
        key=lambda item: item[1],
    ) if lane_snapshot else ("none", 100.0)
    top_lane = pressure_lane[0].title() if recs else "None"

    next_reward = advisor.build_next_reward_block(user).split("\n")[0].replace("**", "")
    timing_context = timing_context or advisor.get_timing_context(user)
    mode = str(timing_context.get("mode", "war"))
    emoji = MODE_EMOJIS.get(mode, "🧠")
    mode_label = f"{emoji} {mode.title()}"
    builder_label = "Idle" if timing_context.get("builder_idle") else "Busy/Unknown"
    lab_label = "Idle" if timing_context.get("lab_idle") else "Busy/Unknown"

    war_state = dict(timing_context.get("war_state") or {})
    resource_pressure = dict(timing_context.get("resource_pressure") or {})
    war_state_label = "CWL" if war_state.get("cwl") else ("In War" if war_state.get("in_war") else ("Prep" if war_state.get("war_prepping") else "None"))
    hottest_resource = max(resource_pressure.items(), key=lambda kv: kv[1])[0] if resource_pressure else "none"
    hottest_value = int(round(float(resource_pressure.get(hottest_resource, 0.0)) * 100)) if resource_pressure else 0

    economy = advisor._get_economy(user)
    summary_html = "".join([
        summary_card("Account", f"{player_name} · TH{th}", "🏰"),
        summary_card("Role", role, "⚔️"),
        summary_card("War Ready", war_ready, "✅"),
        summary_card("Progress", f"{progress['percent']}%", "📈"),
        summary_card("Goals", f"{progress['done']}/{progress['tracked']}", "🎯"),
        summary_card("Pressure Lane", f"{top_lane} · {int(pressure_lane[1])}%", LANE_EMOJIS.get(pressure_lane[0], "📌")),
        summary_card("Mode", mode_label, "🧠"),
        summary_card("Builder", builder_label, "🛠️"),
        summary_card("War State", war_state_label, "🪖"),
        summary_card("Resource", f"{hottest_resource.replace('_', ' ').title()} {hottest_value}%", "💰"),
        summary_card("Lab", lab_label, "🧪"),
        summary_card("Coverage", f"{tracked_count}/{tracking_total}", "🧭"),
        summary_card("Coins", str(int(economy.get("coins", 0))), "🪙"),
        summary_card("Efficiency", str(int(economy.get("efficiency_score", 0))), "⭐"),
        summary_card("Reward", next_reward, "🏆"),
    ])

    if recs:
        rows_html = "".join(advisor._render_upgrade_pick_row_html(rec, idx) for idx, rec in enumerate(recs[:5], start=1))
    else:
        rows_html = '<div class="empty">Nothing urgent right now.</div>'

    board_html = (
        '<div class="section-title">Upgrade Spotlights</div>'
        + advisor._render_spotlight_tiles_html(recs, pool)
        + '<div class="section-title">Top Upgrade Picks</div>'
        + rows_html
        + '<div class="section-title">Lane Breakdown</div>'
        + advisor._render_lane_tiles_html(recs)
        + '<div class="section-title">Remaining Goals</div>'
        + f'<div class="note">{advisor._html_escape(advisor.build_remaining_goals_block(user, limit=5).replace("**", ""))}</div>'
        + '<div class="section-title">Advisor Tracking Gaps</div>'
        + f'<div class="note">{advisor._html_escape(advisor.build_untracked_goals_block(user, limit=3).replace("**", ""))}</div>'
        + f'<div class="note">Focus: {advisor._html_escape(advisor.build_milestone_hint(user).replace("**", ""))}</div>'
    )

    return base_upgrade_card_html(
        "Upgrade Advisor",
        f"Advisor recommendations for {player_name}",
        summary_html,
        board_html,
    )
