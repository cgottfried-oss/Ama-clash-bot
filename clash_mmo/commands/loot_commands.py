from __future__ import annotations

from datetime import datetime

import discord


def register_loot_commands(bot, ctx):
    leader_role_id = ctx.LEADER_ROLE_ID
    co_leader_role_id = ctx.CO_LEADER_ROLE_ID
    clan_chat_channel_id = ctx.CLAN_CHAT_CHANNEL_ID
    loot_drop_file = ctx.LOOT_DROP_FILE

    safe_save_json = ctx.safe_save_json
    create_loot_drop = ctx.create_loot_drop
    load_loot_drop = ctx.load_loot_drop
    schedule_next_loot_drop = ctx.schedule_next_loot_drop

    def _is_leader(member: discord.Member) -> bool:
        return any(role.id in {leader_role_id, co_leader_role_id} for role in member.roles)

    async def _require_leader(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Could not verify your server roles.",
                ephemeral=True,
            )
            return False

        if not _is_leader(interaction.user):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
            return False

        return True

    @bot.tree.command(name="spawnloot", description="Manually spawn a loot drop in clan chat")
    async def spawnloot(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This command must be used in a server.",
                ephemeral=True,
            )
            return

        if not await _require_leader(interaction):
            return

        created = await create_loot_drop()
        if not created:
            await interaction.response.send_message(
                "There is already an active loot drop.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ Loot drop spawned in clan chat.",
            ephemeral=True,
        )

    @bot.tree.command(name="dropstatus", description="View the current loot drop status")
    async def dropstatus(interaction: discord.Interaction):
        if not await _require_leader(interaction):
            return

        drop = await load_loot_drop()

        active = drop.get("active", False)
        style = drop.get("style") or "None"
        reward = drop.get("reward", 0)
        claimed_by = drop.get("claimed_by")
        next_drop_at_raw = drop.get("next_drop_at")
        created_at_raw = drop.get("created_at")

        embed = discord.Embed(
            title="📦 Loot Drop Status",
            color=0x3498DB,
        )

        embed.add_field(
            name="Active Drop",
            value="Yes" if active else "No",
            inline=True,
        )
        embed.add_field(
            name="Style",
            value=str(style).replace("_", " ").title(),
            inline=True,
        )
        embed.add_field(
            name="Reward",
            value=f"{reward} coins" if reward else "None",
            inline=True,
        )
        embed.add_field(
            name="Last Claimed By",
            value=f"<@{claimed_by}>" if claimed_by else "Nobody yet",
            inline=True,
        )

        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(created_at_raw)
                created_value = discord.utils.format_dt(created_at, style="R")
            except Exception:
                created_value = str(created_at_raw)
        else:
            created_value = "N/A"
        embed.add_field(name="Created At", value=created_value, inline=True)

        if next_drop_at_raw:
            try:
                next_drop_at = datetime.fromisoformat(next_drop_at_raw)
                next_value = (
                    f"{discord.utils.format_dt(next_drop_at, style='F')}\n"
                    f"({discord.utils.format_dt(next_drop_at, style='R')})"
                )
            except Exception:
                next_value = str(next_drop_at_raw)
        else:
            next_value = "Not scheduled yet"
        embed.add_field(name="Next Scheduled Drop", value=next_value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="resetdrop", description="Reset the current loot drop state")
    async def resetdrop(interaction: discord.Interaction):
        if not await _require_leader(interaction):
            return

        drop = await load_loot_drop()

        drop["active"] = False
        drop["drop_id"] = None
        drop["channel_id"] = clan_chat_channel_id
        drop["reward"] = 0
        drop["style"] = None
        drop["claimed_by"] = None
        drop["message_id"] = None
        drop["created_at"] = None
        drop["next_drop_at"] = None

        await safe_save_json(loot_drop_file, drop)
        await schedule_next_loot_drop()

        updated = await load_loot_drop()
        next_drop_at_raw = updated.get("next_drop_at")

        next_text = "Scheduled"
        if next_drop_at_raw:
            try:
                next_drop_at = datetime.fromisoformat(next_drop_at_raw)
                next_text = (
                    f"{discord.utils.format_dt(next_drop_at, style='F')} "
                    f"({discord.utils.format_dt(next_drop_at, style='R')})"
                )
            except Exception:
                next_text = str(next_drop_at_raw)

        await interaction.response.send_message(
            f"✅ Loot drop state reset.\nNext drop: {next_text}",
            ephemeral=True,
        )
