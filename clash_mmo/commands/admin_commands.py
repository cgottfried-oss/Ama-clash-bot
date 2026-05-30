from __future__ import annotations

from datetime import datetime
import json
import time

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.pve.chests import CHEST_CONFIG
from clash_mmo.game.heroes import normalize_hero_loadouts, unlock_hero
from clash_mmo.game.heroes import unlocked_hero_ids_for_town_hall
from clash_mmo.game.state import load_mmo_state, update_mmo_state


RESOURCE_FIELDS = {
    "gold",
    "elixir",
    "dark_elixir",
    "gems",
    "raid_medals",
    "clan_xp",
    "shiny_ore",
    "glowy_ore",
    "starry_ore",
    "daily_streak",
    "town_hall",
}

SHOP_ITEM_FIELDS = {
    "training_potion",
    "resource_potion",
    "builder_potion",
    "guard_shield",
    "builder_crate",
    "raid_medal_pack",
    "hero_tome",
    "dark_elixir_flask",
    "ore_pouch",
    "chest_key",
}

BOOST_FIELDS = {
    "training_potion",
    "resource_potion",
}


def _parse_admin_value(value: str):
    raw = str(value).strip()

    if raw.lower() in {"true", "yes", "on"}:
        return True
    if raw.lower() in {"false", "no", "off"}:
        return False
    if raw.lower() in {"none", "null"}:
        return None

    try:
        return int(raw)
    except ValueError:
        pass

    try:
        return float(raw)
    except ValueError:
        pass

    if (raw.startswith("{") and raw.endswith("}")) or (raw.startswith("[") and raw.endswith("]")):
        try:
            return json.loads(raw)
        except Exception:
            return raw

    return raw


def _set_nested_value(root: dict, path: str, value):
    parts = [part.strip() for part in str(path).split(".") if part.strip()]
    if not parts:
        raise ValueError("Empty path")

    current = root
    for part in parts[:-1]:
        if not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value


def _add_or_set_count(container: dict, key: str, amount: int, mode: str = "set"):
    amount = int(amount)
    current = int(container.get(key, 0) or 0)

    if mode == "add":
        container[key] = max(0, current + amount)
    else:
        container[key] = max(0, amount)

    if container[key] <= 0:
        container.pop(key, None)

    return container.get(key, 0)


def _grant_gear(profile: dict, item_id: str, quantity: int = 1, *, slot: str = "admin", rarity: str = "admin"):
    inventory = profile.setdefault("inventory", {})
    items = inventory.setdefault("items", [])

    quantity = max(0, int(quantity))
    item_id = str(item_id).strip().lower()
    if not item_id or quantity <= 0:
        return 0

    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).lower() == item_id:
            item["quantity"] = int(item.get("quantity", 1) or 1) + quantity
            item.setdefault("slot", slot)
            item.setdefault("rarity", rarity)
            item.setdefault("source", "admin")
            return int(item["quantity"])

    items.append(
        {
            "item_id": item_id,
            "quantity": quantity,
            "slot": slot,
            "rarity": rarity,
            "source": "admin",
        }
    )
    return quantity


def _ensure_mmo_profile(state: dict, user_id: str, display_name: str) -> dict:
    if not isinstance(state, dict):
        state = {}

    profile = ensure_player_profile(state, user_id, display_name)

    for field in RESOURCE_FIELDS:
        if field == "town_hall":
            profile.setdefault(field, 1)
        else:
            profile.setdefault(field, 0)

    profile.setdefault("cooldowns", {})
    profile.setdefault("boosts", {})
    profile.setdefault("stats", {})
    profile.setdefault("achievements", [])
    profile.setdefault("inventory", {})
    profile.setdefault("heroes", {})
    profile.setdefault("shop_inventory", {})
    profile.setdefault("pvp", {})

    identity = profile.setdefault("identity", {})
    identity["display_name"] = display_name
    profile["name"] = display_name

    return profile


