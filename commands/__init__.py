from .economy_commands import register_economy_commands
from .linking_commands import register_linking_commands
from .changelog import register_changelog


def register_all_commands(bot, ctx):
    register_economy_commands(bot, ctx)
    register_linking_commands(bot, ctx)
    register_changelog(bot, ctx)
