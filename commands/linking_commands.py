from __future__ import annotations

import discord
from discord import app_commands


def register_linking_commands(bot, ctx):
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID
    CLAN_TAGS = ctx.CLAN_TAGS
    MAIN_CLAN_TAG = ctx.MAIN_CLAN_TAG
    LINKED_FILE = ctx.LINKED_FILE
    TAG_REGEX = ctx.TAG_REGEX

    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file
    normalize_tag = ctx.normalize_tag
    normalize_linked_data = ctx.normalize_linked_data
    build_tag_to_discord_map = ctx.build_tag_to_discord_map
    fetch_clan_data = ctx.fetch_clan_data
    get_cached_or_fetch = ctx.get_cached_or_fetch

    @bot.tree.command(
        name="linkaudit",
        description="Audit Discord members vs linked Clash accounts vs clan roster",
    )
    async def linkaudit(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This command must be used in a server.", ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Could not verify your server roles.", ephemeral=True
            )
            return

        roles = [role.id for role in interaction.user.roles]
        is_leader = LEADER_ROLE_ID in roles or CO_LEADER_ROLE_ID in roles
        if not is_leader:
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(
                "❌ This command must be used in a server.", ephemeral=True
            )
            return

        await guild.chunk()

        linked_raw = await safe_load_json(LINKED_FILE)
        linked = normalize_linked_data(linked_raw)

        all_clan_members = []
        failed_clan_tags = []
        tag_to_clan_label = {}

        for clan_tag in CLAN_TAGS:
            if not clan_tag:
                continue

            clan_label = "Main Clan" if clan_tag == MAIN_CLAN_TAG else "Feeder Clan"

            _, clan_members = await fetch_clan_data(clan_tag)
            if not clan_members:
                failed_clan_tags.append(f"{clan_label} ({clan_tag})")
                continue

            for clan_member in clan_members:
                member_tag = normalize_tag(clan_member.get("tag", ""))
                if member_tag:
                    tag_to_clan_label[member_tag] = clan_label

            all_clan_members.extend(clan_members)

        if not all_clan_members:
            await interaction.followup.send(
                "❌ Could not fetch current clan members from the Clash API.",
                ephemeral=True,
            )
            return

        clan_lookup = []
        clan_tags = set()

        for m in all_clan_members:
            tag = normalize_tag(m.get("tag", ""))
            name = m.get("name", "Unknown")
            if tag and tag not in clan_tags:
                clan_lookup.append({"tag": tag, "name": name})
                clan_tags.add(tag)

        tag_to_discord = build_tag_to_discord_map(linked)

        unlinked_discord = []
        linked_not_in_clan = []
        linked_in_clan = []
        clan_not_linked = []
        kick_candidates = []

        for member in guild.members:
            if member.bot:
                continue

            user_id = str(member.id)
            entries = linked.get(user_id, [])
            linked_tags = [e["tag"] for e in entries if e.get("tag")]

            if not linked_tags:
                unlinked_discord.append(member)
                kick_candidates.append((member, "No linked Clash account"))
                continue

            in_clan_tags = [tag for tag in linked_tags if tag in clan_tags]

            if in_clan_tags:
                linked_in_clan.append((member, entries, in_clan_tags))
            else:
                linked_not_in_clan.append((member, entries))
                kick_candidates.append(
                    (member, "Linked, but no linked accounts are in clan")
                )

        for m in clan_lookup:
            if m["tag"] not in tag_to_discord:
                clan_not_linked.append(m)

        def format_accounts(entries, clan_labels=None):
            formatted = []
            for e in entries:
                player_tag = e.get("tag", "Unknown")
                account_text = f"{e.get('name', 'Unknown')} ({player_tag})"
                if clan_labels:
                    clan_label = clan_labels.get(normalize_tag(player_tag))
                    if clan_label:
                        account_text += f" — {clan_label}"
                formatted.append(account_text)
            return ", ".join(formatted)

        sections = []

        sections.append("**Kick Candidates**")
        if kick_candidates:
            for member, reason in kick_candidates:
                sections.append(f"• {member.display_name} — {reason}")
        else:
            sections.append("• None")

        sections.append("\n**Discord Members With No Link**")
        if unlinked_discord:
            for member in unlinked_discord:
                sections.append(f"• {member.display_name}")
        else:
            sections.append("• None")

        sections.append("\n**Linked Discord Members Not In Clan**")
        if linked_not_in_clan:
            for member, entries in linked_not_in_clan:
                sections.append(f"• {member.display_name} — {format_accounts(entries)}")
        else:
            sections.append("• None")

        sections.append("\n**Clan Members Not Linked To Discord**")
        if clan_not_linked:
            for m in clan_not_linked:
                sections.append(f"• {m['name']} ({m['tag']})")
        else:
            sections.append("• None")

        sections.append("\n**Linked And In Clan**")
        if linked_in_clan:
            for member, entries, in_clan_tags in linked_in_clan:
                matching = [e for e in entries if e.get("tag") in in_clan_tags]
                sections.append(
                    f"• {member.display_name} — {format_accounts(matching, tag_to_clan_label)}"
                )
        else:
            sections.append("• None")

        if failed_clan_tags:
            failed_tags = ", ".join(failed_clan_tags)
            sections.append(
                f"\n**Warnings**\n• Could not fetch members for: {failed_tags}"
            )

        report = "\n".join(sections)

        chunk_size = 1900
        for i in range(0, len(report), chunk_size):
            await interaction.followup.send(report[i:i + chunk_size], ephemeral=True)


    @bot.tree.command(name="linked", description="View linked Clash accounts")
    @app_commands.describe(user="Optional: leaders can check another member")
    async def linked(interaction: discord.Interaction, user: discord.Member | None = None):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True,
            )
            return

        # Defer immediately so Discord doesn't think the command failed
        await interaction.response.defer(ephemeral=True)

        linked_data = normalize_linked_data(await safe_load_json(LINKED_FILE))

        if not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "❌ Could not verify your server roles.",
                ephemeral=True,
            )
            return

        is_leader = any(
            role.id in (LEADER_ROLE_ID, CO_LEADER_ROLE_ID)
            for role in interaction.user.roles
        )

        if user is not None and not is_leader:
            await interaction.followup.send(
                "❌ Only leaders and co-leaders can check another member's linked accounts.",
                ephemeral=True,
            )
            return

        target_user = user if user is not None else interaction.user
        user_id = str(target_user.id)

        tags = linked_data.get(user_id, [])

        # Normalize old data
        normalized = []
        for entry in tags:
            if isinstance(entry, str):
                normalized.append({"tag": entry, "name": "Unknown"})
            elif isinstance(entry, dict) and "tag" in entry:
                normalized.append(
                    {
                        "tag": entry["tag"],
                        "name": entry.get("name", "Unknown"),
                    }
                )

        tags = normalized

        # Refresh names from API
        updated = False
        for entry in tags:
            try:
                encoded_tag = entry["tag"].replace("#", "%23")
                url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"
                data = await get_cached_or_fetch(f"player_{entry['tag']}", url, ttl=3600)

                if data:
                    new_name = data.get("name")
                    if new_name and new_name != entry["name"]:
                        entry["name"] = new_name
                        updated = True
            except Exception as e:
                print(f"[LINKED REFRESH ERROR] {entry.get('tag')}: {e}")

        if updated:

            def _update_linked_names(data):
                data = normalize_linked_data(data)
                data[user_id] = tags
                return data

            await update_json_file(LINKED_FILE, _update_linked_names)

        entries_text = (
            ", ".join(f"{e['name']} ({e['tag']})" for e in tags) if tags else "None"
        )
        msg = f"{target_user.display_name}'s linked accounts:\n{entries_text}"

        await interaction.followup.send(msg, ephemeral=True)


    @bot.tree.command(name="link", description="Link your Clash player tag to your Discord")
    @app_commands.describe(tag="Enter your Clash player tag (e.g., #ABCD123)")
    async def link(interaction: discord.Interaction, tag: str):
        tag = normalize_tag(tag)

        if not TAG_REGEX.match(tag):
            await interaction.response.send_message(
                "❌ Invalid Clash tag! Include # and only use letters A-Z and numbers.",
                ephemeral=True,
            )
            return

        linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
        user_id = str(interaction.user.id)

        existing_entries = linked.get(user_id, [])
        if any(normalize_tag(entry["tag"]) == tag for entry in existing_entries):
            await interaction.response.send_message(
                f"Already linked to {tag}", ephemeral=True
            )
            return

        # ✅ Fetch player data
        encoded_tag = tag.replace("#", "%23")
        url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"

        data = await get_cached_or_fetch(f"player_{tag}", url, ttl=300)

        if not data:
            await interaction.response.send_message(
                "❌ Could not fetch player. Check the tag.", ephemeral=True
            )
            return

        player_name = data.get("name", "Unknown")

        # ✅ Save tag + name atomically
        def _update_linked(data):
            data = normalize_linked_data(data)
            data.setdefault(user_id, [])

            if not any(normalize_tag(entry["tag"]) == tag for entry in data[user_id]):
                data[user_id].append({"tag": tag, "name": player_name})

            return data

        await update_json_file(LINKED_FILE, _update_linked)

        await interaction.response.send_message(
            f"✅ Linked **{player_name}** ({tag})", ephemeral=True
        )


    @bot.tree.command(name="unlink", description="Unlink one of your Clash accounts")
    @app_commands.describe(tag="Enter the Clash player tag you want to unlink")
    async def unlink(interaction: discord.Interaction, tag: str):
        await interaction.response.defer(ephemeral=True)

        tag = normalize_tag(tag)
        user_id = str(interaction.user.id)

        linked_data = normalize_linked_data(await safe_load_json(LINKED_FILE))
        existing_entries = linked_data.get(user_id, [])

        if not existing_entries:
            await interaction.followup.send(
                "❌ You do not have any linked Clash accounts.",
                ephemeral=True,
            )
            return

        if not any(normalize_tag(entry["tag"]) == tag for entry in existing_entries):
            await interaction.followup.send(
                f"❌ {tag} is not currently linked to your Discord.",
                ephemeral=True,
            )
            return

        def _update_unlinked(data):
            data = normalize_linked_data(data)
            entries = data.get(user_id, [])
            data[user_id] = [
                entry for entry in entries if normalize_tag(entry["tag"]) != tag
            ]

            if not data[user_id]:
                data.pop(user_id, None)

            return data

        await update_json_file(LINKED_FILE, _update_unlinked)

        await interaction.followup.send(
            f"✅ Unlinked {tag} from your Discord.",
            ephemeral=True,
        )

