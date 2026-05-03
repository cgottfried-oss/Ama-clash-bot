from __future__ import annotations

import asyncio
from typing import Any


async def run_update_cycle(ctx: dict[str, Any]):
    """
    This function will contain ONE full iteration of your bot's update logic.
    Keep it as a direct move from bot_runner.py (no logic changes).
    """
    # TODO: Move logic here from bot_runner.py safely
    pass


async def update_loop(ctx: dict[str, Any], interval_seconds: int = 120):
    """
    Simple async loop wrapper.
    Keeps behavior identical to your existing loop.
    """
    while True:
        try:
            await run_update_cycle(ctx)
        except Exception as e:
            print(f"[UPDATE LOOP ERROR] {e}")
        await asyncio.sleep(interval_seconds)


async def start_update_loop(bot, ctx: dict[str, Any]):
    """
    Starts the loop without blocking Discord bot startup.
    """
    bot.loop.create_task(update_loop(ctx))
