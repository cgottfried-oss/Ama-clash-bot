from __future__ import annotations

import asyncio
import traceback
from collections.abc import Awaitable, Callable, Sequence
from typing import Any


async def run_update_cycle(
    *,
    bot: Any,
    clan_tags: Sequence[str],
    main_clan_tag: str | None,
    clan_stats_channel_id: int,
    fetch_clan_data: Callable[[str], Awaitable[tuple[Any, list[dict[str, Any]]]]],
    update_donation_leaderboard: Callable[[list[dict[str, Any]], Any], Awaitable[None]],
    process_war_updates: Callable[..., Awaitable[None]],
) -> None:
    await asyncio.sleep(1)

    try:
        for clan_tag in clan_tags:
            if not clan_tag:
                continue

            is_main_clan = clan_tag == main_clan_tag
            war, members = await fetch_clan_data(clan_tag)

            # Keep the existing donation leaderboard tied to the main clan only.
            if is_main_clan:
                stats_channel = bot.get_channel(clan_stats_channel_id)
                if stats_channel and members:
                    await update_donation_leaderboard(members, stats_channel)

            # Process war logic for both clans.
            if war:
                await process_war_updates(
                    war,
                    members,
                    clan_tag,
                    is_main_clan=is_main_clan,
                )

    except Exception as e:
        print(f"[UPDATE LOOP ERROR] {e}")
        traceback.print_exc()


async def update_loop(
    *,
    bot: Any,
    clan_tags: Sequence[str],
    main_clan_tag: str | None,
    clan_stats_channel_id: int,
    fetch_clan_data: Callable[[str], Awaitable[tuple[Any, list[dict[str, Any]]]]],
    update_donation_leaderboard: Callable[[list[dict[str, Any]], Any], Awaitable[None]],
    process_war_updates: Callable[..., Awaitable[None]],
    interval_seconds: int = 120,
) -> None:
    while True:
        await run_update_cycle(
            bot=bot,
            clan_tags=clan_tags,
            main_clan_tag=main_clan_tag,
            clan_stats_channel_id=clan_stats_channel_id,
            fetch_clan_data=fetch_clan_data,
            update_donation_leaderboard=update_donation_leaderboard,
            process_war_updates=process_war_updates,
        )
        await asyncio.sleep(interval_seconds)
