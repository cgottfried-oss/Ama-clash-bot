from __future__ import annotations

import io
import traceback
from datetime import datetime

import discord
from discord import app_commands

from advisor.constants import CHECK, DEFAULT_ROLE, CATEGORY_EMOJIS
from advisor.cap_mappings import ACCOUNT_COMPLETION_CATEGORY_LABELS
from renderers.advisor_renderer import render_advisor_card_to_file


def register_advisor_commands(advisor):

    async def account_autocomplete(interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        linked_accounts = await advisor.get_linked_accounts(str(interaction.user.id))
        choices: list[app_commands.Choice[str]] = []
        for account in linked_accounts:
            label = f"{account['name']} ({account['tag']})"
            if current and current not in label.lower() and current not in account['tag'].lower():
                continue
            choices.append(app_commands.Choice(name=label[:100], value=account['tag']))
        return choices[:25]

    @advisor.tree.command(name="setrole", description="Set your upgrade advisor profile")
    @app_commands.describe(role="Choose how the advisor should prioritize your upgrades")
    @app_commands.choices(
        role=[
            app_commands.Choice(name="Attacker", value="attacker"),
            app_commands.Choice(name="Hybrid", value="hybrid"),
            app_commands.Choice(name="Farmer", value="farmer"),
        ]
    )
    async def setrole(interaction: discord.Interaction, role: app_commands.Choice[str]):
        await advisor.save_user_patch(
            str(interaction.user.id),
            lambda root, account: root.update({"role": role.value}),
        )
        root = await advisor.get_user_root(str(interaction.user.id))
        active_tag = root.get("active_player_tag")
        if active_tag:
            targets = advisor.infer_default_targets(advisor.get_account_from_root(root, active_tag).get("town_hall"), role.value)
            if targets:
                await advisor.save_user_patch(
                    str(interaction.user.id),
                    lambda root, account: account.setdefault("targets", {}).update({k: account.setdefault("targets", {}).get(k, v) for k, v in targets.items()}),
                    player_tag=active_tag,
                )
        await interaction.response.send_message(
            f"✅ Upgrade advisor role set to **{role.name}**.",
            ephemeral=True,
        )

    @advisor.tree.command(name="syncupgrades", description="Sync heroes, troops, spells, and pets from one linked Clash account")
    @app_commands.describe(account="Which linked Clash account to sync")
    async def syncupgrades(interaction: discord.Interaction, account: str | None = None):
        await interaction.response.defer(ephemeral=True)

        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        if not chosen_link:
            await interaction.followup.send("❌ You need to link a Clash account first with /link.", ephemeral=True)
            return

        before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_link["tag"])

        try:
            user = await advisor.sync_player(str(interaction.user.id), account_hint=account)
        except ValueError as exc:
            await interaction.followup.send(f"❌ {exc}", ephemeral=True)
            return
        except Exception as exc:
            import traceback
            print(f"[SYNCUPGRADES ERROR] {exc}")
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ syncupgrades failed: {type(exc).__name__}: {exc}",
                ephemeral=True,
            )
            return

        try:
            synced_count = len(user.get("synced_levels", {}))
            manual_count = len(user.get("manual_levels", {}))

            account_snap = advisor.build_account_completion_snapshot(user)
            milestone_celebration = advisor.build_milestone_celebration(before_user, user)
            reward_state = advisor.evaluate_path_rewards(before_user, user)
            if reward_state.get("coins") or reward_state.get("efficiency"):
                user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_link["tag"], reward_state)

            mode_label = advisor.resolve_advisor_mode(user, requested_mode=None).title()
            milestone_state = advisor.get_milestone_state(user)
            war_ready = "Yes" if milestone_state.get("achieved", {}).get("war_ready") else "Not yet"
            pool_snap = advisor.build_recommendation_pool_snapshot(user)
            player_name = user.get("player_name") or "Unknown"
            player_tag = user.get("player_tag") or chosen_link["tag"]
            role = str(user.get("role", DEFAULT_ROLE)).title()
            th = user.get("town_hall") or "?"
            synced_at = user.get("last_synced_at") or user.get("last_upgrade_sync")
            sync_text = "Never"
            if synced_at:
                try:
                    sync_text = discord.utils.format_dt(datetime.fromisoformat(str(synced_at)), style="R")
                except Exception:
                    sync_text = str(synced_at)

            reward_text = advisor.build_reward_result_block(reward_state)

            try:
                html_card = advisor._build_syncupgrades_card_html(
                    user,
                    synced_count=synced_count,
                    manual_count=manual_count,
                    account_snap=account_snap,
                    pool_snap=pool_snap,
                    war_ready=war_ready,
                    mode_label=mode_label,
                    milestone_celebration=milestone_celebration,
                    reward_text=reward_text,
                )

                print(
                    f"[SYNCUPGRADES_HTML] user={interaction.user.id} html_len={len(html_card or '')}",
                    flush=True,
                )
                print((html_card or "")[:1000], flush=True)
            
                file = await render_advisor_card_to_file(
                    html_card,
                    "syncupgrades.png",
                    width=1000,
                    height=1220,
                    wait_ms=1000,
                )
            
                await interaction.followup.send(file=file, ephemeral=True)
                return
            
            except Exception as exc:
                print(f"[SYNCUPGRADES CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()

            embed = discord.Embed(title=f"{CHECK} Upgrade Sync Complete", color=0x2ECC71)
            embed.description = advisor._truncate_for_embed(
                f"Account: **{player_name}** ({player_tag}) | TH **{th}** | Role: **{role}** | Mode: **{mode_label}** | Last sync: {sync_text}",
                limit=4000,
            )

            advisor._safe_followup_embed_field(
                embed,
                name="Sync snapshot",
                value=(
                    f"Auto-synced from Clash API: **{synced_count}** hero/lab/pet items\n"
                    f"Manual tracked entries: **{manual_count}**"
                ),
                inline=False,
                limit=700,
            )
            advisor._safe_followup_embed_field(
                embed,
                name="Completion snapshot",
                value=(
                    f"Account completion: **{account_snap.get('supported_complete', 0)}/{account_snap.get('supported_slots', 0)}** "
                    f"({account_snap.get('percent_complete', 0)}%)\n"
                    f"Data coverage: **{account_snap.get('supported_known', 0)}/{account_snap.get('supported_slots', 0)}** "
                    f"({account_snap.get('coverage_percent', 0)}%)"
                ),
                inline=False,
                limit=700,
            )
            advisor._safe_followup_embed_field(
                embed,
                name="Advisor snapshot",
                value=(
                    f"Top Picks: **{pool_snap.get('top_size', 0)}**\n"
                    f"Recommendation Pool: **{pool_snap.get('pool_size', 0)}**\n"
                    f"War ready: **{war_ready}**"
                ),
                inline=False,
                limit=700,
            )
            advisor._safe_followup_embed_field(
                embed,
                name="What changed",
                value=(
                    f"Milestones: {milestone_celebration}\n"
                    f"Rewards: {reward_text}"
                ),
                inline=False,
                limit=900,
            )

            embed.set_footer(text=f"Viewing account: {player_name} {player_tag}")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            import traceback
            print(f"[SYNCUPGRADES ERROR] {exc}")
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ syncupgrades failed: {type(exc).__name__}: {exc}",
                ephemeral=True,
            )


    @syncupgrades.autocomplete("account")
    async def syncupgrades_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @advisor.tree.command(name="trackupgrade", description="Track a manual item level or override a target")
    @app_commands.describe(item="Item key to track", current_level="Your current level", target_level="Optional advisor target override", account="Which linked account this should apply to", copy_count="Optional number of copies at this exact level")
    async def trackupgrade(interaction: discord.Interaction, item: str, current_level: int, target_level: int | None = None, account: str | None = None, copy_count: int | None = None):
        item = item.strip().lower()
        if item not in ITEMS:
            await interaction.response.send_message("❌ Unknown item key. Use autocomplete or a valid advisor item.", ephemeral=True)
            return
        if current_level < 0:
            await interaction.response.send_message("❌ Current level cannot be negative.", ephemeral=True)
            return
        if copy_count is not None and copy_count < 1:
            await interaction.response.send_message("❌ Copy count must be at least 1.", ephemeral=True)
            return
        if target_level is not None and target_level < current_level:
            await interaction.response.send_message("❌ Target level cannot be lower than your current level.", ephemeral=True)
            return
        if item == "wall" and copy_count is None:
            await interaction.response.send_message(
                "❌ Walls need a quantity so one wall level does not get treated like all walls. Use `/trackcopies item:wall levels_csv:18x230,17x120` or `/trackupgrade item:wall current_level:18 copy_count:230`.",
                ephemeral=True,
            )
            return

        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)

        def patch(root: dict[str, Any], account_store: dict[str, Any]):
            if chosen_tag:
                root["active_player_tag"] = chosen_tag
                account_store.setdefault("player_tag", chosen_tag)
                if chosen_link:
                    account_store.setdefault("player_name", chosen_link.get("name", "Unknown"))
            if copy_count and advisor.is_multi_copy_item(account_store.get("town_hall"), item):
                cap_count = advisor.get_item_copy_cap(account_store.get("town_hall"), item)
                applied = max(1, min(int(copy_count), cap_count))
                account_store.setdefault("manual_copy_levels", {})[item] = [int(current_level)] * applied
                account_store.setdefault("manual_levels", {}).pop(item, None)
            else:
                account_store.setdefault("manual_levels", {})[item] = int(current_level)
            if target_level is not None:
                th_for_target = account_store.get("town_hall")
                cap_target = advisor.get_th_cap_target(th_for_target, item)
                sanitized_target = int(target_level)
                if cap_target is not None:
                    sanitized_target = max(int(current_level), min(sanitized_target, cap_target))
                account_store.setdefault("targets", {})[item] = sanitized_target

        await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        reward_state = advisor.evaluate_path_rewards(before_user, user)
        if reward_state.get("coins") or reward_state.get("efficiency"):
            user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_tag, reward_state)
        effective_target = advisor.get_effective_targets(user).get(item, target_level or current_level)
        if copy_count and advisor.is_multi_copy_item(user.get("town_hall"), item):
            copy_cap = advisor.get_item_copy_cap(user.get("town_hall"), item)
            await interaction.response.send_message(
                f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{min(copy_count, copy_cap)}/{copy_cap}** copies entered at level **{current_level}** and target **{effective_target}**. Use `/trackcopies` for mixed levels.\n{advisor.build_reward_result_block(reward_state)}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** at level **{current_level}** with target **{effective_target}**.\n{advisor.build_reward_result_block(reward_state)}",
                ephemeral=True,
            )

    @trackupgrade.autocomplete("item")
    async def trackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

    @trackupgrade.autocomplete("account")
    async def trackupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @advisor.tree.command(name="untrackupgrade", description="Remove a manually tracked item or target override")
    @app_commands.describe(item="Item key to remove", account="Which linked account this should apply to")
    async def untrackupgrade(interaction: discord.Interaction, item: str, account: str | None = None):
        item = item.strip().lower()
        if item not in ITEMS:
            await interaction.response.send_message("❌ Unknown item key.", ephemeral=True)
            return

        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account

        def patch(root: dict[str, Any], account_store: dict[str, Any]):
            if chosen_tag:
                root["active_player_tag"] = chosen_tag
            account_store.setdefault("manual_levels", {}).pop(item, None)
            account_store.setdefault("manual_copy_levels", {}).pop(item, None)
            account_store.setdefault("targets", {}).pop(item, None)

        await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        await interaction.response.send_message(
            f"✅ Removed manual tracking for **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}**.",
            ephemeral=True,
        )

    @advisor.tree.command(name="trackcopies", description="Track mixed copy levels for a building or trap with multiple copies")
    @app_commands.describe(item="Multi-copy item key to track", levels_csv="Comma-separated levels like 13,13,12 or compact counts like 18x230,17x120", target_level="Optional advisor target override", account="Which linked account this should apply to")
    async def trackcopies(interaction: discord.Interaction, item: str, levels_csv: str, target_level: int | None = None, account: str | None = None):
        item = item.strip().lower()
        if item not in ITEMS:
            await interaction.response.send_message("❌ Unknown item key. Use autocomplete or a valid advisor item.", ephemeral=True)
            return

        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        before_user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        existing_user = before_user
        town_hall = existing_user.get("town_hall")
        if town_hall is None:
            await interaction.response.send_message(
                "❌ I do not know this account's Town Hall yet. Run `/syncupgrades` for that account first, then try `/trackcopies` again.",
                ephemeral=True,
            )
            return
        if not advisor.is_multi_copy_item(town_hall, item):
            label = ITEMS[item].label if item in ITEMS else item
            await interaction.response.send_message(
                f"❌ **{label}** is not configured as a multi-copy item for TH{town_hall}. Use `/trackupgrade` instead.",
                ephemeral=True,
            )
            return

        cap_count = advisor.get_item_copy_cap(existing_user.get("town_hall"), item)
        parsed, parse_errors = advisor.parse_copy_level_entries(levels_csv, require_counts=(item == "wall"))
        if parse_errors:
            await interaction.response.send_message(
                "❌ " + " ".join(parse_errors[:3]) + (" Example for walls: `18x230,17x120`." if item == "wall" else ""),
                ephemeral=True,
            )
            return
        if not parsed:
            example = "`18x230,17x120`" if item == "wall" else "`13,13,12,12` or `13x2,12x2`"
            await interaction.response.send_message(f"❌ Enter at least one copy level, like {example}.", ephemeral=True)
            return
        if len(parsed) > cap_count:
            await interaction.response.send_message(
                f"❌ You entered **{len(parsed)}** copies, but **{ITEMS[item].label}** only has **{cap_count}** copy/copies at TH{town_hall}.",
                ephemeral=True,
            )
            return

        def patch(root: dict[str, Any], account_store: dict[str, Any]):
            if chosen_tag:
                root["active_player_tag"] = chosen_tag
                account_store.setdefault("player_tag", chosen_tag)
                if chosen_link:
                    account_store.setdefault("player_name", chosen_link.get("name", "Unknown"))
            account_store.setdefault("manual_copy_levels", {})[item] = parsed
            account_store.setdefault("manual_levels", {}).pop(item, None)
            if target_level is not None:
                th_for_target = account_store.get("town_hall")
                cap_target = advisor.get_th_cap_target(th_for_target, item)
                sanitized_target = int(target_level)
                if cap_target is not None:
                    sanitized_target = min(sanitized_target, cap_target)
                if parsed:
                    sanitized_target = max(sanitized_target, max(parsed))
                account_store.setdefault("targets", {})[item] = sanitized_target

        await advisor.save_user_patch(str(interaction.user.id), patch, player_tag=chosen_tag)
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        reward_state = advisor.evaluate_path_rewards(before_user, user)
        if reward_state.get("coins") or reward_state.get("efficiency"):
            user = await advisor.apply_path_rewards(str(interaction.user.id), chosen_tag, reward_state)
        status = advisor.get_item_status(user, item)
        effective_target = advisor.get_effective_targets(user).get(item, target_level or max(parsed))
        level_summary = advisor.summarize_copy_levels(parsed)
        await interaction.response.send_message(
            f"✅ Tracking **{ITEMS[item].label}** on **{user.get('player_name', 'this account')}** with **{status.get('tracked_copies', 0)}/{status.get('copy_cap', 1)}** copies entered. Summary: **{level_summary}**. Target **{effective_target}**. At target now: **{status.get('done', 0)}/{status.get('copy_cap', 1)}**.\n{advisor.build_reward_result_block(reward_state)}",
            ephemeral=True,
        )

    @trackcopies.autocomplete("item")
    async def trackcopies_item_autocomplete(interaction: discord.Interaction, current: str):
        current = (current or "").lower()

        # Prefer the currently selected account's Town Hall when available.
        requested_account = getattr(getattr(interaction, "namespace", None), "account", None)
        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), requested_account)
        chosen_tag = chosen_link["tag"] if chosen_link else requested_account
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        town_hall = user.get("town_hall")

        seen: set[str] = set()
        choices: list[app_commands.Choice[str]] = []

        def append_choice(item_key: str, copy_count: int | None = None):
            if item_key in seen or item_key not in ITEMS:
                return
            label = ITEMS[item_key].label
            if copy_count and copy_count > 1:
                label = f"{label} ({copy_count}x)"
            choice = app_commands.Choice(name=f"{label} ({item_key})", value=item_key)
            if current and current not in choice.value.lower() and current not in choice.name.lower():
                return
            seen.add(item_key)
            choices.append(choice)

        # Resolve from TH_CAPS dynamically. If the selected TH is missing or stale, the advisor
        # will scan other Town Halls before falling back, so items like X-Bow still appear.
        for item_key in sorted(ITEMS, key=lambda k: ITEMS[k].label.lower()):
            copy_count = advisor.get_item_copy_cap(town_hall, item_key)
            if copy_count > 1:
                append_choice(item_key, copy_count)

        return choices[:25]

    @trackcopies.autocomplete("account")
    async def trackcopies_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @untrackupgrade.autocomplete("item")
    async def untrackupgrade_item_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [choice for choice in TRACKABLE_CHOICES if current in choice.value.lower() or current in choice.name.lower()][:25]

    @untrackupgrade.autocomplete("account")
    async def untrackupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @advisor.tree.command(name="nextupgrade", description="See your top recommended next upgrades")
    @app_commands.describe(count="How many recommendations to show (1-10)", account="Which linked account to view", mode="Advisor priority mode: auto uses your saved mode or role default, war prioritizes war value, farm prioritizes economy/progression flow", builder_idle="Set true if you currently have an idle builder", lab_idle="Set true if your lab is idle")
    @app_commands.choices(mode=[app_commands.Choice(name="Auto", value="auto"), app_commands.Choice(name="War", value="war"), app_commands.Choice(name="Farm", value="farm")])
    async def nextupgrade(interaction: discord.Interaction, count: int = 5, account: str | None = None, mode: str = "auto", builder_idle: bool | None = None, lab_idle: bool | None = None):
        await interaction.response.defer(ephemeral=True)
        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        if chosen_tag and user.get("player_tag") != chosen_tag:
            user["player_tag"] = chosen_tag
            if chosen_link:
                user["player_name"] = chosen_link.get("name", "Unknown")
        if not user.get("synced_levels") and not user.get("manual_levels"):
            await interaction.followup.send(
                "❌ No upgrade data found for that account yet. Run `/syncupgrades` on the account first, then optionally add manual buildings with `/trackupgrade`.",
                ephemeral=True,
            )
            return

        timing_context = advisor.get_timing_context(user, requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
        recs, pool = advisor.build_recommendation_pool(user, count=count, pool_size=max(count + 3, 8), requested_mode=mode, builder_idle=builder_idle, lab_idle=lab_idle)
        if not recs:
            await interaction.followup.send(
                "✅ You are at or above all current advisor targets for this account. Add more manual targets or raise your standards.",
                ephemeral=True,
            )
            return

        await advisor.save_active_recommendations(str(interaction.user.id), chosen_tag, recs)

        try:
            html_card = advisor.build_nextupgrade_card_html(
                user,
                recs,
                pool,
                timing_context=timing_context,
            )
            
            file = await render_advisor_card_to_file(
                html_card,
                "nextupgrade.png",
                width=1000,
                height=1600,
                wait_ms=1000,
            )

            await interaction.followup.send(file=file, ephemeral=True)
            return
            
        except Exception as exc:
            print(f"[UPGRADE ADVISOR CARD ERROR] {exc}")
            import traceback
            traceback.print_exc()

        try:
            embed = advisor._build_safe_nextupgrade_embed(user, recs, pool, timing_context=timing_context)
            embed.set_footer(text="Image card failed, so this compact advisor view is being shown instead.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as fallback_exc:
            print(f"[UPGRADE ADVISOR FALLBACK ERROR] {fallback_exc}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                "❌ Could not build the next-upgrade view right now. Try `/syncupgrades` again, then rerun `/nextupgrade`.",
                ephemeral=True,
            )

    @nextupgrade.autocomplete("account")
    async def nextupgrade_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @advisor.tree.command(name="setadvisormode", description="Save a default advisor mode for an account")
    @app_commands.describe(mode="Default advisor priority mode", account="Which linked account to update")
    @app_commands.choices(mode=[app_commands.Choice(name="Auto", value="auto"), app_commands.Choice(name="War", value="war"), app_commands.Choice(name="Farm", value="farm")])
    async def setadvisormode(interaction: discord.Interaction, mode: str, account: str | None = None):
        await interaction.response.defer(ephemeral=True)
        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)

        await advisor.save_user_patch(
            str(interaction.user.id),
            lambda root, acct: acct.__setitem__("advisor_mode", str(mode or "auto").lower()),
            player_tag=chosen_tag or user.get("player_tag"),
        )

        refreshed = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag or user.get("player_tag"))
        effective_mode = advisor.resolve_advisor_mode(refreshed, requested_mode=None)
        emoji = MODE_EMOJIS.get(str(mode).lower(), "🧠")
        player_name = refreshed.get("player_name") or user.get("player_name") or "Unknown"

        embed = discord.Embed(title=f"{emoji} Advisor Mode Saved", color=0x2ECC71)
        embed.description = f"Default mode for **{player_name}** is now set to **{str(mode).title()}**."
        advisor._safe_followup_embed_field(
            embed,
            name="How to use it",
            value=(
                "Your saved mode will now be used by `/nextupgrade` and `/upgradeprogress` when you leave the mode option on Auto.\n"
                "You can still override it per command by passing `mode: war` or `mode: farm`."
            ),
            inline=False,
            limit=900,
        )
        advisor._safe_followup_embed_field(
            embed,
            name="Effective behavior",
            value=f"Current effective mode: **{effective_mode.title()}**",
            inline=False,
            limit=300,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @setadvisormode.autocomplete("account")
    async def setadvisormode_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)

    @advisor.tree.command(name="missinggoals", description="See which advisor goals still need manual tracking input")
    @app_commands.describe(account="Which linked account to inspect")
    async def missinggoals(interaction: discord.Interaction, account: str | None = None):
        await interaction.response.defer(ephemeral=True)
        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        if chosen_tag and user.get("player_tag") != chosen_tag:
            user["player_tag"] = chosen_tag
            if chosen_link:
                user["player_name"] = chosen_link.get("name", "Unknown")

        snapshot = advisor.build_untracked_goal_snapshot(user)
        total_items = int(snapshot.get("items", 0) or 0)
        player_name = user.get("player_name") or "Unknown"

        if total_items <= 0:
            try:
                html_card = advisor._build_missing_goals_card_html(user, snapshot)
                file = await advisor.render_html_card_to_file(html_card, "missing_goals.png", width=1000, height=820, wait_ms=700)
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[MISSING GOALS CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()
            embed = discord.Embed(title="✅ Missing Goal Input", color=0x2ECC71)
            embed.description = f"All current advisor goals for **{player_name}** are already tracked."
            advisor._safe_followup_embed_field(embed, name="What this means", value="Your remaining advisor goals should now mostly be true upgrades left to complete, not missing manual entries.", inline=False, limit=900)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            html_card = advisor._build_missing_goals_card_html(user, snapshot)
            file = await advisor.render_html_card_to_file(html_card, "missing_goals.png", width=1000, height=920, wait_ms=800)
            report_text = advisor.build_untracked_goals_export_text(user)
            report_file = discord.File(io.BytesIO(report_text.encode("utf-8")), filename="missing_goals_report.txt")
            await interaction.followup.send(file=file, ephemeral=True)
            await interaction.followup.send(file=report_file, ephemeral=True)
            return
        except Exception as exc:
            print(f"[MISSING GOALS CARD ERROR] {exc}")
            import traceback
            traceback.print_exc()

        embed = discord.Embed(title="🧭 Missing Goal Input", color=0xF1C40F)
        embed.description = advisor.build_untracked_goal_callout(user)
        advisor._safe_followup_embed_field(
            embed,
            name="Account",
            value=f"{player_name} · TH{user.get('town_hall') or '?'} · {str(user.get('role', DEFAULT_ROLE)).title()}",
            inline=False,
            limit=300,
        )
        advisor._safe_followup_embed_field(
            embed,
            name="Counts",
            value=(
                f"Missing input items: **{total_items}**\n"
                f"Fully missing items: **{int(snapshot.get('missing_items', 0) or 0)}**\n"
                f"Partial multi-copy items: **{int(snapshot.get('partial_items', 0) or 0)}**\n"
                f"Missing tracking slots: **{int(snapshot.get('missing_slots', 0) or 0)}**"
            ),
            inline=False,
            limit=500,
        )

        groups = snapshot.get("groups") or {}
        for category, items in list(groups.items())[:8]:
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            lines = [advisor._format_untracked_goal_line(goal) for goal in items[:10]]
            if len(items) > 10:
                lines.append(f"…and **{len(items) - 10}** more in this category.")
            advisor._safe_followup_embed_field(
                embed,
                name=f"{emoji} {category.replace('_', ' ').title()} ({len(items)})",
                value="\n".join(lines),
                inline=False,
                limit=1000,
            )

        advisor._safe_followup_embed_field(
            embed,
            name="How to fill these",
            value=(
                "Use **/trackupgrade** for single-value manual items.\n"
                "Use **/trackcopies** when a multi-copy building or trap has mixed levels.\n"
                "A text attachment with the full missing-input report is included below."
            ),
            inline=False,
            limit=900,
        )

        report_text = advisor.build_untracked_goals_export_text(user)
        report_bytes = io.BytesIO(report_text.encode("utf-8"))
        report_file = discord.File(report_bytes, filename="missing_goals_report.txt")
        await interaction.followup.send(embed=embed, file=report_file, ephemeral=True)

    @missinggoals.autocomplete("account")
    async def missinggoals_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)


    @advisor.tree.command(name="missingdata", description="List full account-completion slots that still need known levels")
    @app_commands.describe(account="Which linked account to inspect")
    async def missingdata(interaction: discord.Interaction, account: str | None = None):
        await interaction.response.defer(ephemeral=True)
        chosen_link = await advisor.resolve_linked_account(str(interaction.user.id), account)
        chosen_tag = chosen_link["tag"] if chosen_link else account
        user = await advisor.get_user_store(str(interaction.user.id), player_tag=chosen_tag)
        if chosen_tag and user.get("player_tag") != chosen_tag:
            user["player_tag"] = chosen_tag
            if chosen_link:
                user["player_name"] = chosen_link.get("name", "Unknown")

        account_snap = advisor.build_account_completion_snapshot(user)
        missing_rows = advisor.get_missing_account_data(user)
        missing_slots = sum(int(row.get("missing", 0) or 0) for row in missing_rows)
        player_name = user.get("player_name") or "Unknown"

        if missing_slots <= 0:
            try:
                html_card = advisor._build_missing_data_card_html(user, account_snap, missing_rows)
                file = await advisor.render_html_card_to_file(html_card, "missing_data.png", width=1000, height=820, wait_ms=700)
                await interaction.followup.send(file=file, ephemeral=True)
                return
            except Exception as exc:
                print(f"[MISSING DATA CARD ERROR] {exc}")
                import traceback
                traceback.print_exc()
            embed = discord.Embed(title="✅ Missing Account Data", color=0x2ECC71)
            embed.description = f"All supported account-completion data for **{player_name}** is tracked."
            advisor._safe_followup_embed_field(
                embed,
                name="Coverage",
                value=f"Known supported slots: **{account_snap.get('supported_known', 0)} / {account_snap.get('supported_slots', 0)}** ({account_snap.get('coverage_percent', 0)}%)",
                inline=False,
                limit=500,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            html_card = advisor._build_missing_data_card_html(user, account_snap, missing_rows)
            file = await advisor.render_html_card_to_file(html_card, "missing_data.png", width=1000, height=920, wait_ms=800)
            report_text = advisor.build_missing_account_data_export_text(user)
            report_file = discord.File(io.BytesIO(report_text.encode("utf-8")), filename="missing_account_data_report.txt")
            await interaction.followup.send(file=file, ephemeral=True)
            await interaction.followup.send(file=report_file, ephemeral=True)
            return
        except Exception as exc:
            print(f"[MISSING DATA CARD ERROR] {exc}")
            import traceback
            traceback.print_exc()

        embed = discord.Embed(title="🧭 Missing Account Data", color=0xF1C40F)
        embed.description = (
            f"**{player_name}** still has **{missing_slots}** supported account-completion slot(s) without known levels.\n"
            "These are separate from `/missinggoals`; this checks full `/accountcompletion` coverage."
        )
        advisor._safe_followup_embed_field(
            embed,
            name="Coverage",
            value=(
                f"Known supported slots: **{account_snap.get('supported_known', 0)} / {account_snap.get('supported_slots', 0)}** ({account_snap.get('coverage_percent', 0)}%)\n"
                f"Missing supported slots: **{missing_slots}**"
            ),
            inline=False,
            limit=600,
        )

        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in missing_rows:
            grouped.setdefault(str(row.get("category") or "other"), []).append(row)

        for category, rows in list(grouped.items())[:8]:
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            category_label = ACCOUNT_COMPLETION_CATEGORY_LABELS.get(category, category.replace("_", " ").title())
            lines = [advisor._format_missing_account_data_line(row) for row in rows[:8]]
            if len(rows) > 8:
                lines.append(f"…and **{len(rows) - 8}** more item(s) in this category.")
            advisor._safe_followup_embed_field(
                embed,
                name=f"{emoji} {category_label} ({sum(int(row.get('missing', 0) or 0) for row in rows)} slots)",
                value="\n".join(lines),
                inline=False,
                limit=1000,
            )

        advisor._safe_followup_embed_field(
            embed,
            name="How to fill these",
            value=(
                "Use **/trackupgrade** for one current level.\n"
                "Use **/trackcopies** for mixed-level multi-copy items like walls, traps, or defenses.\n"
                "A text attachment with the full missing-data report is included below."
            ),
            inline=False,
            limit=900,
        )

        report_text = advisor.build_missing_account_data_export_text(user)
        report_bytes = io.BytesIO(report_text.encode("utf-8"))
        report_file = discord.File(report_bytes, filename="missing_account_data_report.txt")
        await interaction.followup.send(embed=embed, file=report_file, ephemeral=True)

    @missingdata.autocomplete("account")
    async def missingdata_account_autocomplete(interaction: discord.Interaction, current: str):
        return await account_autocomplete(interaction, current)
