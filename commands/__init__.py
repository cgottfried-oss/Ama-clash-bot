from clash_mmo.commands import register_clash_mmo_commands
from clan_bot.commands import register_clan_bot_commands


def register_all_commands(bot, ctx):
    register_clash_mmo_commands(bot, ctx)
    register_clan_bot_commands(bot, ctx)