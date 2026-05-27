from clan_bot.commands.linking_commands import register_linking_commands


def register_clan_bot_commands(bot, ctx):
    register_linking_commands(bot, ctx)