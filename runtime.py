from __future__ import annotations

from typing import Any, Callable

from clash_api import ClashApiClient
from economy import EconomyManager
from war.context import WarRuntimeContext

from config import (
    ASSETS_DIR,
    CACHE_FILE,
    CLAN_CHAT_CHANNEL_ID,
    CLAN_TAGS,
    CLASH_API_KEY,
    COINS_FILE,
    CURRENT_WAR_MVP_FILE,
    DATA_DIR,
    DONATION_TEMPLATE_PATH,
    FEEDER_WAR_CHANNEL_ID,
    FINAL_WAR_TEMPLATE_PATH,
    LINKED_FILE,
    MAIN_CLAN_TAG,
    MONTHLY_MVP_FILE,
    PERFORMANCE_FILE,
    SHOP_FILE,
    TEMPLATES_DIR,
    WAR_CHANNEL_ID,
    WAR_END_FILE,
    WAR_MVP_ROLE_ID,
    WAR_PINGS_FILE,
    WAR_SUMMARY_CHANNEL_ID,
    WAR_SUMMARY_POSTS_FILE,
    WAR_TEMPLATE_PATH,
)

from reward_config import (
    CLUTCH_COIN_REWARD,
    CLUTCH_REWARD_TIERS,
    STAR_COIN_REWARD,
    WAR_MVP_BONUS,
)

from clash_mmo.config.economy_config import SHOP_ITEMS


def create_economy_manager() -> EconomyManager:
    return EconomyManager(
        coins_file=COINS_FILE,
        shop_file=SHOP_FILE,
        linked_file=LINKED_FILE,
        shop_items=SHOP_ITEMS,
        star_coin_reward=STAR_COIN_REWARD,
        war_mvp_bonus=WAR_MVP_BONUS,
        clutch_coin_reward=CLUTCH_COIN_REWARD,
        clutch_reward_tiers=CLUTCH_REWARD_TIERS,
    )


def create_clash_client(
    *,
    safe_load_json: Callable[..., Any],
    safe_save_json: Callable[..., Any],
) -> ClashApiClient:
    return ClashApiClient(
        api_key=CLASH_API_KEY,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        cache_file=CACHE_FILE,
    )


def create_war_runtime_context(
    *,
    bot: Any,
    economy: EconomyManager,
    safe_load_json: Callable[..., Any],
    safe_save_json: Callable[..., Any],
    update_json_file: Callable[..., Any],
    normalize_tag: Callable[..., Any],
    normalize_linked_data: Callable[..., Any],
    build_tag_to_discord_map: Callable[..., Any],
    get_cached_or_fetch: Callable[..., Any],
) -> WarRuntimeContext:
    return WarRuntimeContext(
        bot=bot,
        economy=economy,
        data_dir=DATA_DIR,
        assets_dir=ASSETS_DIR,
        templates_dir=TEMPLATES_DIR,
        war_channel_id=WAR_CHANNEL_ID,
        feeder_war_channel_id=FEEDER_WAR_CHANNEL_ID,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
        war_summary_channel_id=WAR_SUMMARY_CHANNEL_ID,
        war_mvp_role_id=WAR_MVP_ROLE_ID,
        main_clan_tag=MAIN_CLAN_TAG,
        clan_tags=CLAN_TAGS,
        linked_file=LINKED_FILE,
        war_pings_file=WAR_PINGS_FILE,
        war_end_file=WAR_END_FILE,
        war_summary_posts_file=WAR_SUMMARY_POSTS_FILE,
        performance_file=PERFORMANCE_FILE,
        monthly_mvp_file=MONTHLY_MVP_FILE,
        current_war_mvp_file=CURRENT_WAR_MVP_FILE,
        war_template_path=WAR_TEMPLATE_PATH,
        final_war_template_path=FINAL_WAR_TEMPLATE_PATH,
        donation_template_path=DONATION_TEMPLATE_PATH,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        update_json_file=update_json_file,
        normalize_tag=normalize_tag,
        normalize_linked_data=normalize_linked_data,
        build_tag_to_discord_map=build_tag_to_discord_map,
        get_cached_or_fetch=get_cached_or_fetch,
    )
