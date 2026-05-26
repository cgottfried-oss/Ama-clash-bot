from clash_mmo.commands.economy_commands import register_economy_commands
from clash_mmo.commands.core_economy_commands import register_economy_game_commands
from clash_mmo.commands.clan_economy_commands import register_clan_economy_commands
from clash_mmo.commands.pvp_commands import register_pvp_commands
from clash_mmo.commands.season_commands import register_season_commands
from clash_mmo.commands.cosmetic_commands import register_cosmetic_commands
from clash_mmo.commands.gear_commands import register_gear_commands
from clash_mmo.commands.ranked_commands import register_ranked_commands
from clash_mmo.commands.territory_commands import register_territory_commands
from clash_mmo.commands.raid_commands import register_raid_commands
from clash_mmo.commands.market_commands import register_market_commands
from clash_mmo.commands.event_commands import register_event_commands
from .rpg_guide_commands import register_rpg_guide_commands
from .linking_commands import register_linking_commands
from .changelog import register_changelog


def register_all_commands(bot, ctx):
    register_economy_commands(bot, ctx)
    register_economy_game_commands(bot, ctx)
    register_clan_economy_commands(bot, ctx)
    register_pvp_commands(bot, ctx)
    register_season_commands(bot, ctx)
    register_cosmetic_commands(bot, ctx)
    register_gear_commands(bot, ctx)
    register_ranked_commands(bot, ctx)
    register_territory_commands(bot, ctx)
    register_raid_commands(bot, ctx)
    register_market_commands(bot, ctx)
    register_event_commands(bot, ctx)
    register_rpg_guide_commands(bot, ctx)
    register_linking_commands(bot, ctx)
    register_changelog(bot, ctx)
