from __future__ import annotations

from clash_mmo.commands.wallet_commands import register_wallet_commands
from clash_mmo.commands.shop_commands import register_shop_commands
from clash_mmo.commands.loot_commands import register_loot_commands


def register_economy_commands(bot, ctx):
    register_wallet_commands(bot, ctx)
    register_shop_commands(bot, ctx)
    register_loot_commands(bot, ctx)