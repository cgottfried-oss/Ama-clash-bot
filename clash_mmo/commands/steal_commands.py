from __future__ import annotations

import discord
from discord import app_commands


def register_steal_commands(bot, ctx):
    steal_coins = ctx.steal_coins

    @bot.tree.command(name="steal", description="Try to steal coins from another user")
    @app_commands.describe(target="The user you want to try stealing coins from")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def steal(interaction: discord.Interaction, target: discord.Member):
        if target.bot:
            await interaction.response.send_message("❌ You cannot steal from bots.", ephemeral=True)
            return

        if target.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot steal from yourself.", ephemeral=True)
            return

        result = await steal_coins(
            thief_id=str(interaction.user.id),
            thief_name=getattr(interaction.user, "display_name", interaction.user.name),
            victim_id=str(target.id),
            victim_name=getattr(target, "display_name", target.name),
        )

        if result.get("reason") == "shielded":
            await interaction.response.send_message(
                f"🛡️ {target.mention}'s **Loot Shield** blocked the steal attempt and was consumed!",
                ephemeral=False,
            )
            return

        if result.get("reason") == "victim_broke":
            await interaction.response.send_message(
                f"❌ {target.mention} has no coins to steal.",
                ephemeral=True,
            )
            return

        banner_note = " 🏴 War Banner made the steal harder." if result.get("war_banner_protected") else ""

        if result.get("success"):
            await interaction.response.send_message(
                f"🦹 {interaction.user.mention} stole **{result['amount']}** coins from {target.mention}! "
                f"New balance: **{result['thief_balance']}** coins.{banner_note}",
                ephemeral=False,
            )
            return

        await interaction.response.send_message(
            f"🚨 {interaction.user.mention} got caught trying to steal from {target.mention} "
            f"and paid **{result.get('penalty', 0)}** coins as a penalty.{banner_note}",
            ephemeral=False,
        )

    @steal.error
    async def steal_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ You can try stealing again in **{int(error.retry_after)}** seconds.",
                ephemeral=True,
            )
            return
        raise error
