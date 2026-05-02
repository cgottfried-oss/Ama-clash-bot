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


def _text(advisor: Any, value: Any) -> str:
    return advisor._html_escape(str(value or ""))


def _rec_title(rec: dict[str, Any]) -> str:
    return str(rec.get("label") or rec.get("name") or rec.get("item") or rec.get("item_key") or "Upgrade")


def _rec_key(rec: dict[str, Any]) -> str:
    return str(
        rec.get("item_key")
        or rec.get("key")
        or rec.get("item")
        or rec.get("name")
        or rec.get("label")
        or "auto"
    )


def _rec_icon_html(advisor: Any, rec: dict[str, Any], css_class: str = "unit-icon") -> str:
    return advisor._render_icon_html(
        icon_key=_rec_key(rec),
        label=_rec_title(rec),
        fallback="📌",
        kind="item",
        css_class=css_class,
    )


def _rec_level_text(rec: dict[str, Any]) -> str:
    current = rec.get("current", rec.get("level", rec.get("current_level", "?")))
    target = rec.get("target", rec.get("next", rec.get("target_level", "?")))
    cap = rec.get("cap", rec.get("max", rec.get("max_level", target)))
    return f"Lvl {current} → {target} of {cap}"


def _rec_score(rec: dict[str, Any]) -> str:
    raw = rec.get("score", rec.get("value", rec.get("priority_score", "")))
    try:
        return f"{float(raw):.1f}"
    except (TypeError, ValueError):
        return str(raw or "—")


def _simple_pick_rows(advisor: Any, recs: list[dict[str, Any]]) -> str:
    if not recs:
        return '<div class="empty">Nothing urgent right now.</div>'

    rows: list[str] = []
    for idx, rec in enumerate(recs[:5], start=1):
        title = _text(advisor, _rec_title(rec))
        level = _text(advisor, _rec_level_text(rec))
        reason = _text(advisor, rec.get("reason") or rec.get("note") or "Recommended next upgrade.")
        score = _text(advisor, _rec_score(rec))
        pct = max(5, min(100, _safe_int(rec.get("percent", rec.get("progress", 72)), 72)))
        icon_html = _rec_icon_html(advisor, rec, "unit-icon")
        rows.append(
            '<div class="pick-row">'
            f'<div class="pick-rank">#{idx}</div>'
            f'<div class="pick-icon">{icon_html}</div>'
            '<div class="pick-main">'
            f'<div class="pick-title">{title}</div>'
            f'<div class="pick-sub">{level} · Score {score}</div>'
            f'<div class="pick-reason">{reason}</div>'
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div>'
            '</div>'
            '</div>'
        )
    return "".join(rows)


def _simple_spotlights(advisor: Any, recs: list[dict[str, Any]]) -> str:
    if not recs:
        return '<div class="note">No upgrade spotlights available yet.</div>'
    labels = ["🔥 Best Upgrade", "⚡ Quick Win", "📈 Big Progress"]
    cards: list[str] = []
    for label, rec in zip(labels, recs[:3]):
        icon_html = _rec_icon_html(advisor, rec, "unit-icon")
        cards.append(
            '<div class="spotlight-card">'
            f'<div class="spotlight-head">{icon_html}<div class="tile-title">{_text(advisor, label)}</div></div>'
            f'<div class="tile-value">{_text(advisor, _rec_title(rec))}</div>'
            f'<div class="tile-sub">{_text(advisor, _rec_level_text(rec))} · Score {_text(advisor, _rec_score(rec))}</div>'
            '</div>'
        )
    return '<div class="spotlight-grid">' + "".join(cards) + '</div>'


def _simple_lane_snapshot(advisor: Any, recs: list[dict[str, Any]]) -> str:
    lanes = {
        "Hero Lane": [],
        "Lab Lane": [],
        "Builder Lane": [],
    }
    for rec in recs[:8]:
        lane = str(rec.get("lane") or rec.get("category") or "").lower()
        title = _rec_title(rec)
        if "hero" in lane:
            lanes["Hero Lane"].append(title)
        elif "spell" in lane or "troop" in lane or "lab" in lane or "siege" in lane:
            lanes["Lab Lane"].append(title)
        else:
            lanes["Builder Lane"].append(title)

    rows = []
    for label, items in lanes.items():
        value = ", ".join(items[:2]) if items else "Quiet"
        rows.append(f'<div class="note"><strong>{_text(advisor, label)}</strong><br>{_text(advisor, value)}</div>')
    return "".join(rows)


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
        summary_card("Pressure", f"{top_lane} · {int(pressure_lane[1])}%", LANE_EMOJIS.get(pressure_lane[0], "📌")),
        summary_card("Mode", mode_label, "🧠"),
        summary_card("Builder", builder_label, "🛠️"),
        summary_card("War", war_state_label, "🪖"),
        summary_card("Resource", f"{hottest_resource.replace('_', ' ').title()} {hottest_value}%", "💰"),
        summary_card("Lab", lab_label, "🧪"),
        summary_card("Coverage", f"{tracked_count}/{tracking_total}", "🧭"),
        summary_card("Coins", str(int(economy.get("coins", 0))), "🪙"),
        summary_card("Efficiency", str(int(economy.get("efficiency_score", 0))), "⭐"),
        summary_card("Reward", next_reward, "🏆"),
    ])

    board_html = (
        '<div class="section-title">Upgrade Spotlights</div>'
        + _simple_spotlights(advisor, recs)
        + '<div class="section-title">Top Upgrade Picks</div>'
        + _simple_pick_rows(advisor, recs)
        + '<div class="section-title">Lane Breakdown</div>'
        + _simple_lane_snapshot(advisor, recs)
        + '<div class="section-title">Remaining Goals</div>'
        + f'<div class="note">{advisor._html_escape(advisor.build_remaining_goals_block(user, limit=5).replace("**", ""))}</div>'
        + '<div class="section-title">Advisor Tracking Gaps</div>'
        + f'<div class="note">{advisor._html_escape(advisor.build_untracked_goals_block(user, limit=3).replace("**", ""))}</div>'
        + f'<div class="note">Focus: {advisor._html_escape(advisor.build_milestone_hint(user).replace("**", ""))}</div>'
    )

    html = base_upgrade_card_html(
        "Upgrade Advisor",
        f"Advisor recommendations for {player_name}",
        summary_html,
        board_html,
    )
    print(f"[NEXTUPGRADE_NATIVE_HTML] html_len={len(html)} recs={len(recs)} pool={len(pool)}", flush=True)
    return html
