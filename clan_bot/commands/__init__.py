from commands.linking_commands import register_linking_commands
from commands.changelog import register_changelog


def register_clan_bot_commands(bot, ctx):
    register_linking_commands(bot, ctx)
    register_changelog(bot, ctx)