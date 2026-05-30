from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.heroes import normalize_hero_loadouts, unlock_hero
from clash_mmo.game.heroes import (
    HERO_CATALOG,
    MAX_HERO_LEVEL,
    enabled_hero_ids,
    get_hero_name,
    get_hero_unlock_th,
    get_hero_upgrade_cost,
    get_profile_hero_level,
    get_total_hero_power,
    hero_is_unlocked,
    set_active_hero,
)
from clash_mmo.game.pve.world_events import get_active_effect
from clash_mmo.game.state import load_mmo_state, update_mmo_state


def register_heroes_commands(bot, ctx):
    async def _profile(user: discord.Member | discord.User):
        user_id = str(user.id)
        display_name = getattr(user, "display_name", None) or getattr(user, "name", "Unknown")

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                user_id,
                display_name,
            )

            profile.setdefault("town_hall", 1)
            profile.setdefault("gold", 0)
            profile.setdefault("dark_elixir", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("clan_xp", 0)
            profile.setdefault("heroes", {})
            profile.setdefault("active_hero", None)

            identity = profile.setdefault("identity", {})
            identity["display_name"] = display_name

            return state

        await update_mmo_state(ctx, _update)

        state = await load_mmo_state(ctx)
        return state.get("players", {}).get(user_id, {})

    @bot.tree.command(name="heroes", description="View your hero roster")
    @app_commands.describe(member="Optional member to view")
    async def heroes(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        profile = await _profile(target)

        town_hall = int(profile.get("town_hall", 1) or 1)
        heroes_data = normalize_hero_loadouts(profile)

        unlocked_lines = []
        locked_lines = []

        for hero_id in enabled_hero_ids():
            unlock_th = get_hero_unlock_th(hero_id)
            hero_data = heroes_data.get(hero_id)

            if isinstance(hero_data, dict):
                level = int(hero_data.get("level", 1) or 1)
                active_marker = " ⭐ Active" if profile.get("active_hero") == hero_id else ""
                unlocked_lines.append(
                    f"**{get_hero_name(hero_id)}** — Lv.{level}/{MAX_HERO_LEVEL}{active_marker}"
                )
            else:
                if town_hall >= unlock_th:
                    locked_lines.append(
                        f"**{get_hero_name(hero_id)}** — Available at TH{unlock_th} but not unlocked"
                    )
                else:
                    locked_lines.append(
                        f"🔒 **{get_hero_name(hero_id)}** — Unlocks TH{unlock_th}"
                    )

        description_parts = []

        if unlocked_lines:
            description_parts.append("**Unlocked Heroes**\n" + "\n".join(unlocked_lines))

        if locked_lines:
            description_parts.append("**Locked Heroes**\n" + "\n".join(locked_lines))

        if not description_parts:
            description_parts.append("No heroes available.")

        embed = discord.Embed(
            title=f"🦸 {target.display_name}'s Heroes",
            description="\n\n".join(description_parts),
            color=0x9B59B6,
        )

        embed.add_field(
            name="Town Hall",
            value=f"TH{town_hall}",
            inline=True,
        )

        embed.add_field(
            name="Total Hero Power",
            value=str(get_total_hero_power(profile)),
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="upgradehero", description="Upgrade one of your heroes using Dark Elixir")
    @app_commands.describe(hero="Hero to upgrade")
    async def upgradehero(interaction: discord.Interaction, hero: str):
        key = str(hero or "").strip().lower()

        if key not in HERO_CATALOG:
            await interaction.response.send_message("❌ Invalid hero.", ephemeral=True)
            return

        profile = await _profile(interaction.user)
        town_hall = int(profile.get("town_hall", 1) or 1)
        unlock_th = get_hero_unlock_th(key)

        if town_hall < unlock_th:
            await interaction.response.send_message(
                f"🔒 {get_hero_name(key)} unlocks at TH{unlock_th}.",
                ephemeral=True,
            )
            return

        if not hero_is_unlocked(profile, key):
            def _unlock_update(state):
                if not isinstance(state, dict):
                    state = {}

                profile_to_update = ensure_player_profile(
                    state,
                    str(interaction.user.id),
                    interaction.user.display_name,
                )

                unlock_hero(profile_to_update, key)

                if not profile_to_update.get("active_hero"):
                    profile_to_update["active_hero"] = key

                return state

            await update_mmo_state(ctx, _unlock_update)
            profile = await _profile(interaction.user)

        current_level = get_profile_hero_level(profile, key)

        if current_level >= MAX_HERO_LEVEL:
            await interaction.response.send_message(
                f"⭐ **{get_hero_name(key)}** is already max level (Lv.{MAX_HERO_LEVEL}).",
                ephemeral=True,
            )
            return

        cost = get_hero_upgrade_cost(key, current_level)

        _event_state = await load_mmo_state(ctx)
        cost_mult = float(get_active_effect(_event_state, "hero_upgrade_cost_multiplier", 1.0) or 1.0)

        current_dark_elixir = int(profile.get("dark_elixir", 0) or 0)
        base_dark_elixir = int(cost.get("dark_elixir", 0) or 0)
        required_dark_elixir = max(0, int(round(base_dark_elixir * cost_mult)))

        if current_dark_elixir < required_dark_elixir:
            await interaction.response.send_message(
                f"❌ You need **{required_dark_elixir:,} Dark Elixir** to upgrade "
                f"{get_hero_name(key)} to Lv.{current_level + 1}.\n"
                f"You currently have **{current_dark_elixir:,} Dark Elixir**.",
                ephemeral=True,
            )
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile_to_update = ensure_player_profile(
                state,
                str(interaction.user.id),
                interaction.user.display_name,
            )

            profile_to_update["dark_elixir"] = max(
                0,
                int(profile_to_update.get("dark_elixir", 0) or 0) - required_dark_elixir,
            )

            heroes_data = normalize_hero_loadouts(profile_to_update)
            hero_data = heroes_data.setdefault(
                key,
                {
                    "level": 1,
                    "abilities": [],
                    "equipped_ability": None,
                    "equipment": {},
                },
            )

            hero_data["level"] = current_level + 1

            if not profile_to_update.get("active_hero"):
                profile_to_update["active_hero"] = key

            return state

        await update_mmo_state(ctx, _update)

        discount_note = ""
        if cost_mult < 1.0:
            saved = base_dark_elixir - required_dark_elixir
            discount_note = f"\n🎉 Trader Weekend: saved **{saved:,} Dark Elixir** ({int((1 - cost_mult) * 100)}% off)!"

        await interaction.response.send_message(
            f"🦸 **{get_hero_name(key)} upgraded to Lv.{current_level + 1}/{MAX_HERO_LEVEL}!**\n"
            f"Cost: **{required_dark_elixir:,} Dark Elixir**{discount_note}"
        )

    @upgradehero.autocomplete("hero")
    async def upgradehero_autocomplete(interaction: discord.Interaction, current: str):
        current = str(current or "").lower()

        return [
            app_commands.Choice(
                name=f"{get_hero_name(hero_id)} ({hero_id})",
                value=hero_id,
            )
            for hero_id in enabled_hero_ids()
            if current in hero_id or current in get_hero_name(hero_id).lower()
        ][:25]

    @bot.tree.command(name="setactivehero", description="Set your active hero for stats and gear drops")
    @app_commands.describe(hero="Hero to make active")
    async def setactivehero_command(interaction: discord.Interaction, hero: str):
        key = str(hero or "").strip().lower()

        if key not in HERO_CATALOG:
            await interaction.response.send_message("❌ Invalid hero.", ephemeral=True)
            return

        profile = await _profile(interaction.user)
        result = set_active_hero(profile, key)

        if not result.get("ok"):
            await interaction.response.send_message(
                f"❌ {result.get('error', 'Could not set active hero.')}",
                ephemeral=True,
            )
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile_to_update = ensure_player_profile(
                state,
                str(interaction.user.id),
                interaction.user.display_name,
            )

            set_active_hero(profile_to_update, key)

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"⭐ Active hero set to **{get_hero_name(key)}**."
        )

    @setactivehero_command.autocomplete("hero")
    async def setactivehero_autocomplete(interaction: discord.Interaction, current: str):
        current = str(current or "").lower()

        return [
            app_commands.Choice(
                name=f"{get_hero_name(hero_id)} ({hero_id})",
                value=hero_id,
            )
            for hero_id in enabled_hero_ids()
            if current in hero_id or current in get_hero_name(hero_id).lower()
        ][:25]
