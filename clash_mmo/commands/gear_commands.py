from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment import (
    GEAR_CATALOG,
    HERO_ABILITIES,
    HERO_CATALOG,
    equip_hero_ability,
    equip_item,
    format_gear_line,
    format_hero_line,
    format_stats_block,
    get_effective_profile_stats,
    grant_equipment,
    roll_equipment_drop,
    unlock_hero,
)

from clash_mmo.game.state import (
    ensure_mmo_player,
    load_mmo_state,
    update_mmo_state,
)


def register_economy_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _profile(user: discord.Member | discord.User):
        def _update(container):
            if not isinstance(container, dict):
                container = {}
            ensure_player_profile(container, str(user.id), user.display_name)
            return container
        await update_mmo_state(ctx, _update)
        refreshed = await load_mmo_state(ctx)
        refreshed.setdefault("players", {})
        return refreshed["players"][str(user.id)]

    @bot.tree.command(name="gear", description="View your equipped gear and stats")
    async def gear(interaction: discord.Interaction):
        profile = await _profile(interaction.user)
        inventory = profile.get("inventory", {})
        equipment = inventory.get("equipment", {})
        lines = []
        for slot, item in equipment.items():
            lines.append(f"**{slot.title()}** — {format_gear_line(item)}" if item else f"**{slot.title()}** — Empty")
        stats = get_effective_profile_stats(profile)
        embed = discord.Embed(title="🛡️ Equipped Gear", description="\n".join(lines) or "No equipment slots found.", color=0xE67E22)
        embed.add_field(name="Effective Stats", value=format_stats_block(stats), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="lootgear", description="Roll a random gear drop")
    async def lootgear(interaction: discord.Interaction):
        drop = roll_equipment_drop()
        def _update(container):
            if not isinstance(container, dict):
                container = {}
            profile = ensure_player_profile(container, str(interaction.user.id), interaction.user.display_name)
            grant_equipment(profile, drop["item_id"])
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"🎁 You found **{drop['item']['name']}** [{drop['item']['rarity'].title()}]")

    @bot.tree.command(name="equipgear", description="Equip a gear item")
    @app_commands.describe(item_id="Gear item ID")
    async def equipgear(interaction: discord.Interaction, item_id: str):
        profile = await _profile(interaction.user)
        result = equip_item(profile, item_id.strip().lower())
        if not result["ok"]:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        def _update(container):
            if not isinstance(container, dict):
                container = {"players": {}}
            container.setdefault("players", {})[str(interaction.user.id)] = profile
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"⚔️ Equipped {item_id}")

    @bot.tree.command(name="heroes", description="View unlocked heroes")
    async def heroes(interaction: discord.Interaction):
        profile = await _profile(interaction.user)
        heroes = profile.get("heroes", {})
        if not heroes:
            await interaction.response.send_message("No heroes unlocked yet.", ephemeral=True)
            return
        lines = [format_hero_line(hero_id, hero_data) for hero_id, hero_data in heroes.items()]
        embed = discord.Embed(title="🦸 Hero Roster", description="\n".join(lines), color=0x9B59B6)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="unlockhero", description="Unlock a hero")
    @app_commands.describe(hero_id="Hero ID")
    async def unlockhero(interaction: discord.Interaction, hero_id: str):
        hero_id = hero_id.strip().lower()
        if hero_id not in HERO_CATALOG:
            await interaction.response.send_message("❌ Invalid hero.", ephemeral=True)
            return
        def _update(container):
            if not isinstance(container, dict):
                container = {}
            profile = ensure_player_profile(container, str(interaction.user.id), interaction.user.display_name)
            unlock_hero(profile, hero_id)
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"🦸 Unlocked {HERO_CATALOG[hero_id]['name']}")

    @bot.tree.command(name="equipability", description="Equip a hero ability")
    @app_commands.describe(hero_id="Hero ID", ability_id="Ability ID")
    async def equipability(interaction: discord.Interaction, hero_id: str, ability_id: str):
        profile = await _profile(interaction.user)
        result = equip_hero_ability(profile, hero_id.strip().lower(), ability_id.strip().lower())
        if not result["ok"]:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        def _update(container):
            if not isinstance(container, dict):
                container = {"players": {}}
            container.setdefault("players", {})[str(interaction.user.id)] = profile
            return container
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"✨ Equipped ability: {result['ability']['name']}")

    @equipgear.autocomplete("item_id")
    async def equipgear_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{gear['name']} ({item_id})", value=item_id) for item_id, gear in GEAR_CATALOG.items() if current in item_id or current in gear["name"].lower()][:25]

    @unlockhero.autocomplete("hero_id")
    async def hero_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=data["name"], value=hero_id) for hero_id, data in HERO_CATALOG.items() if current in hero_id or current in data["name"].lower()][:25]

    @equipability.autocomplete("ability_id")
    async def ability_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=data["name"], value=ability_id) for ability_id, data in HERO_ABILITIES.items() if current in ability_id or current in data["name"].lower()][:25]