def register_admin_commands(bot, ctx):
    SHOP_ITEMS = ctx.SHOP_ITEMS

    def _unlock_heroes_for_town_hall(profile: dict, town_hall: int):
        unlocked = []
        hero_ids = unlocked_hero_ids_for_town_hall(town_hall)

        for hero_id in hero_ids:
            unlock_hero(profile, hero_id)
            unlocked.append(hero_id)

        heroes = normalize_hero_loadouts(profile)

        if unlocked and not profile.get("active_hero"):
            profile["active_hero"] = unlocked[0]

        if profile.get("active_hero") not in heroes and unlocked:
            profile["active_hero"] = unlocked[0]

        return unlocked

    def _is_owner(interaction: discord.Interaction) -> bool:
        return int(interaction.user.id) == int(getattr(ctx, "MMO_OWNER_ID", 0) or 0)

    @bot.tree.command(name="adminview", description="Owner: privately view a member's complete MMO profile")
    @app_commands.describe(member="Member to inspect")
    async def adminview(interaction: discord.Interaction, member: discord.Member):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        user_id = str(member.id)
        display_name = getattr(member, "display_name", member.name)

        def _update(state):
            _ensure_mmo_profile(state, user_id, display_name)
            return state

        await update_mmo_state(ctx, _update)

        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(user_id, {})

        shop_inventory = profile.get("shop_inventory", {})
        if not isinstance(shop_inventory, dict):
            shop_inventory = {}

        inventory = profile.get("inventory", {})
        if not isinstance(inventory, dict):
            inventory = {}

        owned_gear = inventory.get("items", [])
        if not isinstance(owned_gear, list):
            owned_gear = []

        cooldowns = profile.get("cooldowns", {}) if isinstance(profile.get("cooldowns"), dict) else {}
        boosts = profile.get("boosts", {}) if isinstance(profile.get("boosts"), dict) else {}
        stats = profile.get("stats", {}) if isinstance(profile.get("stats"), dict) else {}
        achievements = profile.get("achievements", []) if isinstance(profile.get("achievements"), list) else []
        heroes = profile.get("heroes", {}) if isinstance(profile.get("heroes"), dict) else {}
        pvp = profile.get("pvp", {}) if isinstance(profile.get("pvp"), dict) else {}

        shop_inventory_lines = []
        for item_key, qty in sorted(shop_inventory.items()):
            item_name = SHOP_ITEMS.get(item_key, {}).get("name", item_key)
            shop_inventory_lines.append(f"**{item_name}** (`{item_key}`): x{int(qty or 0)}")
        if not shop_inventory_lines:
            shop_inventory_lines = ["No shop items."]

        gear_lines = []
        grouped_gear = {}
        for item in owned_gear:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("item_id", "unknown"))
            grouped_gear.setdefault(
                item_id,
                {
                    "count": 0,
                    "slot": item.get("slot", "unknown"),
                    "rarity": item.get("rarity", "common"),
                },
            )
            grouped_gear[item_id]["count"] += int(item.get("quantity", 1) or 1)

        for item_id, data in sorted(grouped_gear.items()):
            gear_lines.append(
                f"**{item_id}** — {str(data['rarity']).title()} {str(data['slot']).title()} x{data['count']}"
            )
        if not gear_lines:
            gear_lines = ["No MMO gear owned."]

        cooldown_lines = []
        for key, value in sorted(cooldowns.items()):
            try:
                timestamp = int(value or 0)
                if timestamp <= 0:
                    cooldown_lines.append(f"`{key}`: cleared")
                else:
                    cooldown_lines.append(
                        f"`{key}`: {discord.utils.format_dt(datetime.fromtimestamp(timestamp), style='R')}"
                    )
            except Exception:
                cooldown_lines.append(f"`{key}`: {value}")
        if not cooldown_lines:
            cooldown_lines = ["No cooldowns recorded."]

        boost_lines = [f"`{key}`: {int(value or 0)} charge(s)" for key, value in sorted(boosts.items())] or ["No boost charges."]
        stat_lines = [f"`{key}`: {value}" for key, value in sorted(stats.items())] or ["No stats recorded."]

        hero_lines = []
        for hero_id, hero_data in sorted(heroes.items()):
            if not isinstance(hero_data, dict):
                hero_lines.append(f"**{hero_id}** — legacy value: `{hero_data}`")
                continue

            level = int(hero_data.get("level", 1) or 1)
            xp = int(hero_data.get("xp", 0) or 0)
            equipped_ability = hero_data.get("equipped_ability") or "None"
            equipment = hero_data.get("equipment", {})
            equipment_count = len(equipment) if isinstance(equipment, dict) else 0
            active_marker = " ⭐" if profile.get("active_hero") == hero_id else ""

            hero_lines.append(
                f"**{hero_id.replace('_', ' ').title()}**{active_marker} — "
                f"Lv {level}, XP {xp:,}, Ability: `{equipped_ability}`, Gear Equipped: {equipment_count}"
            )
        if not hero_lines:
            hero_lines = ["No heroes unlocked."]

        embed = discord.Embed(
            title=f"🛠️ GM View: {member.display_name}",
            color=0xE67E22,
        )

        embed.add_field(
            name="Resources",
            value=(
                f"Gold: **{int(profile.get('gold', 0) or 0):,}**\n"
                f"Elixir: **{int(profile.get('elixir', 0) or 0):,}**\n"
                f"Dark Elixir: **{int(profile.get('dark_elixir', 0) or 0):,}**\n"
                f"Gems: **{int(profile.get('gems', 0) or 0):,}**\n"
                f"Raid Medals: **{int(profile.get('raid_medals', 0) or 0):,}**\n"
                f"Clan XP: **{int(profile.get('clan_xp', 0) or 0):,}**\n"
                f"Shiny Ore: **{int(profile.get('shiny_ore', 0) or 0):,}**\n"
                f"Glowy Ore: **{int(profile.get('glowy_ore', 0) or 0):,}**\n"
                f"Starry Ore: **{int(profile.get('starry_ore', 0) or 0):,}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="Account",
            value=(
                f"Town Hall: **TH{int(profile.get('town_hall', 1) or 1)}**\n"
                f"Daily Streak: **{int(profile.get('daily_streak', 0) or 0)}**\n"
                f"Active Hero: **{str(profile.get('active_hero') or 'None').replace('_', ' ').title()}**\n"
                f"PvP Keys: **{len(pvp)}**"
            ),
            inline=False,
        )

        embed.add_field(name="Heroes", value="\n".join(hero_lines[:10]), inline=False)
        embed.add_field(name="Gear", value="\n".join(gear_lines[:15]), inline=False)
        embed.add_field(name="Shop Inventory", value="\n".join(shop_inventory_lines[:20]), inline=False)
        embed.add_field(name="Boosts", value="\n".join(boost_lines[:10]), inline=False)
        embed.add_field(name="Cooldowns", value="\n".join(cooldown_lines[:10]), inline=False)
        embed.add_field(name="Stats", value="\n".join(stat_lines[:15]), inline=False)
        embed.add_field(name="Achievements", value=f"{len(achievements)} unlocked", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="adminreset", description="Owner: wipe a player's Clash MMO data from mmo_state.json")
    @app_commands.describe(
        user="Discord user whose MMO data should be wiped",
        wipe_mmo="Wipe MMO profile, heroes, gear, PvP, raids, and state profile",
    )
    async def adminreset(
        interaction: discord.Interaction,
        user: discord.User,
        wipe_mmo: bool = True,
    ):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        target_id = str(user.id)

        if not wipe_mmo:
            await interaction.response.send_message("Nothing was wiped.", ephemeral=True)
            return

        def _wipe_mmo(state):
            if not isinstance(state, dict):
                state = {}

            players = state.setdefault("players", {})
            players.pop(target_id, None)

            raids = state.setdefault("raids", {})
            active_raid = raids.get("active_raid")

            if isinstance(active_raid, dict):
                players_list = active_raid.get("players", [])
                if isinstance(players_list, list):
                    active_raid["players"] = [player_id for player_id in players_list if str(player_id) != target_id]

                damage = active_raid.get("damage", {})
                if isinstance(damage, dict):
                    damage.pop(target_id, None)

                mechanics = active_raid.get("mechanics", {})
                if isinstance(mechanics, dict):
                    mechanics.pop(target_id, None)

            return state

        await update_mmo_state(ctx, _wipe_mmo)

        await interaction.response.send_message(
            f"✅ Wiped MMO data for {user.mention} from `mmo_state.json`.",
            ephemeral=True,
        )

    @bot.tree.command(name="adminclearcooldowns", description="Owner: clear a member's Clash MMO cooldowns")
    @app_commands.describe(member="Member whose cooldowns should be cleared. Defaults to you.")
    async def adminclearcooldowns(interaction: discord.Interaction, member: discord.Member | None = None):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        target = member or interaction.user
        user_id = str(target.id)
        display_name = getattr(target, "display_name", getattr(target, "name", "Unknown"))

        def _clear_mmo_cooldowns(state):
            profile = _ensure_mmo_profile(state, user_id, display_name)
            profile["cooldowns"] = {}

            pvp = profile.setdefault("pvp", {})
            pvp.pop("last_raiduser", None)

            raids = state.setdefault("raids", {})
            active_raid = raids.get("active_raid")

            if isinstance(active_raid, dict):
                mechanics = active_raid.get("mechanics", {})
                if isinstance(mechanics, dict):
                    mechanics.pop(user_id, None)

            return state

        await update_mmo_state(ctx, _clear_mmo_cooldowns)

        await interaction.response.send_message(
            f"✅ Cleared MMO cooldowns for {target.mention}.",
            ephemeral=True,
        )

    @bot.tree.command(name="admingiveall", description="Owner: give yourself or a member any resource, item, or gear")
    @app_commands.describe(
        kind="What to grant: resource, item, or gear",
        name="Resource field, shop item id, or gear item id",
        amount="Amount to grant (default 1)",
        member="Member to grant to. Defaults to you.",
    )
    @app_commands.choices(kind=[
        app_commands.Choice(name="resource (gold, elixir, ore, etc)", value="resource"),
        app_commands.Choice(name="item (shop/consumable)", value="item"),
        app_commands.Choice(name="gear (equipment)", value="gear"),
    ])
    async def admingiveall(
        interaction: discord.Interaction,
        kind: app_commands.Choice[str],
        name: str,
        amount: int = 1,
        member: discord.Member | None = None,
    ):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        target = member or interaction.user
        user_id = str(target.id)
        display_name = getattr(target, "display_name", target.name)
        kind_value = kind.value
        key = str(name).strip().lower()
        amount = int(amount)
        result_msg = {"text": ""}

        def _update(state):
            profile = _ensure_mmo_profile(state, user_id, display_name)

            if kind_value == "resource":
                if key not in RESOURCE_FIELDS:
                    result_msg["text"] = (
                        f"❌ `{key}` is not a valid resource. Valid: {', '.join(sorted(RESOURCE_FIELDS))}"
                    )
                    return state
                current = int(profile.get(key, 0) or 0)
                profile[key] = max(0, current + amount)
                result_msg["text"] = f"✅ {target.mention}: **{key}** {current:,} → **{profile[key]:,}**"

            elif kind_value == "item":
                inventory = profile.setdefault("inventory", {})
                items = inventory.setdefault("items", [])
                qty = max(1, amount)
                for it in items:
                    if isinstance(it, dict) and str(it.get("item_id", "")).lower() == key:
                        it["quantity"] = int(it.get("quantity", 1) or 1) + qty
                        result_msg["text"] = f"✅ {target.mention}: item `{key}` stack now **x{it['quantity']}**"
                        return state
                items.append({"item_id": key, "quantity": qty, "source": "admin_give"})
                result_msg["text"] = f"✅ {target.mention}: granted item `{key}` x{qty}"

            elif kind_value == "gear":
                final_qty = _grant_gear(profile, key, max(1, amount))
                result_msg["text"] = f"✅ {target.mention}: gear `{key}` stack now **x{final_qty}**"

            return state

        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(
            result_msg["text"] or "Nothing granted.",
            ephemeral=True,
        )

    @admingiveall.autocomplete("name")
    async def admingiveall_name_autocomplete(interaction: discord.Interaction, current: str):
        # The valid options depend on which `kind` the user already picked.
        # interaction.namespace exposes the other option values mid-typing.
        current = str(current or "").lower()
        selected_kind = getattr(interaction.namespace, "kind", None)

        if selected_kind == "resource":
            pool = sorted(RESOURCE_FIELDS)
        elif selected_kind == "item":
            # shop items + chests are both grantable as "item"
            pool = sorted(SHOP_ITEM_FIELDS | set(CHEST_CONFIG.keys()))
        elif selected_kind == "gear":
            pool = sorted(GEAR_CATALOG.keys())
        else:
            # kind not chosen yet — show a small mixed hint set
            pool = sorted(RESOURCE_FIELDS) + sorted(CHEST_CONFIG.keys())

        matches = [item for item in pool if current in item.lower()]

        return [
            app_commands.Choice(name=item, value=item)
            for item in matches[:25]
        ]
