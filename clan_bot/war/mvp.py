from __future__ import annotations


def get_war_id(war):
    clan_tag = war.get("clan", {}).get("tag", "")
    opponent_tag = war.get("opponent", {}).get("tag", "")
    end_time = war.get("endTime", "")
    prep_time = war.get("preparationStartTime", "")
    team_size = war.get("teamSize", 0)
    return f"{clan_tag}_{opponent_tag}_{team_size}_{prep_time}_{end_time}"


def get_war_result(clan: dict, opponent: dict):
    clan_stars = int(clan.get("stars", 0) or 0)
    opp_stars = int(opponent.get("stars", 0) or 0)
    clan_dest = float(clan.get("destructionPercentage", 0) or 0)
    opp_dest = float(opponent.get("destructionPercentage", 0) or 0)

    if clan_stars > opp_stars or (clan_stars == opp_stars and clan_dest > opp_dest):
        return "Victory", 0x2ECC71, "#2ECC71"
    if clan_stars < opp_stars or (clan_stars == opp_stars and clan_dest < opp_dest):
        return "Defeat", 0xE74C3C, "#E74C3C"
    return "Draw", 0xF1C40F, "#F1C40F"


def get_war_banner_stat_multiplier(member, tag_to_discord=None, shop_data=None, now=None, *, economy, shop_items):
    import time

    tag_to_discord = tag_to_discord or {}
    shop_data = shop_data or {}
    now = int(now or time.time())

    player_tag = economy.normalize_tag(member.get("tag", ""))
    discord_id = tag_to_discord.get(player_tag)
    if not discord_id:
        return 1.0

    user_shop = shop_data.get("users", {}).get(str(discord_id), {})
    active_until = int(user_shop.get("active_effects", {}).get("war_banner", 0) or 0)
    if active_until <= now:
        return 1.0

    banner = shop_items.get("war_banner", {})
    return float(banner.get("war_stat_multiplier", 1.10) or 1.10)


def get_war_member_performance(member, tag_to_discord=None, shop_data=None, now=None, *, economy, shop_items):
    attacks = member.get("attacks", [])
    stars = sum(a.get("stars", 0) for a in attacks)
    destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
    triples = sum(1 for a in attacks if a.get("stars", 0) == 3)
    attack_count = len(attacks)
    base_score = stars * 100 + destruction

    banner_multiplier = get_war_banner_stat_multiplier(
        member,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
        shop_items=shop_items,
    )
    score = base_score * banner_multiplier

    return {
        "stars": stars,
        "destruction": round(destruction, 2),
        "triples": triples,
        "attacks": attack_count,
        "base_score": round(base_score, 2),
        "score": round(score, 2),
        "war_banner_active": banner_multiplier > 1.0,
        "war_banner_multiplier": banner_multiplier,
    }


def get_war_mvp_stats(war, tag_to_discord=None, shop_data=None, now=None, *, economy, shop_items):
    clan = war.get("clan", {})
    best_member = None
    best_score = -1

    for member in clan.get("members", []):
        attacks = member.get("attacks", [])
        if not attacks:
            continue

        perf = get_war_member_performance(
            member,
            tag_to_discord,
            shop_data,
            now,
            economy=economy,
            shop_items=shop_items,
        )
        score = float(perf.get("score", 0) or 0)

        if score > best_score:
            best_score = score
            best_member = {
                "name": member.get("name", "Unknown"),
                "tag": member.get("tag", ""),
                **perf,
            }

    return best_member


def get_war_mvp_member(war, tag_to_discord=None, shop_data=None, now=None, *, economy, shop_items):
    best_stats = get_war_mvp_stats(
        war,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
        shop_items=shop_items,
    )
    if not best_stats:
        return None

    for member in war.get("clan", {}).get("members", []):
        if member.get("name") == best_stats.get("name") and member.get("tag") == best_stats.get("tag"):
            return member

    return None