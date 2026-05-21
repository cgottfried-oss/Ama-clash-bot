from __future__ import annotations

import asyncio
from datetime import datetime, timezone


async def create_war_image(
    *,
    war,
    ai_data,
    war_template_path,
    load_war_banner_context,
    get_war_member_performance,
    build_war_plan_data,
    render_war_plan_html,
    inject_large_war_plan_css,
    render_html_to_png_buffer,
):
    def _read_template():
        with open(war_template_path, "r", encoding="utf-8") as f:
            return f.read()

    html = await asyncio.to_thread(_read_template)
    tag_to_discord, shop_data, banner_now = await load_war_banner_context()

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    war_state = war.get("state", "")

    clan_badge = clan.get("badgeUrls", {}).get("large", "")
    opponent_badge = opponent.get("badgeUrls", {}).get("large", "")

    clan_stars = clan.get("stars", 0) or 0
    opponent_stars = opponent.get("stars", 0) or 0

    clan_destruction = float(clan.get("destructionPercentage", 0) or 0)
    opponent_destruction = float(opponent.get("destructionPercentage", 0) or 0)

    clan_attacks = clan.get("attacks", 0) or 0
    opponent_attacks = opponent.get("attacks", 0) or 0

    team_size = war.get("teamSize", 0) or 0
    attacks_per_member = war.get("attacksPerMember", 2) or 2
    max_attacks = team_size * attacks_per_member

    total_stars = clan_stars + opponent_stars
    if total_stars > 0:
        clan_stars_pct = int((clan_stars / total_stars) * 100)
        opponent_stars_pct = 100 - clan_stars_pct
    else:
        clan_stars_pct = 50
        opponent_stars_pct = 50

    clan_destruction_pct = max(0, min(100, int(round(clan_destruction))))
    opponent_destruction_pct = max(0, min(100, int(round(opponent_destruction))))

    clan_attacks_pct = int((clan_attacks / max_attacks) * 100) if max_attacks else 0
    opponent_attacks_pct = int((opponent_attacks / max_attacks) * 100) if max_attacks else 0

    def attack_star_buckets(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        return {
            3: sum(1 for a in attacks if a.get("stars") == 3),
            2: sum(1 for a in attacks if a.get("stars") == 2),
            1: sum(1 for a in attacks if a.get("stars") == 1),
            0: sum(1 for a in attacks if a.get("stars") == 0),
        }

    clan_buckets = attack_star_buckets(clan)
    opp_buckets = attack_star_buckets(opponent)

    clan_avg_stars = round(clan_stars / clan_attacks, 2) if clan_attacks else 0
    opp_avg_stars = round(opponent_stars / opponent_attacks, 2) if opponent_attacks else 0

    def average_attack_destruction(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        if not attacks:
            return 0
        total_destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        return round(total_destruction / len(attacks), 2)

    clan_avg_dest = average_attack_destruction(clan)
    opp_avg_dest = average_attack_destruction(opponent)

    end_time = war.get("endTime")
    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = end_dt - now
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            time_remaining = "Ended"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_remaining = f"{hours}h {minutes:02d}m"
    else:
        time_remaining = "N/A"

    def calculate_actual_mvp(clan_data):
        best_name = None
        best_score = -1

        for member in clan_data.get("members", []):
            attacks = member.get("attacks", [])
            if not attacks:
                continue

            score = get_war_member_performance(member, tag_to_discord, shop_data, banner_now)["score"]

            if score > best_score:
                best_score = score
                best_name = member.get("name")

        return best_name

    plan_data = {"targets": []}

    if war_state == "warEnded":
        mvp = calculate_actual_mvp(clan) or "TBD"
        mvp_label = "War MVP"
        war_plan_html = ""
        war_insights_html = """
        <div class="war-insights-section">
            <div class="war-insights-title">War Insights</div>
            <div class="war-insights-grid">
                <div class="war-insight-card">
                    <div class="war-insight-label">Phase</div>
                    <div class="war-insight-value">Ended</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Strategy</div>
                    <div class="war-insight-value">Ended</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Win Chance</div>
                    <div class="war-insight-value">—</div>
                </div>
            </div>
        </div>
        """
    else:
        mvp = ai_data.get("mvp")
        
        if not mvp:
            mvp = calculate_actual_mvp(clan) or "—"
        mvp_label = "Predicted MVP"
        plan_data = build_war_plan_data(war, ai_data)
        war_plan_html = render_war_plan_html(plan_data)

        phase = str(ai_data.get("phase") or "Active").title()
        strategy = str(ai_data.get("strategy") or "Standard").title()
        win_chance = ai_data.get("win_chance")

        if isinstance(win_chance, (int, float)):
            win_chance_text = f"{win_chance:.1f}%"
        else:
            # Fallback live estimation
            if clan_stars > opponent_stars:
                win_chance_text = "99.0%"
            elif clan_stars == opponent_stars:
                win_chance_text = "50.0%"
            else:
                win_chance_text = "1.0%"

        war_insights_html = f"""
        <div class="war-insights-section">
            <div class="war-insights-title">War Insights</div>
            <div class="war-insights-grid">
                <div class="war-insight-card">
                    <div class="war-insight-label">Phase</div>
                    <div class="war-insight-value">{phase}</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Strategy</div>
                    <div class="war-insight-value">{strategy}</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Win Chance</div>
                    <div class="war-insight-value">{win_chance_text}</div>
                </div>
            </div>
        </div>
        """

    plan_target_count = len(plan_data.get("targets", []))
    html = inject_large_war_plan_css(html, plan_target_count)

    replacements = {
        "{{CLAN_BADGE}}": clan_badge,
        "{{OPPONENT_BADGE}}": opponent_badge,
        "{{TIME_REMAINING}}": time_remaining,
        "{{CLAN_STARS}}": str(clan_stars),
        "{{OPPONENT_STARS}}": str(opponent_stars),
        "{{CLAN_STARS_PCT}}": str(clan_stars_pct),
        "{{OPPONENT_STARS_PCT}}": str(opponent_stars_pct),
        "{{CLAN_DESTRUCTION}}": f"{clan_destruction:.2f}",
        "{{OPPONENT_DESTRUCTION}}": f"{opponent_destruction:.2f}",
        "{{CLAN_DESTRUCTION_PCT}}": str(clan_destruction_pct),
        "{{OPPONENT_DESTRUCTION_PCT}}": str(opponent_destruction_pct),
        "{{CLAN_ATTACKS}}": f"{clan_attacks}/{max_attacks}",
        "{{OPPONENT_ATTACKS}}": f"{opponent_attacks}/{max_attacks}",
        "{{CLAN_ATTACKS_PCT}}": str(clan_attacks_pct),
        "{{OPPONENT_ATTACKS_PCT}}": str(opponent_attacks_pct),
        "{{CLAN_3STARS}}": str(clan_buckets[3]),
        "{{OPP_3STARS}}": str(opp_buckets[3]),
        "{{CLAN_2STARS}}": str(clan_buckets[2]),
        "{{OPP_2STARS}}": str(opp_buckets[2]),
        "{{CLAN_1STARS}}": str(clan_buckets[1]),
        "{{OPP_1STARS}}": str(opp_buckets[1]),
        "{{CLAN_0STARS}}": str(clan_buckets[0]),
        "{{OPP_0STARS}}": str(opp_buckets[0]),
        "{{CLAN_AVG_STARS}}": f"{clan_avg_stars:.2f}",
        "{{OPP_AVG_STARS}}": f"{opp_avg_stars:.2f}",
        "{{CLAN_AVG_DEST}}": f"{clan_avg_dest:.2f}",
        "{{OPP_AVG_DEST}}": f"{opp_avg_dest:.2f}",
        "{{MVP}}": str(mvp),
        "{{MVP_LABEL}}": str(mvp_label),
        "{{CLAN_NAME}}": clan.get("name", "Clan"),
        "{{OPPONENT_NAME}}": opponent.get("name", "Opponent"),
        "{{WAR_INSIGHTS_HTML}}": war_insights_html,
        "{{WAR_PLAN_HTML}}": war_plan_html,
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    return await render_html_to_png_buffer(
        html,
        width=1000,
        height=1400,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )


async def create_final_war_image(
    *,
    war,
    final_war_template_path,
    load_war_banner_context,
    get_war_member_performance,
    get_war_result,
    render_html_to_png_buffer,
    get_war_mvp_stats=None,
):
    def _read_template():
        with open(final_war_template_path, "r", encoding="utf-8") as f:
            return f.read()

    html = await asyncio.to_thread(_read_template)
    tag_to_discord, shop_data, banner_now = await load_war_banner_context()

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    clan_name = clan.get("name", "Clan")
    opponent_name = opponent.get("name", "Opponent")

    clan_badge = clan.get("badgeUrls", {}).get("large", "")
    opponent_badge = opponent.get("badgeUrls", {}).get("large", "")

    clan_stars = clan.get("stars", 0) or 0
    opp_stars = opponent.get("stars", 0) or 0

    clan_destruction = float(clan.get("destructionPercentage", 0) or 0)
    opp_destruction = float(opponent.get("destructionPercentage", 0) or 0)

    clan_attacks = clan.get("attacks", 0) or 0
    opp_attacks = opponent.get("attacks", 0) or 0

    team_size = war.get("teamSize", 0) or 0
    attacks_per_member = war.get("attacksPerMember", 2) or 2
    max_attacks = team_size * attacks_per_member

    def attack_star_buckets(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        return {
            3: sum(1 for a in attacks if a.get("stars") == 3),
            2: sum(1 for a in attacks if a.get("stars") == 2),
            1: sum(1 for a in attacks if a.get("stars") == 1),
            0: sum(1 for a in attacks if a.get("stars") == 0),
        }

    clan_buckets = attack_star_buckets(clan)
    opp_buckets = attack_star_buckets(opponent)

    def average_attack_destruction(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        if not attacks:
            return 0
        total_destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        return round(total_destruction / len(attacks), 2)

    clan_avg_stars = round(clan_stars / clan_attacks, 2) if clan_attacks else 0
    opp_avg_stars = round(opp_stars / opp_attacks, 2) if opp_attacks else 0
    clan_avg_dest = average_attack_destruction(clan)
    opp_avg_dest = average_attack_destruction(opponent)

    result, _discord_color, result_color = get_war_result(clan, opponent)

    def calculate_actual_mvp(clan_data):
        best_name = None
        best_score = -1

        for member in clan_data.get("members", []):
            attacks = member.get("attacks", [])
            if not attacks:
                continue

            score = get_war_member_performance(member, tag_to_discord, shop_data, banner_now)["score"]

            if score > best_score:
                best_score = score
                best_name = member.get("name")

        return best_name or "—"

    mvp_data = None
    if callable(get_war_mvp_stats):
        mvp_data = get_war_mvp_stats(war, tag_to_discord, shop_data, banner_now)
    
    if mvp_data:
        mvp = mvp_data.get("name", "—")
        mvp_stars = mvp_data.get("stars", 0)
        mvp_destruction = round(mvp_data.get("destruction", 0), 1)
        mvp_triples = mvp_data.get("triples", 0)
        mvp_attacks = mvp_data.get("attacks", 0)
    else:
        mvp = calculate_actual_mvp(clan)
        mvp_stars = mvp_destruction = mvp_triples = mvp_attacks = "—"

    replacements = {
        "{{MVP_STARS}}": str(mvp_stars),
        "{{MVP_DESTRUCTION}}": str(mvp_destruction),
        "{{MVP_TRIPLES}}": str(mvp_triples),
        "{{MVP_ATTACKS}}": str(mvp_attacks),
        "{{CLAN_NAME}}": clan_name,
        "{{OPPONENT_NAME}}": opponent_name,
        "{{CLAN_BADGE}}": clan_badge,
        "{{OPPONENT_BADGE}}": opponent_badge,
        "{{RESULT}}": result,
        "{{RESULT_COLOR}}": result_color,
        "{{CLAN_STARS}}": str(clan_stars),
        "{{OPPONENT_STARS}}": str(opp_stars),
        "{{CLAN_DESTRUCTION}}": f"{clan_destruction:.2f}",
        "{{OPPONENT_DESTRUCTION}}": f"{opp_destruction:.2f}",
        "{{CLAN_ATTACKS}}": f"{clan_attacks}/{max_attacks}",
        "{{OPPONENT_ATTACKS}}": f"{opp_attacks}/{max_attacks}",
        "{{CLAN_3STARS}}": str(clan_buckets[3]),
        "{{OPP_3STARS}}": str(opp_buckets[3]),
        "{{CLAN_2STARS}}": str(clan_buckets[2]),
        "{{OPP_2STARS}}": str(opp_buckets[2]),
        "{{CLAN_1STARS}}": str(clan_buckets[1]),
        "{{OPP_1STARS}}": str(opp_buckets[1]),
        "{{CLAN_0STARS}}": str(clan_buckets[0]),
        "{{OPP_0STARS}}": str(opp_buckets[0]),
        "{{CLAN_AVG_STARS}}": f"{clan_avg_stars:.2f}",
        "{{OPP_AVG_STARS}}": f"{opp_avg_stars:.2f}",
        "{{CLAN_AVG_DEST}}": f"{clan_avg_dest:.2f}",
        "{{OPP_AVG_DEST}}": f"{opp_avg_dest:.2f}",
        "{{MVP}}": mvp,
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    return await render_html_to_png_buffer(
        html,
        width=1000,
        height=1000,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )
