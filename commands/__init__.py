from .economy_commands import register_economy_commands
from .economy_game_commands import register_economy_game_commands
from .economy_phase3_commands import register_economy_phase3_commands
from .economy_phase4_commands import register_economy_phase4_commands
from .economy_phase5_1_commands import register_economy_phase5_1_commands
from .economy_phase5_2_commands import register_economy_phase5_2_commands
from .rpg_guide_commands import register_rpg_guide_commands
from .linking_commands import register_linking_commands
from .changelog import register_changelog


def register_all_commands(bot, ctx):
    register_economy_commands(bot, ctx)
    register_economy_game_commands(bot, ctx)
    register_economy_phase3_commands(bot, ctx)
    register_economy_phase4_commands(bot, ctx)
    register_economy_phase5_1_commands(bot, ctx)
    register_economy_phase5_2_commands(bot, ctx)
    register_rpg_guide_commands(bot, ctx)
    register_linking_commands(bot, ctx)
    register_changelog(bot, ctx)
