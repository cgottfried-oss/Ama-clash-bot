from __future__ import annotations


def get_clutch_scope_key(war, normalize_tag):
    clan = war.get("clan") or {}
    clan_tag = normalize_tag(clan.get("tag", ""))
    if not clan_tag:
        return None
    return clan_tag.replace("#", "")


def get_clutch_log_file(war, *, data_dir: str, normalize_tag):
    import os

    scope_key = get_clutch_scope_key(war, normalize_tag)
    if not scope_key:
        return None
    return os.path.join(data_dir, f"clutch_log_{scope_key}.json")


def get_clutch_state_file(war, *, data_dir: str, normalize_tag):
    import os

    scope_key = get_clutch_scope_key(war, normalize_tag)
    if not scope_key:
        return None
    return os.path.join(data_dir, f"clutch_state_{scope_key}.json")


def classify_war_state(star_diff, destruction_diff):
    if star_diff > 0:
        return "winning"
    if star_diff < 0:
        return "losing"
    if destruction_diff > 0:
        return "winning"
    if destruction_diff < 0:
        return "losing"
    return "tied"


def collect_clan_attacks(war, normalize_tag):
    attacks = []
    for member in war.get("clan", {}).get("members", []):
        member_tag = member.get("tag", "")
        member_name = member.get("name", "Someone")
        for attack in member.get("attacks", []):
            attacks.append(
                {
                    "member_tag": member_tag,
                    "member_name": member_name,
                    "attack": attack,
                    "order": attack.get("order", 0),
                    "defender_tag": normalize_tag(attack.get("defenderTag", "")),
                    "stars": attack.get("stars", 0) or 0,
                    "destruction": attack.get("destructionPercentage", 0) or 0,
                }
            )
    attacks.sort(key=lambda x: x["order"])
    return attacks


def get_prior_best_on_defender(war, defender_tag, attack_order, normalize_tag):
    defender_tag = normalize_tag(defender_tag)
    best_stars = 0
    best_destruction = 0

    for item in collect_clan_attacks(war, normalize_tag):
        if item["order"] >= attack_order:
            break
        if item["defender_tag"] != defender_tag:
            continue

        stars = item["stars"]
        destruction = item["destruction"]
        if stars > best_stars or (stars == best_stars and destruction > best_destruction):
            best_stars = stars
            best_destruction = destruction

    return {"stars": best_stars, "destruction": best_destruction}


def get_attack_impact(attack, war, normalize_tag):
    defender_tag = attack.get("defenderTag", "")
    attack_order = attack.get("order", 0)
    new_stars = attack.get("stars", 0) or 0
    new_destruction = attack.get("destructionPercentage", 0) or 0
    prior_best = get_prior_best_on_defender(war, defender_tag, attack_order, normalize_tag)

    star_gain = max(0, new_stars - prior_best["stars"])
    destruction_gain = 0
    if new_stars > prior_best["stars"]:
        destruction_gain = new_destruction
    elif new_stars == prior_best["stars"] and new_destruction > prior_best["destruction"]:
        destruction_gain = new_destruction - prior_best["destruction"]

    return {
        "prior_best_stars": prior_best["stars"],
        "prior_best_destruction": prior_best["destruction"],
        "star_gain": star_gain,
        "destruction_gain": destruction_gain,
        "is_new_triple": new_stars == 3 and prior_best["stars"] < 3,
    }


def build_attack_id(member_tag, attack, normalize_tag):
    return f"{normalize_tag(member_tag)}_{normalize_tag(attack.get('defenderTag', ''))}_{attack.get('order', 0)}"


def get_clutch_reward_amount(clutch_type, clutch_reward_tiers, default_reward):
    return int(clutch_reward_tiers.get(str(clutch_type or ""), default_reward))


def is_clutch_attack(
    attack,
    war,
    *,
    attacker_tag=None,
    get_defender_position,
    get_attacker_position,
    get_attacker_townhall_level,
    get_defender_townhall_level,
    normalize_tag,
):
    from datetime import datetime

    try:
        end_time = war.get("endTime")
        if not end_time:
            return None

        now = datetime.utcnow()
        war_end = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z")
        time_left_seconds = (war_end - now).total_seconds()
        if time_left_seconds < 0:
            return None

        defender_pos = get_defender_position(attack, war)
        attacker_pos = get_attacker_position(attack, war, attacker_tag=attacker_tag)
        attacker_th = get_attacker_townhall_level(attack, war, attacker_tag=attacker_tag)
        defender_th = get_defender_townhall_level(attack, war)
        impact = get_attack_impact(attack, war, normalize_tag)

        if impact["star_gain"] <= 0 and impact["destruction_gain"] <= 0:
            return None

        clan = war.get("clan", {})
        opponent = war.get("opponent", {})

        clan_stars_after = clan.get("stars", 0) or 0
        clan_destruction_after = float(clan.get("destructionPercentage", 0) or 0)
        opponent_stars = opponent.get("stars", 0) or 0
        opponent_destruction = float(opponent.get("destructionPercentage", 0) or 0)

        clan_stars_before = clan_stars_after - impact["star_gain"]
        clan_destruction_before = clan_destruction_after - impact["destruction_gain"]

        before_state = classify_war_state(
            clan_stars_before - opponent_stars,
            clan_destruction_before - opponent_destruction,
        )
        after_state = classify_war_state(
            clan_stars_after - opponent_stars,
            clan_destruction_after - opponent_destruction,
        )

        stars = attack.get("stars", 0) or 0
        is_new_triple = impact["is_new_triple"]

        th_gap = None
        if attacker_th is not None and defender_th is not None:
            th_gap = int(defender_th) - int(attacker_th)

        if (
            0 <= time_left_seconds <= 3600
            and is_new_triple
            and before_state != after_state
            and after_state in {"tied", "winning"}
        ):
            return "lead_flip"

        if (
            0 <= time_left_seconds <= 1800
            and is_new_triple
            and (clan_stars_after - opponent_stars) >= -1
            and (clan_stars_before - opponent_stars) <= -2
        ):
            return "keep_alive"

        if (
            0 <= time_left_seconds <= 900
            and stars == 3
            and is_new_triple
            and impact["prior_best_stars"] >= 2
        ):
            return "last_stand"

        if is_new_triple and th_gap is not None and th_gap >= 1:
            return "underdog_triple"

        if is_new_triple and defender_pos is not None and defender_pos <= 3:
            return "top_three_triple"

        if (
            is_new_triple
            and defender_pos is not None
            and defender_pos <= 5
            and attacker_pos is not None
            and (attacker_pos - defender_pos) >= 5
        ):
            return "rank_upset"

        if (
            defender_pos is not None
            and defender_pos <= 3
            and is_new_triple
            and (
                abs(clan_stars_before - opponent_stars) <= 3
                or 0 <= time_left_seconds <= 21600
            )
        ):
            return "top_base"

        return None

    except Exception as e:
        print(f"[CLUTCH CHECK ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None
