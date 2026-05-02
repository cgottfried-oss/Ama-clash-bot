from __future__ import annotations

from typing import Any

from advisor.constants import DEFAULT_ROLE
from advisor.upgrade_cards import base_upgrade_card_html, metric_row, status_note, summary_card


def _build_compact_accountcompletion_card_html(
    self,
    user: dict[str, Any],
    requested_mode: str | None = None,
    builder_idle: bool | None = None,
    lab_idle: bool | None = None,
) -> str:
    progress = self.build_progress_snapshot(user)
    account = self.build_account_completion_snapshot(user)
    pool = self.build_recommendation_pool_snapshot(
        user,
        requested_mode=requested_mode,
        builder_idle=builder_idle,
        lab_idle=lab_idle,
    )
    velocity = self.get_progress_velocity(user)

    player_name = user.get("player_name") or "Unknown"
    th = user.get("town_hall") or "?"
    role = str(user.get("role", DEFAULT_ROLE)).title()
    eta_value, eta_sub = self._format_days_eta_text(velocity.get("days_to_target"), empty="Need history")

    groups = dict(account.get("group_breakdown") or {})

    def totals_for(*keys: str) -> tuple[int, int]:
        complete = 0
        total = 0
        for key in keys:
            row = groups.get(key) or {}
            complete += int(row.get("complete", 0) or 0)
            total += int(row.get("supported", 0) or 0)
        return complete, total

    supported_complete = int(account.get("supported_complete", 0) or 0)
    supported_slots = max(1, int(account.get("supported_slots", 0) or 0))
    supported_known = int(account.get("supported_known", 0) or 0)
    percent_complete = int(account.get("percent_complete", 0) or 0)
    coverage_percent = int(account.get("coverage_percent", 0) or 0)

    heroes_done, heroes_total = totals_for("heroes")
    lab_done, lab_total = totals_for("troops", "spells", "siege_machines")
    pets_done, pets_total = totals_for("pets")
    structures_done, structures_total = totals_for(
        "offense_buildings",
        "core_buildings",
        "defenses",
        "traps",
        "resource_buildings",
        "army_buildings",
    )
    walls_done, walls_total = totals_for("walls")

    pool_cats = dict(pool.get("by_category") or [])
    hero_pool = int(pool_cats.get("heroes", 0) or 0)
    lab_pool = (
        int(pool_cats.get("troops", 0) or 0)
        + int(pool_cats.get("spells", 0) or 0)
        + int(pool_cats.get("siege_machines", 0) or 0)
    )
    building_pool = sum(
        int(pool_cats.get(k, 0) or 0)
        for k in ("defenses", "core_buildings", "offense_buildings", "resource_buildings", "army_buildings", "walls", "traps")
    )
    other_pool = max(0, int(pool.get("pool_size", 0) or 0) - hero_pool - lab_pool - building_pool)

    unsupported = int(account.get("unsupported_slots", 0) or 0)
    footer_note = f"Outside Current Model: {unsupported} TH slot(s)" if unsupported else "All visible TH slots are inside the current model"

    summary_html = "".join([
        summary_card("Account", f"{player_name} · TH{th}", "🏰"),
        summary_card("Role", role, "⚔️"),
        summary_card("Overall", f"{percent_complete}%", "📈"),
        summary_card("Coverage", f"{coverage_percent}%", "🧭"),
        summary_card("Advisor", f"{int(progress.get('percent', 0) or 0)}%", "🎯"),
        summary_card("ETA", f"{eta_value} {eta_sub}".strip(), "⏱️"),
        summary_card("Top Picks", str(int(pool.get("top_size", 0) or 0)), "🔥"),
        summary_card("Available", str(int(pool.get("pool_size", 0) or 0)), "📌"),
    ])

    metrics_html = "".join([
        metric_row("Overall Completion", supported_complete, supported_slots, "📊"),
        metric_row("Data Coverage", supported_known, supported_slots, "🧭"),
    ])
    if heroes_total:
        metrics_html += metric_row("Heroes", heroes_done, heroes_total, "👑")
    if lab_total:
        metrics_html += metric_row("Lab", lab_done, lab_total, "🧪")
    if pets_total:
        metrics_html += metric_row("Pets", pets_done, pets_total, "🐾")
    if structures_total:
        metrics_html += metric_row("Structures", structures_done, structures_total, "🏗️")
    if walls_total:
        metrics_html += metric_row("Walls", walls_done, walls_total, "🧱")

    advisor_done = int(progress.get("done", 0) or 0)
    advisor_total = max(1, int(progress.get("tracked", 0) or 0))
    recommendation_note = (
        f"Top picks: {int(pool.get('top_size', 0) or 0)} · "
        f"Eligible upgrades: {int(pool.get('pool_size', 0) or 0)} · "
        f"Hero {hero_pool} · Lab {lab_pool} · Buildings {building_pool} · Misc {other_pool}"
    )

    board_html = (
        '<div class="section-title">Completion Snapshot</div>'
        + metrics_html
        + '<div class="section-title">Advisor Progress</div>'
        + metric_row("Advisor Targets", advisor_done, advisor_total, "🎯")
        + '<div class="section-title">Available Recommendations</div>'
        + f'<div class="note">{self._html_escape(recommendation_note)}</div>'
        + status_note(footer_note, "ⓘ")
        + status_note(self._lowest_account_category_note(account), "📉")
    )

    return base_upgrade_card_html(
        "Account Completion",
        f"Completion snapshot for {player_name}",
        summary_html,
        board_html,
    )
