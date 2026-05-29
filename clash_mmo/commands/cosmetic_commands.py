from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.cosmetics import (
    COSMETIC_CATALOG,
    equip_owned_cosmetic,
    format_cosmetic_line,
    format_equipped_cosmetics,
    get_player_cosmetics,
    get_equipped_cosmetic_bonuses,
    grant_cosmetic,
)
from clash_mmo.game.state import (
    load_mmo_state,
    update_mmo_state,
)


def register_cosmetic_commands(bot, ctx):
    async def _load_profiles():
        data = await load_mmo_state(ctx)
        data.setdefault("players", {})
        return data

    async def _ensure(interaction: discord.Interaction):
        def _update(container):
            if not isinstance(container, dict):
                container = {}
            ensure_player_profile(container, str(interaction.user.id), interaction.user.display_name)
            return container
        await update_mmo_state(ctx, _update)
        data = await _load_profiles()
        return data["players"][str(interaction.user.id)]

    @bot.tree.command(name="cosmetics", description="View your cosmetic collection")
    async def cosmetics(interaction: discord.Interaction):
        profile = await _ensure(interaction)
        cosmetics_data = get_player_cosmetics(profile)
        owned = cosmetics_data.get("owned", {})
        lines = []
        for category, entries in owned.items():
            if not entries:
                continue
            lines.append(f"__{category.title()}__")
            for cosmetic_id in entries:
                lines.append(format_cosmetic_line(cosmetic_id))
        if not lines:
            lines.append("No cosmetics unlocked yet.")
        embed = discord.Embed(title="🎨 Cosmetic Collection", description="\n".join(lines), color=0x9B59B6)
        equipped = format_equipped_cosmetics(profile) or "None"
        embed.add_field(name="Equipped", value=equipped, inline=False)
        bonuses = get_equipped_cosmetic_bonuses(profile)
        if bonuses:
            bonus_lines = [
                f"**{str(key).replace('_', ' ').title()}**: +{value}{'%' if str(key).endswith('_pct') else ''}"
                for key, value in sorted(bonuses.items())
            ]
            embed.add_field(name="Active Cosmetic Perks", value="\n".join(bonus_lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="equipcosmetic", description="Equip a cosmetic you own")
    @app_commands.describe(cosmetic_id="Cosmetic ID")
    async def equipcosmetic(interaction: discord.Interaction, cosmetic_id: str):
        cosmetic_id = cosmetic_id.strip().lower()
        profile = await _ensure(interaction)
        result = equip_owned_cosmetic(profile, cosmetic_id)
        if not result["ok"]:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        def _update(container):
            ensure_player_profile(container, str(interaction.user.id), interaction.user.display_name)
            container["players"][str(interaction.user.id)] = profile
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"✨ Equipped **{result['cosmetic']['name']}**")

    @equipcosmetic.autocomplete("cosmetic_id")
    async def equipcosmetic_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        profile = await _ensure(interaction)
        cosmetics_data = get_player_cosmetics(profile)
        choices = []
        for category, entries in cosmetics_data.get("owned", {}).items():
            for cosmetic_id in entries:
                cosmetic = COSMETIC_CATALOG.get(cosmetic_id)
                if not cosmetic:
                    continue
                if current in cosmetic_id.lower() or current in cosmetic["name"].lower():
                    choices.append(app_commands.Choice(name=f"{cosmetic['name']} ({category})", value=cosmetic_id))
        return choices[:25]

    @bot.tree.command(name="grantcosmetic", description="Leader tool: grant a cosmetic to a member")
    @app_commands.describe(member="Member to grant cosmetic to", cosmetic_id="Cosmetic ID")
    async def grantcosmetic(interaction: discord.Interaction, member: discord.Member, cosmetic_id: str):
        leader_role_id = ctx.LEADER_ROLE_ID
        co_leader_role_id = ctx.CO_LEADER_ROLE_ID
        if not isinstance(interaction.user, discord.Member) or not any(role.id in {leader_role_id, co_leader_role_id} for role in interaction.user.roles):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return

        cosmetic_id = cosmetic_id.strip().lower()
        result = None

        def _update(container):
            nonlocal result
            profile = ensure_player_profile(container, str(member.id), member.display_name)
            result = grant_cosmetic(profile, cosmetic_id)
            return container

        await update_mmo_state(ctx, _update)
        if not result or not result.get("ok"):
            await interaction.response.send_message(f"❌ {(result or {}).get('error', 'Unknown cosmetic.')}", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Granted **{result['cosmetic']['name']}** to {member.mention}.", ephemeral=True)

    @grantcosmetic.autocomplete("cosmetic_id")
    async def grantcosmetic_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []
        for cosmetic_id, cosmetic in COSMETIC_CATALOG.items():
            if current in cosmetic_id.lower() or current in cosmetic["name"].lower():
                choices.append(app_commands.Choice(name=f"{cosmetic['name']} ({cosmetic.get('category', 'cosmetic')})", value=cosmetic_id))
        return choices[:25]
