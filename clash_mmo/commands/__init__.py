from clash_mmo.commands.heroes_commands import register_heroes_commands
from clash_mmo.commands.pve_commands import register_pve_commands
from clash_mmo.commands.economy_commands import register_economy_commands
from clash_mmo.commands.core_economy_commands import register_core_economy_commands
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
from clash_mmo.commands.admin_commands import register_admin_commands
from clash_mmo.commands.systems_guide_commands import register_systems_guide_commands
from clash_mmo.commands.loot_commands import register_loot_commands
from clash_mmo.commands.shop_commands import register_shop_commands
from clash_mmo.commands.wallet_commands import register_wallet_commands


def register_clash_mmo_commands(bot, ctx):
    register_economy_commands(bot, ctx)
    register_core_economy_commands(bot, ctx)
    register_clan_economy_commands(bot, ctx)
    register_pvp_commands(bot, ctx)
    register_pve_commands(bot, ctx)
    register_season_commands(bot, ctx)
    register_cosmetic_commands(bot, ctx)
    register_gear_commands(bot, ctx)
    register_ranked_commands(bot, ctx)
    register_territory_commands(bot, ctx)
    register_raid_commands(bot, ctx)
    register_market_commands(bot, ctx)
    register_event_commands(bot, ctx)
    register_admin_commands(bot, ctx)
    register_heroes_commands(bot, ctx)
    register_systems_guide_commands(bot, ctx)
