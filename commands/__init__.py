from .economy_commands import register_economy_commands
from clash_mmo.commands.core_economy_commands import register_economy_game_commands
from clash_mmo.commands.clan_economy_commands import register_economy_phase3_commands
from clash_mmo.commands.pvp_commands import register_economy_phase4_commands
from clash_mmo.commands.season_commands import register_economy_phase5_1_commands
from clash_mmo.commands.cosmetic_commands import register_economy_phase5_2_commands
from clash_mmo.commands.gear_commands import register_economy_phase5_3_commands
from clash_mmo.commands.ranked_commands import register_economy_commands as register_economy_phase5_4_commands
from clash_mmo.commands.territory_commands import register_economy_phase5_5_commands
from clash_mmo.commands.raid_commands import register_economy_phase5_6_commands
from clash_mmo.commands.market_commands import register_economy_phase5_7_commands
from clash_mmo.commands.event_commands import register_economy_phase5_8_commands
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
    register_economy_phase5_3_commands(bot, ctx)
    register_economy_phase5_4_commands(bot, ctx)
    register_economy_phase5_5_commands(bot, ctx)
    register_economy_phase5_6_commands(bot, ctx)
    register_economy_phase5_7_commands(bot, ctx)
    register_economy_phase5_8_commands(bot, ctx)
    register_rpg_guide_commands(bot, ctx)
    register_linking_commands(bot, ctx)
    register_changelog(bot, ctx)
