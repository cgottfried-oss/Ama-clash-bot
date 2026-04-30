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

        rows: list[tuple[str, int, int, Any, str, str, str]] = [
            (
                "Overall Completion",
                int(account.get("supported_complete", 0) or 0),
                max(1, int(account.get("supported_slots", 0) or 0)),
                "overall_completion",
                "item",
                "📊",
                "#4f8df7",
            ),
            (
                "Data Coverage",
                int(account.get("supported_known", 0) or 0),
                max(1, int(account.get("supported_slots", 0) or 0)),
                "tracking_coverage",
                "item",
                "🧭",
                "#7ccf45",
            ),
        ]

        heroes_done, heroes_total = totals_for("heroes")
        if heroes_total:
            rows.append(("Heroes", heroes_done, heroes_total, "hero", "ui", "👑", "#8b6de9"))

        lab_done, lab_total = totals_for("troops", "spells", "siege_machines")
        if lab_total:
            rows.append(("Lab", lab_done, lab_total, "lab", "ui", "🧪", "#33c6cc"))

        pets_done, pets_total = totals_for("pets")
        if pets_total:
            rows.append(("Pets", pets_done, pets_total, "pet", "ui", "🐾", "#ff9b3d"))

        structures_done, structures_total = totals_for(
            "offense_buildings",
            "core_buildings",
            "defenses",
            "traps",
            "resource_buildings",
            "army_buildings",
        )
        if structures_total:
            rows.append(("Structures", structures_done, structures_total, "builder", "ui", "🏗️", "#ff6464"))

        walls_done, walls_total = totals_for("walls")
        if walls_total:
            rows.append(("Walls", walls_done, walls_total, "wall", "item", "🧱", "#f5c542"))

        def ratio_pct(done: int, total: int) -> tuple[int, str]:
            total = max(1, int(total or 1))
            done = max(0, min(int(done or 0), total))
            pct = int(round((done / total) * 100))
            return pct, f"{done} / {total}"

        metric_rows: list[str] = []
        for label, done, total, icon_key, icon_kind, fallback_icon, color in rows[:7]:
            pct, ratio = ratio_pct(done, total)
            icon_html = self._render_icon_html(
                icon_key=icon_key,
                label=label,
                fallback=fallback_icon,
                kind=icon_kind,
                css_class="ac-row-icon-img",
            )
            metric_rows.append(
                f'<div class="ac-row">'
                f'<div class="ac-row-left">{icon_html}<span class="ac-row-label">{self._html_escape(label)}</span></div>'
                f'<div class="ac-row-bar-wrap"><div class="ac-row-bar"><div class="ac-row-fill" style="width:{pct}%; background:{color};"></div></div></div>'
                f'<div class="ac-row-right"><div class="ac-row-ratio">{self._html_escape(ratio)}</div><div class="ac-row-pct" style="color:{color};">{pct}%</div></div>'
                f'</div>'
            )
        metrics_html = ''.join(metric_rows)

        advisor_pct, advisor_ratio = ratio_pct(int(progress.get("done", 0) or 0), max(1, int(progress.get("tracked", 0) or 0)))
        advisor_icon = self._render_icon_html(icon_key="auto", label="Advisor Targets", fallback="🎯", kind="ui", css_class="ac-row-icon-img")
        advisor_row_html = (
            '<div class="ac-row">'
            f'<div class="ac-row-left">{advisor_icon}<span class="ac-row-label">Advisor Targets</span></div>'
            f'<div class="ac-row-bar-wrap"><div class="ac-row-bar"><div class="ac-row-fill" style="width:{advisor_pct}%; background:#4f8df7;"></div></div></div>'
            f'<div class="ac-row-right"><div class="ac-row-ratio">{self._html_escape(advisor_ratio)}</div>'
            f'<div class="ac-row-pct" style="color:#4f8df7;">{advisor_pct}%</div></div>'
            '</div>'
        )

        pool_cats = dict(pool.get("by_category") or [])
        hero_pool = int(pool_cats.get("heroes", 0) or 0)
        lab_pool = int(pool_cats.get("troops", 0) or 0) + int(pool_cats.get("spells", 0) or 0) + int(pool_cats.get("siege_machines", 0) or 0)
        building_pool = sum(int(pool_cats.get(k, 0) or 0) for k in ("defenses", "core_buildings", "offense_buildings", "resource_buildings", "army_buildings", "walls", "traps"))
        other_pool = max(0, int(pool.get("pool_size", 0) or 0) - hero_pool - lab_pool - building_pool)

        unsupported = int(account.get("unsupported_slots", 0) or 0)
        footer_note = f"Outside Current Model: {unsupported} TH slot(s)" if unsupported else "All visible TH slots are inside the current model"

        def info_tile(title: str, value: str, sub: str = "", accent: str = "", icon_key: Any = None, fallback: str = "📌", kind: str = "ui") -> str:
            icon_html = self._render_icon_html(
                icon_key=icon_key or title,
                label=title,
                fallback=fallback,
                kind=kind,
                css_class="tile-icon",
            )
            accent_attr = f' style="color:{accent};"' if accent else ''
            sub_html = f'<div class="tile-sub">{self._html_escape(sub)}</div>' if sub else ''
            return (
                '<div class="info-tile">'
                f'<div class="tile-head">{icon_html}<div class="tile-title">{self._html_escape(title)}</div></div>'
                f'<div class="tile-value"{accent_attr}>{self._html_escape(value)}</div>'
                f'{sub_html}'
                '</div>'
            )

        overall_ratio = f"{int(account.get('supported_complete', 0) or 0)} / {max(1, int(account.get('supported_slots', 0) or 0))}"
        coverage_ratio = f"{int(account.get('supported_known', 0) or 0)} / {max(1, int(account.get('supported_slots', 0) or 0))}"
        subtitle = self._html_escape(f"Completion snapshot for {player_name}")
        th_icon_html = self._render_icon_html(
            icon_key=f"th_{th}",
            label=f"Town Hall {th}",
            fallback="🏰",
            kind="item",
            css_class="th-icon",
        )

        def pool_stat(label: str, value: int, icon_key: Any, fallback: str, kind: str = "ui") -> str:
            icon_html = self._render_icon_html(icon_key=icon_key, label=label, fallback=fallback, kind=kind, css_class="pool-stat-icon")
            return f'<div class="pool-stat">{icon_html}<span class="pool-stat-label">{self._html_escape(label)}</span><strong>{int(value)}</strong></div>'

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin: 0;
    background: #edf1f6;
    font-family: Arial, Helvetica, sans-serif;
    color: #111827;
}}
.th-icon,
.tile-icon,
.ac-row-icon-img,
.pool-stat-icon {{
    object-fit: contain;
    display: inline-block;
    flex-shrink: 0;
}}
.emoji-fallback {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
}}
.card-shell {{
    width: 920px;
    box-sizing: border-box;
    padding: 24px;
}}
.card {{
    background: #ffffff;
    border: 1px solid #dfe5ee;
    border-radius: 22px;
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
    padding: 28px;
    box-sizing: border-box;
}}
.header {{
    margin-bottom: 20px;
}}
.title {{
    font-size: 38px;
    font-weight: 800;
    line-height: 1.05;
    margin: 0 0 6px;
    letter-spacing: -0.02em;
}}
.subtitle {{
    font-size: 18px;
    color: #667085;
    margin: 0;
}}
.hero-grid {{
    display: grid;
    grid-template-columns: 210px 1fr;
    gap: 18px;
    align-items: stretch;
    margin-bottom: 24px;
}}
.th-panel {{
    background: linear-gradient(180deg, #f9fbff 0%, #eef4ff 100%);
    border: 1px solid #dbe6f7;
    border-radius: 20px;
    min-height: 228px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 18px 16px;
    box-sizing: border-box;
}}
.th-icon {{
    width: 146px;
    height: 146px;
    margin-bottom: 14px;
}}
.th-pill {{
    display: inline-block;
    background: #1f4f93;
    color: #ffffff;
    border-radius: 14px;
    padding: 10px 18px;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
}}
.info-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
}}
.info-tile {{
    background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
    border: 1px solid #e3e8f0;
    border-radius: 18px;
    padding: 16px 18px;
    min-height: 104px;
    box-sizing: border-box;
}}
.tile-head {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}}
.tile-icon {{
    width: 22px;
    height: 22px;
}}
.tile-title {{
    font-size: 15px;
    color: #667085;
    font-weight: 700;
}}
.tile-value {{
    font-size: 24px;
    line-height: 1.12;
    color: #111827;
    font-weight: 800;
    letter-spacing: -0.02em;
}}
.tile-sub {{
    margin-top: 6px;
    font-size: 15px;
    color: #667085;
    line-height: 1.35;
}}
.section {{
    border-top: 1px solid #e7edf4;
    padding-top: 18px;
    margin-top: 18px;
}}
.section-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 20px;
    font-weight: 800;
    margin: 0 0 14px;
    color: #111827;
}}
.ac-row {{
    display: grid;
    grid-template-columns: minmax(0, 240px) minmax(0, 1fr) 132px;
    gap: 14px;
    align-items: center;
    padding: 14px 16px;
    border: 1px solid #e7ebf1;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
    margin-bottom: 10px;
}}
.ac-row-left {{
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}}
.ac-row-icon-img {{
    width: 28px;
    height: 28px;
    border-radius: 8px;
}}
.ac-row-label {{
    font-size: 18px;
    font-weight: 800;
    color: #1f2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.ac-row-bar-wrap {{
    width: 100%;
}}
.ac-row-bar {{
    width: 100%;
    height: 14px;
    background: #e7ebf1;
    border-radius: 999px;
    overflow: hidden;
}}
.ac-row-fill {{
    height: 100%;
    border-radius: 999px;
}}
.ac-row-right {{
    text-align: right;
}}
.ac-row-ratio {{
    font-size: 18px;
    color: #344054;
    font-weight: 800;
    line-height: 1.15;
}}
.ac-row-pct {{
    font-size: 18px;
    font-weight: 800;
    margin-top: 2px;
}}
.pool-box {{
    border: 1px solid #e3e8f0;
    border-radius: 18px;
    background: linear-gradient(180deg, #fbfcfe 0%, #f7f9fc 100%);
    padding: 18px 20px;
}}
.pool-head {{
    font-size: 18px;
    font-weight: 800;
    text-align: center;
    margin-bottom: 4px;
}}
.pool-sub {{
    font-size: 15px;
    color: #667085;
    text-align: center;
    margin-bottom: 14px;
}}
.pool-breakdown {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
}}
.pool-stat {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 12px;
    border: 1px solid #e3e8f0;
    border-radius: 14px;
    background: #ffffff;
    font-size: 15px;
    color: #344054;
}}
.pool-stat-icon {{
    width: 22px;
    height: 22px;
    border-radius: 6px;
}}
.pool-stat-label {{
    font-weight: 700;
}}
.footer-note {{
    text-align: center;
    color: #667085;
    font-size: 15px;
    margin-top: 14px;
}}
</style>
</head>
<body>
<div class="card-shell">
  <div class="card">
    <div class="header">
      <div class="title">Account Completion</div>
      <div class="subtitle">{subtitle}</div>
    </div>

    <div class="hero-grid">
      <div class="th-panel">
        {th_icon_html}
        <div class="th-pill">TH{self._html_escape(str(th))}</div>
      </div>
      <div class="info-grid">
        {info_tile('Account', str(player_name), f'TH{th}', icon_key=f'th_{th}', fallback='🏰', kind='item')}
        {info_tile('Role', role, icon_key='auto', fallback='⚔️')}
        {info_tile('Overall Completion', f"{account.get('percent_complete', 0)}%", overall_ratio, '#4f8df7', icon_key='overall_completion', fallback='📈', kind='item')}
        {info_tile('Tracking Coverage', f"{account.get('coverage_percent', 0)}%", coverage_ratio, '#7ccf45', icon_key='tracking_coverage', fallback='🧭', kind='item')}
        {info_tile('ETA to Advisor Completion', eta_value, eta_sub, '#d69e2e', icon_key='soon', fallback='⏱️')}
        {info_tile('Top Picks', str(pool.get('top_size', 0) or 0), f"from {pool.get('pool_size', 0) or 0} available", icon_key='auto', fallback='🔥')}
      </div>
    </div>

    <div class="section">
      <div class="section-title">📊 Completion Snapshot</div>
      {metrics_html}
    </div>

    <div class="section">
      <div class="section-title">🎯 Advisor Progress</div>
      {advisor_row_html}
    </div>

    <div class="section">
      <div class="pool-box">
        <div class="pool-head">🔥 Available Recommendations</div>
        <div class="pool-sub">Top picks: {int(pool.get('top_size', 0) or 0)} &nbsp; • &nbsp; Eligible upgrades: {int(pool.get('pool_size', 0) or 0)}</div>
        <div class="pool-breakdown">
          {pool_stat('Hero', hero_pool, 'hero', '👑')}
          {pool_stat('Lab', lab_pool, 'lab', '🧪')}
          {pool_stat('Buildings', building_pool, 'builder', '🏗️')}
          {pool_stat('Misc', other_pool, 'auto', '📌')}
        </div>
      </div>
      <div class="footer-note">ⓘ {self._html_escape(footer_note)}</div>
      <div class="footer-note">📉 {self._html_escape(self._lowest_account_category_note(account))}</div>
    </div>
  </div>
</div>
</body>
</html>
"""