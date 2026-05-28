from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import discord

from clash_mmo.config.economy_config import SHOP_ITEMS
from war import mvp as war_mvp
from war import summaries as war_summaries
from mvp_roles import (
    generate_war_mvp_title,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
)


def get_season_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_war_id(war: dict[str, Any]):
    return war_mvp.get_war_id(war)


def get_war_result(clan: dict, opponent: dict):
    return war_mvp.get_war_result(clan, opponent)


def get_war_banner_stat_multiplier(
    member: dict[str, Any],
    tag_to_discord=None,
    shop_data=None,
    now=None,
    *,
    economy,
):
    return war_mvp.get_war_banner_stat_multiplier(
        member,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
        shop_items=SHOP_ITEMS,
    )


def get_war_member_performance(
    member: dict[str, Any],
    tag_to_discord=None,
    shop_data=None,
    now=None,
    *,
    economy,
):
    return war_mvp.get_war_member_performance(
        member,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
        shop_items=SHOP_ITEMS,
    )


def get_war_mvp_stats(
    war: dict[str, Any],
    tag_to_discord=None,
    shop_data=None,
    now=None,
    *,
    economy,
):
    return war_mvp.get_war_mvp_stats(
        war,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
        shop_items=SHOP_ITEMS,
    )


async def load_war_banner_context(*, safe_load_json, linked_file: str, economy):
    linked_raw = await safe_load_json(linked_file)
    linked = economy.normalize_linked_data(linked_raw)
    tag_to_discord = economy.build_tag_to_discord_map(linked)
    shop_data = await economy.load_shop_data()
    return tag_to_discord, shop_data, int(time.time())


async def update_monthly_mvp_from_war(
    war: dict[str, Any],
    *,
    economy,
    linked_file: str,
    monthly_mvp_file: str,
    safe_load_json,
    update_json_file,
) -> None:
    if war.get("state") != "warEnded":
        return

    season_key = get_season_key()
    war_id = get_war_id(war)
    clan = war.get("clan", {})
    tag_to_discord, shop_data, banner_now = await load_war_banner_context(
        safe_load_json=safe_load_json,
        linked_file=linked_file,
        economy=economy,
    )

    def _update_mvp(stored):
        if not isinstance(stored, dict):
            stored = {}

        if stored.get("season") != season_key:
            stored = {
                "season": season_key,
                "wars": [],
                "players": {},
            }

        processed_wars = stored.setdefault("wars", [])
        players = stored.setdefault("players", {})

        if war_id in processed_wars:
            return stored

        for member in clan.get("members", []):
            name = member.get("name")
            if not name:
                continue

            attacks = member.get("attacks", [])
            if not attacks:
                continue

            perf = get_war_member_performance(
                member,
                tag_to_discord,
                shop_data,
                banner_now,
                economy=economy,
            )
            stars = perf["stars"]
            destruction = perf["destruction"]
            attack_count = perf["attacks"]
            triples = perf["triples"]
            score = perf["score"]

            players.setdefault(
                name,
                {
                    "points": 0,
                    "wars": 0,
                    "attacks": 0,
                    "stars": 0,
                    "destruction": 0,
                    "triples": 0,
                },
            )

            players[name]["points"] += round(score, 2)
            players[name]["wars"] += 1
            players[name]["attacks"] += attack_count
            players[name]["stars"] += stars
            players[name]["destruction"] += round(destruction, 2)
            players[name]["triples"] += triples

        processed_wars.append(war_id)
        return stored

    await update_json_file(monthly_mvp_file, _update_mvp)


async def post_war_mvp_announcement(
    war: dict[str, Any],
    *,
    channel: discord.abc.Messageable | None = None,
    war_rewards=None,
    clan_chat_channel_id: int,
    bot,
    economy,
    linked_file: str,
    current_war_mvp_file: str,
    war_mvp_role_id: int,
    safe_load_json,
    safe_save_json,
    reward_war_coins,
    format_member_mention,
):
    async def _load_war_banner_context():
        return await load_war_banner_context(
            safe_load_json=safe_load_json,
            linked_file=linked_file,
            economy=economy,
        )

    def _get_war_mvp_stats(current_war, tag_to_discord=None, shop_data=None, now=None):
        return get_war_mvp_stats(
            current_war,
            tag_to_discord,
            shop_data,
            now,
            economy=economy,
        )

    return await war_summaries.post_war_mvp_announcement(
        war=war,
        channel=channel,
        clan_chat_channel_id=clan_chat_channel_id,
        bot=bot,
        get_war_result=get_war_result,
        get_war_id=get_war_id,
        get_war_mvp_stats=_get_war_mvp_stats,
        load_war_banner_context=_load_war_banner_context,
        reward_war_coins=reward_war_coins,
        format_member_mention=format_member_mention,
        generate_war_mvp_title=generate_war_mvp_title,
        rotate_war_mvp_role=rotate_war_mvp_role,
        update_war_mvp_role_presentation=update_war_mvp_role_presentation,
        current_war_mvp_file=current_war_mvp_file,
        war_mvp_role_id=war_mvp_role_id,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        war_rewards=war_rewards,
    )
