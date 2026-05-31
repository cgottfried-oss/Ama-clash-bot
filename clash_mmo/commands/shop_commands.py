from __future__ import annotations

import random
import time

import discord
from shared.interactions import safe_respond
from discord import app_commands
from clash_mmo.game.state import load_mmo_state, update_mmo_state


BUILDER_POTION_COOLDOWN = 30 * 60


def _format_remaining(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def register_shop_commands(bot, ctx):
    shop_items = ctx.SHOP_ITEMS


    async def _get_shop_inventory_text(user_id: str) -> str:
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        inventory = profile.get("shop_inventory", {}) if isinstance(profile, dict) else {}
        if not isinstance(inventory, dict) or not inventory:
            return "Empty"
        lines = []
        for item_key, qty in sorted(inventory.items()):
            qty = _safe_int(qty, 0)
            if qty <= 0:
                continue
            item_name = shop_items.get(item_key, {}).get("name", item_key)
            lines.append(f"**{item_name}** (`{item_key}`): x{qty}")
        return "\n".join(lines) if lines else "Empty"

    async def _get_shop_inventory(user_id: str) -> dict:
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        inventory = profile.get("shop_inventory", {}) if isinstance(profile, dict) else {}
        return inventory if isinstance(inventory, dict) else {}

    async def _add_shop_item(user_id: str, item_key: str, quantity: int = 1, display_name: str = "Unknown") -> None:
        def _update(state):
            if not isinstance(state, dict):
                state = {}
            players = state.setdefault("players", {})
            profile = players.setdefault(str(user_id), {})
            profile.setdefault("name", display_name)
            inventory = profile.setdefault("shop_inventory", {})
            inventory[item_key] = max(0, _safe_int(inventory.get(item_key), 0) + int(quantity))
            return state
        await update_mmo_state(ctx, _update)

    async def _consume_shop_item(user_id: str, item_key: str) -> bool:
        consumed = False
        def _update(state):
            nonlocal consumed
            if not isinstance(state, dict):
                state = {}
            players = state.setdefault("players", {})
            profile = players.setdefault(str(user_id), {})
            inventory = profile.setdefault("shop_inventory", {})
            qty = _safe_int(inventory.get(item_key), 0)
            if qty <= 0:
                return state
            if qty == 1:
                inventory.pop(item_key, None)
            else:
                inventory[item_key] = qty - 1
            consumed = True
            return state
        await update_mmo_state(ctx, _update)
        return consumed

    async def _grant_resources(user: discord.Member | discord.User, *, gold=0, elixir=0, dark_elixir=0, gems=0, raid_medals=0, clan_xp=0, shiny_ore=0, glowy_ore=0, starry_ore=0):
        user_id = str(user.id)
        display_name = getattr(user, "display_name", None) or getattr(user, "name", "Unknown")

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            players = state.setdefault("players", {})
            profile = players.setdefault(user_id, {})
            profile.setdefault("name", display_name)

            identity = profile.setdefault("identity", {})
            identity["display_name"] = display_name

            profile["gold"] = max(0, _safe_int(profile.get("gold")) + int(gold))
            profile["elixir"] = max(0, _safe_int(profile.get("elixir")) + int(elixir))
            profile["dark_elixir"] = max(0, _safe_int(profile.get("dark_elixir")) + int(dark_elixir))
            profile["gems"] = max(0, _safe_int(profile.get("gems")) + int(gems))
            profile["raid_medals"] = max(0, _safe_int(profile.get("raid_medals")) + int(raid_medals))
            profile["clan_xp"] = max(0, _safe_int(profile.get("clan_xp")) + int(clan_xp))
            profile["shiny_ore"] = max(0, _safe_int(profile.get("shiny_ore")) + int(shiny_ore))
            profile["glowy_ore"] = max(0, _safe_int(profile.get("glowy_ore")) + int(glowy_ore))
            profile["starry_ore"] = max(0, _safe_int(profile.get("starry_ore")) + int(starry_ore))

            stats = profile.setdefault("stats", {})
            if gold > 0:
                stats["lifetime_gold"] = _safe_int(stats.get("lifetime_gold")) + int(gold)
            stats["shop_items_used"] = _safe_int(stats.get("shop_items_used")) + 1

            return state

        await update_mmo_state(ctx, _update)

    async def _get_user_profile(user: discord.Member | discord.User) -> dict:
        state = await load_mmo_state(ctx)
        return state.get("players", {}).get(str(user.id), {})

    @bot.tree.command(name="shop", description="View the Gold shop")
    async def shop(interaction: discord.Interaction):
        await interaction.response.defer()
        lines = []

        for item_key, item in shop_items.items():
            required_th = item.get("required_th")
            unlock_text = f"\nUnlocks at: **TH{required_th}**" if required_th else ""
            lines.append(
                f"**{item_key}** — {item['name']}\n"
                f"Cost: **{int(item['cost']):,} Gold**{unlock_text}\n"
                f"{item['description']}"
            )

        embed = discord.Embed(
            title="🛒 Gold Shop",
            description="\n\n".join(lines),
            color=0x9B59B6,
        )

        await safe_respond(interaction, embed=embed, ephemeral=True)

    @bot.tree.command(name="buy", description="Buy an item from the Gold shop")
    @app_commands.describe(item="The item key to buy")
    async def buy(interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        item = item.strip().lower()

        if item not in shop_items:
            await safe_respond(interaction, 
                "❌ Invalid item. Use `/shop` to view available items.",
                ephemeral=True,
            )
            return

        shop_item = shop_items[item]
        cost = int(shop_item["cost"])

        profile = await _get_user_profile(interaction.user)
        required_th = _safe_int(shop_item.get("required_th"), 0)
        user_th = _safe_int(profile.get("town_hall"), 1)

        if required_th and user_th < required_th:
            await safe_respond(interaction, 
                f"🔒 **{shop_item['name']}** unlocks at Town Hall **{required_th}**.\n"
                f"Your current Town Hall: **{user_th}**.",
                ephemeral=True,
            )
            return

        spend_result = {"ok": False, "balance": 0}

        def _spend_mmo_gold(state):
            if not isinstance(state, dict):
                state = {}

            players = state.setdefault("players", {})
            profile = players.setdefault(str(interaction.user.id), {})
            profile.setdefault("name", getattr(interaction.user, "display_name", interaction.user.name))

            current_gold = _safe_int(profile.get("gold"), 0)
            spend_result["balance"] = current_gold

            if current_gold < cost:
                return state

            profile["gold"] = current_gold - cost
            spend_result["balance"] = profile["gold"]
            spend_result["ok"] = True

            return state

        await update_mmo_state(ctx, _spend_mmo_gold)

        if not spend_result["ok"]:
            await safe_respond(interaction, 
                f"❌ You need **{cost:,} Gold** to buy **{shop_item['name']}**.",
                ephemeral=True,
            )
            return

        await _add_shop_item(str(interaction.user.id), item, 1, getattr(interaction.user, "display_name", interaction.user.name))
        inventory_text = await _get_shop_inventory_text(str(interaction.user.id))

        embed = discord.Embed(
            title="✅ Purchase Successful",
            description=(
                f"You bought **{shop_item['name']}** for **{cost:,} Gold**.\n\n"
                f"**New Gold:** {spend_result['balance']:,} Gold"
            ),
            color=0x2ECC71,
        )
        embed.add_field(name="Inventory", value=inventory_text, inline=False)

        await safe_respond(interaction, embed=embed, ephemeral=True)

    @buy.autocomplete("item")
    async def buy_item_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        current = current.lower()
        choices = []

        for item_key, item in shop_items.items():
            if current in item_key.lower() or current in item["name"].lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{item['name']} ({item_key}) - {int(item['cost']):,} Gold",
                        value=item_key,
                    )
                )

        return choices[:25]

    @bot.tree.command(name="inventory", description="View your purchased shop items")
    async def inventory(interaction: discord.Interaction):
        await interaction.response.defer()
        inventory_text = await _get_shop_inventory_text(str(interaction.user.id))

        embed = discord.Embed(
            title="🎒 Your Inventory",
            description=inventory_text,
            color=0x3498DB,
        )

        await safe_respond(interaction, embed=embed, ephemeral=True)

    @bot.tree.command(name="useitem", description="Use or activate an item from your inventory")
    @app_commands.describe(item="The item key to use")
    async def useitem(interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        item = item.strip().lower()

        if item not in shop_items:
            await safe_respond(interaction, 
                "❌ Invalid item. Use `/inventory` to see what you own.",
                ephemeral=True,
            )
            return

        shop_item = shop_items[item]
        item_type = str(shop_item.get("type") or "").strip().lower()

        inventory_data = await _get_shop_inventory(str(interaction.user.id))
        owned = _safe_int(inventory_data.get(item), 0)

        if owned <= 0:
            await safe_respond(interaction, 
                f"❌ You do not own **{shop_item['name']}** yet. Buy it with `/buy {item}`.",
                ephemeral=True,
            )
            return

        profile = await _get_user_profile(interaction.user)
        required_th = _safe_int(shop_item.get("required_th"), 0)
        user_th = _safe_int(profile.get("town_hall"), 1)

        if required_th and user_th < required_th:
            await safe_respond(interaction, 
                f"🔒 **{shop_item['name']}** requires Town Hall **{required_th}**.\n"
                f"Your current Town Hall: **{user_th}**.",
                ephemeral=True,
            )
            return

        if item == "builder_potion" or item_type == "cooldown_clear":
            cooldowns = profile.get("cooldowns", {}) if isinstance(profile, dict) else {}
            last_builder_potion = _safe_int(cooldowns.get("builder_potion"), 0)
            use_cooldown = _safe_int(shop_item.get("use_cooldown_seconds"), BUILDER_POTION_COOLDOWN)
            remaining = use_cooldown - (int(time.time()) - last_builder_potion)

            if remaining > 0:
                await safe_respond(interaction, 
                    f"⏳ Builder Potion can only be used once every {_format_remaining(use_cooldown)}.\n"
                    f"Try again in **{_format_remaining(remaining)}**.",
                    ephemeral=True,
                )
                return

            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, 
                    f"❌ You do not have a **{shop_item['name']}** available.",
                    ephemeral=True,
                )
                return

            def _clear_raid_cooldowns(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                profile.setdefault("name", getattr(interaction.user, "display_name", interaction.user.name))

                cooldowns_data = profile.setdefault("cooldowns", {})
                cooldowns_data.pop("raidvillage", None)
                cooldowns_data.pop("raid_village", None)
                cooldowns_data.pop("raid", None)
                cooldowns_data.pop("pve", None)
                cooldowns_data.pop("farm", None)
                cooldowns_data.pop("train", None)
                cooldowns_data.pop("attackraid", None)
                cooldowns_data.pop("raid_attack", None)
                cooldowns_data["builder_potion"] = int(time.time())

                pvp = profile.setdefault("pvp", {})
                pvp.pop("last_raiduser", None)

                return state

            await update_mmo_state(ctx, _clear_raid_cooldowns)

            await safe_respond(interaction, 
                "🧪 **Builder Potion used!** Your `/farm`, `/train`, `/pve`, `/raidvillage`, `/raiduser`, and `/attackraid` cooldowns have been cleared.",
                ephemeral=True,
            )
            return

        if item == "guard_shield" or item_type == "raiduser_defense":
            await safe_respond(interaction, 
                "🛡️ **Guard Shield is passive.** Keep it in your inventory and it will automatically block the next successful `/raiduser` attack against your village.",
                ephemeral=True,
            )
            return

        if item_type == "progression_bundle":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            gold = _safe_int(shop_item.get("gold"), 0)
            clan_xp = _safe_int(shop_item.get("clan_xp"), 0)
            await _grant_resources(interaction.user, gold=gold, clan_xp=clan_xp)
            await safe_respond(interaction, 
                f"📦 **{shop_item['name']} opened!** You gained **{gold:,} Gold** and **{clan_xp:,} Clan XP**.",
                ephemeral=True,
            )
            return

        if item_type == "raid_medals":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            medals = _safe_int(shop_item.get("raid_medals"), 0)
            await _grant_resources(interaction.user, raid_medals=medals)
            await safe_respond(interaction, 
                f"🎖️ **{shop_item['name']} used!** You gained **{medals:,} Raid Medals**.",
                ephemeral=True,
            )
            return

        if item_type == "dark_elixir":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            dark_elixir = _safe_int(shop_item.get("dark_elixir"), 0)
            await _grant_resources(interaction.user, dark_elixir=dark_elixir)
            await safe_respond(interaction, 
                f"🛢️ **{shop_item['name']} used!** You gained **{dark_elixir:,} Dark Elixir**.",
                ephemeral=True,
            )
            return

        if item_type == "ore_bundle":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            shiny_min = _safe_int(shop_item.get("shiny_ore_min"), 0)
            shiny_max = _safe_int(shop_item.get("shiny_ore_max"), shiny_min)
            if shiny_max < shiny_min:
                shiny_max = shiny_min
            shiny_ore = random.randint(shiny_min, shiny_max)
            glowy_ore = _safe_int(shop_item.get("glowy_ore_amount"), 0) if random.random() < float(shop_item.get("glowy_ore_chance", 0) or 0) else 0

            await _grant_resources(interaction.user, shiny_ore=shiny_ore, glowy_ore=glowy_ore)
            extra = f" and **{glowy_ore:,} Glowy Ore**" if glowy_ore else ""
            await safe_respond(interaction, 
                f"⛏️ **{shop_item['name']} opened!** You gained **{shiny_ore:,} Shiny Ore**{extra}.",
                ephemeral=True,
            )
            return

        if item_type == "hero_xp":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            hero_xp = _safe_int(shop_item.get("hero_xp"), 0)
            result = {"hero": None, "xp": hero_xp}

            def _grant_hero_xp(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                active_hero = str(profile.get("active_hero") or "").strip().lower()
                heroes = profile.setdefault("heroes", {})

                if not active_hero:
                    result["hero"] = None
                    return state

                hero = heroes.setdefault(active_hero, {"level": 1, "xp": 0})
                hero["xp"] = _safe_int(hero.get("xp"), 0) + hero_xp
                result["hero"] = active_hero
                return state

            await update_mmo_state(ctx, _grant_hero_xp)

            if not result["hero"]:
                # Refund the item if there is no active hero.
                await _add_shop_item(str(interaction.user.id), item, 1, getattr(interaction.user, "display_name", interaction.user.name))
                await safe_respond(interaction, 
                    "❌ You need an active hero before using a Hero Tome. Your item was refunded.",
                    ephemeral=True,
                )
                return

            await safe_respond(interaction, 
                f"📖 **{shop_item['name']} used!** Your active hero **{str(result['hero']).replace('_', ' ').title()}** gained **{hero_xp:,} XP**.",
                ephemeral=True,
            )
            return

        if item_type == "chest_key":
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            def _grant_chest_key(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                inventory = profile.setdefault("inventory", {})
                inventory["chest_keys"] = _safe_int(inventory.get("chest_keys"), 0) + 1
                return state

            await update_mmo_state(ctx, _grant_chest_key)
            await safe_respond(interaction, 
                "🗝️ **Chest Key used!** You gained **1 bonus chest key**.",
                ephemeral=True,
            )
            return

        if item_type in {"combat_boost_charges", "farm_boost_charges"}:
            if not await _consume_shop_item(str(interaction.user.id), item):
                await safe_respond(interaction, f"❌ You do not have **{shop_item['name']}** available.", ephemeral=True)
                return

            charges = max(1, _safe_int(shop_item.get("charges"), 1))
            boost_key = "training_potion" if item_type == "combat_boost_charges" else "resource_potion"
            stored = {"total": 0}

            def _activate_boost(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                boosts = profile.setdefault("boosts", {})
                # Cap total stored charges at 2 per potion type.
                new_total = min(2, _safe_int(boosts.get(boost_key), 0) + charges)
                boosts[boost_key] = new_total
                stored["total"] = new_total
                return state

            await update_mmo_state(ctx, _activate_boost)

            target = "combat/PvE" if boost_key == "training_potion" else "farm"
            await safe_respond(interaction, 
                f"⚡ **{shop_item['name']} activated!** You now have **{stored['total']}**/2 {target} boost charge(s) stored (cap is 2).",
                ephemeral=True,
            )
            return

        await safe_respond(interaction, 
            f"ℹ️ **{shop_item['name']}** does not have an active use yet.",
            ephemeral=True,
        )

    @useitem.autocomplete("item")
    async def useitem_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        current = current.lower()
        inventory_data = await _get_shop_inventory(str(interaction.user.id))

        choices = []

        for item_key, qty in inventory_data.items():
            item_data = shop_items.get(item_key)
            if not item_data:
                continue

            if current in item_key.lower() or current in item_data["name"].lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{item_data['name']} ({item_key}) x{qty}",
                        value=item_key,
                    )
                )

        return choices[:25]
