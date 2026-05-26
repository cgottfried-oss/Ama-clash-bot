from __future__ import annotations

import discord
from discord import app_commands

from features.phase5.core.profiles import ensure_player_profile
from features.phase5.cosmetics import (
    COSMETIC_CATALOG,
    equip_owned_cosmetic,
    format_cosmetic_line,
    format_equipped_cosmetics,
    get_player_cosmetics,
    grant_cosmetic,
)


from features.phase5.state import (
    ensure_mmo_player,
    load_mmo_state,
    update_mmo_state,
)



def register_economy_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _load_profiles():
        data = await load_mmo_state(ctx)
        players = data.setdefault("players", {})
        if not isinstance(data, dict):
            data = {}
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

    @bot.tree.command(name="grantcosmetic", description="Admin tool: grant a cosmetic")
    @app_commands.describe(member="Target member", cosmetic_id="Cosmetic ID")
    async def grantcosmetic(interaction: discord.Interaction, member: discord.Member, cosmetic_id: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator only.", ephemeral=True)
            return
        cosmetic_id = cosmetic_id.strip().lower()
        if cosmetic_id not in COSMETIC_CATALOG:
            await interaction.response.send_message("❌ Invalid cosmetic ID.", ephemeral=True)
            return
        def _update(container):
            profile = ensure_player_profile(container, str(member.id), member.display_name)
            grant_cosmetic(profile, cosmetic_id)
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"🎁 Granted **{COSMETIC_CATALOG[cosmetic_id]['name']}** to {member.mention}")

    @equipcosmetic.autocomplete("cosmetic_id")
    @grantcosmetic.autocomplete("cosmetic_id")
    async def cosmetic_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=f"{data['name']} ({cosmetic_id})", value=cosmetic_id)
            for cosmetic_id, data in COSMETIC_CATALOG.items()
            if current in cosmetic_id or current in data["name"].lower()
        ][:25]