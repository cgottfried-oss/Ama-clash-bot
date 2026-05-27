from __future__ import annotations
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from clash_mmo.game.equipment.service import normalize_hero_loadouts

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment import (
    GEAR_CATALOG,
    HERO_ABILITIES,
    equip_hero_ability,
    equip_item,
    format_gear_line,
    format_stats_block,
    get_effective_profile_stats,
    grant_equipment,
    roll_equipment_drop,
)

from clash_mmo.game.state import (
    ensure_mmo_player,
    load_mmo_state,
    update_mmo_state,
)

LOOTGEAR_COOLDOWN_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _format_remaining(delta: timedelta) -> str:
    total_seconds = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes}m"
    return "less than 1m"

def register_gear_commands(bot, ctx):
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

    @bot.tree.command(name="gear", description="View your heroes and equipped gear")
    async def gear(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        heroes = normalize_hero_loadouts(profile)
        active_hero = profile.get("active_hero")

        embed = discord.Embed(
            title="🛡️ Hero Equipment",
            color=0xE67E22
        )

        if not heroes:
            embed.description = "No heroes unlocked."
            await interaction.response.send_message(embed=embed)
            return
            
        inventory = profile.setdefault("inventory", {})
        owned_items = inventory.setdefault("items", [])

        if owned_items:
            grouped_items = {}

            for item in owned_items:
                item_id = str(item.get("item_id", "unknown"))

                if item_id not in grouped_items:
                    gear_data = GEAR_CATALOG.get(item_id, {})
                    grouped_items[item_id] = {
                        "count": 0,
                        "name": gear_data.get("name", item_id),
                        "rarity": item.get("rarity") or gear_data.get("rarity", "common"),
                        "slot": item.get("slot") or gear_data.get("slot", "unknown"),
                    }

                grouped_items[item_id]["count"] += 1

            owned_lines = []

            for item_id, grouped in list(grouped_items.items())[:15]:
                count_text = f" ×{grouped['count']}" if grouped["count"] > 1 else ""

                owned_lines.append(
                    f"**{grouped['name']}**{count_text} — "
                    f"{str(grouped['rarity']).title()} {str(grouped['slot']).title()}"
                )

            if len(grouped_items) > 15:
                owned_lines.append(f"...and {len(grouped_items) - 15} more item types")

            embed.add_field(
                name="Owned Gear",
                value="\n".join(owned_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="Owned Gear",
                value="No owned gear.",
                inline=False,
            )

        for hero_id, hero_data in heroes.items():
            if not isinstance(hero_data, dict):
                continue
                
            equipment = hero_data.get("equipment", {})

            hero_lines = []

            for slot in ["weapon", "armor", "relic"]:
                item = equipment.get(slot)

                if item:
                    hero_lines.append(
                        f"**{slot.title()}** — {format_gear_line(item)}"
                    )
                else:
                    hero_lines.append(
                        f"**{slot.title()}** — Empty"
                    )

            ability = hero_data.get("equipped_ability")
            hero_lines.append(
                f"**Ability** — {ability if ability else 'None Equipped'}"
            )

            title = hero_id.replace("_", " ").title()

            if hero_id == active_hero:
                title += " ⭐"

            embed.add_field(
                name=title,
                value="\n".join(hero_lines),
                inline=False,
            )

        stats = get_effective_profile_stats(profile)

        embed.add_field(
            name="Active Hero Effective Stats",
            value=format_stats_block(stats),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="lootgear", description="Roll a random gear drop once every 24 hours")
    async def lootgear(interaction: discord.Interaction):
        now = _utc_now()
        drop = None
        cooldown_remaining = None
    
        def _update(container):
            nonlocal drop, cooldown_remaining
    
            if not isinstance(container, dict):
                container = {}
    
            profile = ensure_player_profile(
                container,
                str(interaction.user.id),
                interaction.user.display_name,
            )
    
            cooldowns = profile.setdefault("cooldowns", {})
    
            last_lootgear_at = _parse_utc_timestamp(cooldowns.get("lootgear"))
    
            if last_lootgear_at is not None:
                next_available_at = last_lootgear_at + timedelta(hours=LOOTGEAR_COOLDOWN_HOURS)
    
                if now < next_available_at:
                    cooldown_remaining = next_available_at - now
                    return container
    
            drop = roll_equipment_drop()
            grant_equipment(profile, drop["item_id"])
            cooldowns["lootgear"] = now.isoformat()
    
            return container
    
        await update_mmo_state(ctx, _update)
    
        if cooldown_remaining is not None:
            await interaction.response.send_message(
                f"⏳ You already claimed your gear drop. Try again in **{_format_remaining(cooldown_remaining)}**.",
                ephemeral=True,
            )
            return
    
        if drop is None:
            await interaction.response.send_message(
                "❌ Could not roll gear right now. Try again in a moment.",
                ephemeral=True,
            )
            return
    
        await interaction.response.send_message(
            f"🎁 You found **{drop['item']['name']}** [{drop['item']['rarity'].title()}]"
        )

    @bot.tree.command(name="equipgear", description="Equip gear to a hero")
    @app_commands.describe(
        hero_id="Hero to equip the item to",
        item_id="Gear item ID"
    )
    async def equipgear(
        interaction: discord.Interaction,
        hero_id: str,
        item_id: str
    ):
        profile = await _profile(interaction.user)
        result = equip_item(
        profile,
        hero_id.strip().lower(),
        item_id.strip().lower(),
    )
        if not result["ok"]:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        def _update(container):
            if not isinstance(container, dict):
                container = {"players": {}}
            container.setdefault("players", {})[str(interaction.user.id)] = profile
            return container
        await update_mmo_state(ctx, _update)
        equipped_item = result.get("item", {})
        equipped_item_id = equipped_item.get("item_id", item_id.strip().lower())
        gear_name = GEAR_CATALOG.get(equipped_item_id, {}).get("name", equipped_item_id)

        await interaction.response.send_message(
            f"⚔️ Equipped **{gear_name}** to **{hero_id.replace('_', ' ').title()}**"
        )

    @bot.tree.command(name="equipability", description="Equip a hero ability")
    @app_commands.describe(hero_id="Hero ID", ability_id="Ability ID")
    async def equipability(interaction: discord.Interaction, hero_id: str, ability_id: str):
        profile = await _profile(interaction.user)
        town_hall = int(profile.get("town_hall", 1) or 1)

        if town_hall < 9:
            await interaction.response.send_message(
                "🧠 Hero Abilities unlock at **Town Hall 9**.",
                ephemeral=True,
            )
            return

        heroes = profile.setdefault("heroes", {})
        hero_id = hero_id.strip().lower()

        if hero_id not in heroes:
            await interaction.response.send_message("❌ You have not unlocked that hero in the MMO system.", ephemeral=True)
            return

        result = equip_hero_ability(profile, hero_id, ability_id.strip().lower())
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
        
    @equipgear.autocomplete("hero_id")
    async def equipgear_hero_autocomplete(interaction: discord.Interaction, current: str):
        profile = await _profile(interaction.user)

        heroes = profile.get("heroes", {})
        current = current.lower()

        return [
            app_commands.Choice(
                name=hero_id.replace("_", " ").title(),
                value=hero_id
            )
            for hero_id in heroes.keys()
            if current in hero_id.lower()
        ][:25]

    @equipgear.autocomplete("item_id")
    async def equipgear_item_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        profile = await _profile(interaction.user)
        inventory = profile.setdefault("inventory", {})
        owned_items = inventory.setdefault("items", [])

        current = current.lower().strip()
        choices = []

        seen = set()

        for item in owned_items:
            item_id = str(item.get("item_id", "")).strip()

            if not item_id or item_id in seen:
                continue

            seen.add(item_id)

            gear_data = GEAR_CATALOG.get(item_id, {})
            gear_name = gear_data.get("name", item_id)

            if current and current not in item_id.lower() and current not in gear_name.lower():
                continue

            choices.append(
                app_commands.Choice(
                    name=gear_name,
                    value=item_id,
                )
            )

        return choices[:25]

    @equipability.autocomplete("hero_id")
    async def hero_autocomplete(interaction: discord.Interaction, current: str):
        profile = await _profile(interaction.user)
        heroes = profile.get("heroes", {})
        current = current.lower()
        return [
            app_commands.Choice(name=hero_id.title(), value=hero_id)
            for hero_id in heroes.keys()
            if current in hero_id.lower()
        ][:25]

    @equipability.autocomplete("ability_id")
    async def ability_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=data["name"], value=ability_id) for ability_id, data in HERO_ABILITIES.items() if current in ability_id or current in data["name"].lower()][:25]
