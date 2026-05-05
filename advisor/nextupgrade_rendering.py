from __future__ import annotations

from typing import Any

from advisor.constants import DEFAULT_ROLE, LANE_EMOJIS, MODE_EMOJIS
from advisor.upgrade_cards import base_upgrade_card_html, summary_card, townhall_summary_card


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


def _rec_icon_html(advisor: Any, rec: dict[str, Any], css_class: str = "nu-icon") -> str:
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


def _rec_pct(rec: dict[str, Any]) -> int:
    current = _safe_int(rec.get("current", rec.get("level", rec.get("current_level", 0))))
    cap = _safe_int(rec.get("cap", rec.get("max", rec.get("max_level", rec.get("target", 1)))), 1)
    if cap <= 0:
        return 72
    return max(5, min(100, int(round((current / cap) * 100))))


def _layout_css() -> str:
    return """
<style>
.nu-spot-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.nu-spot-card, .nu-pick-row {
  background: linear-gradient(180deg, rgba(24, 34, 66, .96), rgba(18, 27, 54, .96));
  border: 1px solid rgba(148, 163, 220, .24);
  border-radius: 16px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 8px 18px rgba(0,0,0,.20);
}
.nu-spot-card { padding: 14px; min-height: 136px; }
.nu-spot-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.nu-spot-icon, .nu-icon { width: 58px !important; height: 58px !important; max-width: 58px !important; max-height: 58px !important; object-fit: contain !important; display: block; border-radius: 12px; }
.nu-spot-label { color: rgba(255,255,255,.74); font-size: 14px; font-weight: 800; }
.nu-spot-title { color: #fff; font-size: 20px; font-weight: 900; line-height: 1.1; text-shadow: 0 2px 2px rgba(0,0,0,.35); }
.nu-spot-sub { margin-top: 6px; color: rgba(255,255,255,.74); font-size: 13px; line-height: 1.25; }
.nu-pick-row { display: grid; grid-template-columns: 58px 72px 1fr; gap: 12px; align-items: center; padding: 12px 14px; margin-bottom: 10px; }
.nu-rank { color: #fff; font-size: 22px; font-weight: 900; text-align: center; text-shadow: 0 2px 2px rgba(0,0,0,.35); }
.nu-icon-wrap { display: flex; justify-content: center; align-items: center; width: 72px; height: 72px; }
.nu-main { min-width: 0; }
.nu-title { color: #fff; font-size: 21px; font-weight: 900; line-height: 1.05; text-shadow: 0 2px 2px rgba(0,0,0,.35); }
.nu-sub { color: rgba(255,255,255,.78); font-size: 14px; margin-top: 4px; }
.nu-reason { color: rgba(255,255,255,.62); font-size: 13px; margin-top: 4px; }
.nu-track { width: 100%; height: 10px; border-radius: 999px; background: rgba(6, 12, 32, .78); margin-top: 8px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,.40); }
.nu-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #58d8ff, #9a86ff, #ffe66d); }
</style>
"""


def _simple_pick_rows(advisor: Any, recs: list[dict[str, Any]]) -> str:
    if not recs:
        return '<div class="note">Nothing urgent right now.</div>'

    rows: list[str] = []
    for idx, rec in enumerate(recs[:5], start=1):
        title = _text(advisor, _rec_title(rec))
        level = _text(advisor, _rec_level_text(rec))
        reason = _text(advisor, rec.get("reason") or rec.get("note") or "Recommended next upgrade.")
        score = _text(advisor, _rec_score(rec))
        pct = _rec_pct(rec)
        icon_html = _rec_icon_html(advisor, rec, "nu-icon")
        rows.append(
            '<div class="nu-pick-row">'
            f'<div class="nu-rank">#{idx}</div>'
            f'<div class="nu-icon-wrap">{icon_html}</div>'
            '<div class="nu-main">'
            f'<div class="nu-title">{title}</div>'
            f'<div class="nu-sub">{level} · Score {score}</div>'
            f'<div class="nu-reason">{reason}</div>'
            f'<div class="nu-track"><div class="nu-fill" style="width:{pct}%"></div></div>'
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
        icon_html = _rec_icon_html(advisor, rec, "nu-spot-icon")
        cards.append(
            '<div class="nu-spot-card">'
            f'<div class="nu-spot-head">{icon_html}<div class="nu-spot-label">{_text(advisor, label)}</div></div>'
            f'<div class="nu-spot-title">{_text(advisor, _rec_title(rec))}</div>'
            f'<div class="nu-spot-sub">{_text(advisor, _rec_level_text(rec))} · Score {_text(advisor, _rec_score(rec))}</div>'
            '</div>'
        )
    return '<div class="nu-spot-grid">' + "".join(cards) + '</div>'


def _simple_lane_snapshot(advisor: Any, recs: list[dict[str, Any]]) -> str:
    lanes = {"Hero Lane": [], "Lab Lane": [], "Builder Lane": []}
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

    role = str(user.get("role", DEFAULT_ROLE)).title()
    player_name = user.get("player_name") or "Unknown"
    th = user.get("town_hall") or "?"

    state = advisor.get_milestone_state(user)
    war_ready = "Yes" if state["achieved"].get("war_ready") else "Not yet"

    lane_snapshot = advisor.build_lane_snapshot(user)
    pressure_lane = min(((lane, float(data.get("percent", 100.0))) for lane, data in lane_snapshot.items()), key=lambda item: item[1]) if lane_snapshot else ("none", 100.0)
    top_lane = pressure_lane[0].title() if recs else "None"

    timing_context = timing_context or advisor.get_timing_context(user)
    mode = str(timing_context.get("mode", "war"))
    emoji = MODE_EMOJIS.get(mode, "🧠")
    mode_label = f"{emoji} {mode.title()}"

    summary_html = "".join([
        townhall_summary_card(advisor, player_name, th),
        summary_card("Role", role, "⚔️"),
        summary_card("War Ready", war_ready, "✅"),
        summary_card("Progress", f"{progress['percent']}%", "📈"),
        summary_card("Goals", f"{progress['done']}/{progress['tracked']}", "🎯"),
        summary_card("Pressure", f"{top_lane} · {int(pressure_lane[1])}%", LANE_EMOJIS.get(pressure_lane[0], "📌")),
        summary_card("Mode", mode_label, "🧠"),
        summary_card("Picks", str(len(recs[:5])), "🔥"),
    ])

    board_html = (
        _layout_css()
        + '<div class="section-title">Upgrade Spotlights</div>'
        + _simple_spotlights(advisor, recs)
        + '<div class="section-title">Top Upgrade Picks</div>'
        + _simple_pick_rows(advisor, recs)
        + '<div class="section-title">Lane Breakdown</div>'
        + _simple_lane_snapshot(advisor, recs)
        + f'<div class="note">Focus: {advisor._html_escape(advisor.build_milestone_hint(user).replace("**", ""))}</div>'
    )

    html = base_upgrade_card_html("Upgrade Advisor", f"Advisor recommendations for {player_name}", summary_html, board_html)
    print(f"[NEXTUPGRADE_NATIVE_HTML] html_len={len(html)} recs={len(recs)} pool={len(pool)}", flush=True)
    return html
