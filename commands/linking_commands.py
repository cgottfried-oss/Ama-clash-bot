from __future__ import annotations

import asyncio
import html as html_lib
import os
from datetime import datetime, timezone

import discord
from discord import app_commands
from playwright.async_api import async_playwright


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

    async def create_link_audit_image(audit_data: dict, image_path: str = "/app/link_audit.png"):
        def esc(v):
            return html_lib.escape(str(v if v is not None else ""))

        def initials(name: str) -> str:
            parts = [p for p in str(name or "").replace("_", " ").split() if p]
            return ("".join(p[0] for p in parts[:2]).upper() or "?")[:2]

        def render_rows(items, empty_text, kind, limit=18):
            if not items:
                return f'<div class="empty">{esc(empty_text)}</div>'

            output = []
            for item in items[:limit]:
                display = item.get("display_name") or item.get("name") or "Unknown"

                if kind == "discord":
                    reason = item.get("reason") or "Discord member has no linked Clash account"
                    output.append(
                        f'<div class="audit-row"><div class="avatar bad">{esc(initials(display))}</div>'
                        f'<div class="row-main"><div class="row-title">{esc(display)}</div>'
                        f'<div class="row-sub">{esc(reason)}</div></div><div class="pill danger">Review</div></div>'
                    )
                elif kind == "linked_not_clan":
                    chips = "".join(
                        f'<span class="tag-chip">{esc(a.get("name", "Unknown"))} · {esc(a.get("tag", ""))}</span>'
                        for a in item.get("accounts", [])
                    ) or '<span class="tag-chip muted">No accounts</span>'
                    output.append(
                        f'<div class="audit-row tall"><div class="avatar warn-a">{esc(initials(display))}</div>'
                        f'<div class="row-main"><div class="row-title">{esc(display)}</div>'
                        f'<div class="chip-wrap">{chips}</div></div><div class="pill warn">Not In Clan</div></div>'
                    )
                elif kind == "clan_not_linked":
                    output.append(
                        f'<div class="audit-row"><div class="avatar clan">{esc(initials(display))}</div>'
                        f'<div class="row-main"><div class="row-title">{esc(display)}</div>'
                        f'<div class="row-sub">{esc(item.get("tag", ""))} · {esc(item.get("clan_label", "Clan"))}</div></div>'
                        f'<div class="pill danger">No Discord</div></div>'
                    )
                else:
                    chips = "".join(
                        f'<span class="tag-chip good-chip">{esc(a.get("name", "Unknown"))} · {esc(a.get("tag", ""))}'
                        f'{(" · " + esc(a.get("clan_label"))) if a.get("clan_label") else ""}</span>'
                        for a in item.get("accounts", [])
                    ) or '<span class="tag-chip muted">No in-clan accounts</span>'
                    output.append(
                        f'<div class="audit-row tall"><div class="avatar ok">{esc(initials(display))}</div>'
                        f'<div class="row-main"><div class="row-title">{esc(display)}</div>'
                        f'<div class="chip-wrap">{chips}</div></div><div class="pill ok-pill">Linked</div></div>'
                    )

            if len(items) > limit:
                output.append(f'<div class="more">+{len(items) - limit} more not shown</div>')
            return "".join(output)

        stats = audit_data.get("stats", {})
        warnings = audit_data.get("warnings", [])
        warning_html = "".join(
            f'<div class="warning">⚠️ {esc(w)}</div>' for w in warnings
        ) or '<div class="warning muted-warning">No API warnings</div>'
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:34px;background:radial-gradient(circle at top left,#26354f 0,#101827 36%,#070b12 100%);color:#f8fafc;font-family:Inter,Arial,sans-serif}}
.card{{width:1040px;border-radius:30px;overflow:hidden;background:linear-gradient(145deg,rgba(15,23,42,.98),rgba(17,24,39,.96));border:1px solid rgba(255,255,255,.10);box-shadow:0 28px 90px rgba(0,0,0,.55)}}
.header{{padding:32px 36px 24px;background:linear-gradient(135deg,rgba(249,115,22,.28),rgba(59,130,246,.12));border-bottom:1px solid rgba(255,255,255,.10)}}
.eyebrow{{color:#fbbf24;text-transform:uppercase;letter-spacing:.16em;font-size:13px;font-weight:800}}
h1{{margin:8px 0;font-size:42px;line-height:1}}
.subtitle{{margin:0;color:#cbd5e1;font-size:17px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:24px 28px 12px}}
.stat{{background:rgba(255,255,255,.065);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:16px}}
.num{{font-size:30px;font-weight:900}}
.label{{color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-top:3px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:18px 28px 28px}}
.section{{background:rgba(255,255,255,.052);border:1px solid rgba(255,255,255,.08);border-radius:22px;overflow:hidden}}
.full{{grid-column:span 2}}
.section-title{{padding:16px 18px;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between}}
.count{{color:#fbbf24}}
.section-body{{padding:12px}}
.audit-row{{display:flex;align-items:center;gap:12px;padding:12px;border-radius:16px;background:rgba(15,23,42,.58);margin-bottom:9px}}
.tall{{align-items:flex-start}}
.avatar{{width:42px;height:42px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:900;flex:0 0 auto}}
.bad{{background:linear-gradient(135deg,#ef4444,#f97316)}}
.warn-a{{background:linear-gradient(135deg,#f59e0b,#eab308)}}
.ok{{background:linear-gradient(135deg,#16a34a,#22c55e)}}
.clan{{background:linear-gradient(135deg,#8b5cf6,#3b82f6)}}
.row-main{{flex:1;min-width:0}}
.row-title{{font-size:16px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.row-sub{{color:#94a3b8;margin-top:4px;font-size:13px}}
.pill{{border-radius:999px;padding:7px 10px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:900;white-space:nowrap}}
.danger{{color:#fecaca;background:rgba(239,68,68,.18);border:1px solid rgba(239,68,68,.25)}}
.warn{{color:#fde68a;background:rgba(245,158,11,.16);border:1px solid rgba(245,158,11,.25)}}
.ok-pill{{color:#bbf7d0;background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.25)}}
.chip-wrap{{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}}
.tag-chip{{font-size:12px;color:#dbeafe;background:rgba(59,130,246,.13);border:1px solid rgba(59,130,246,.25);border-radius:999px;padding:5px 8px}}
.good-chip{{color:#bbf7d0;background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.24)}}
.muted,.empty,.more{{color:#94a3b8}}
.empty,.more{{padding:16px;text-align:center}}
.more{{border-top:1px dashed rgba(255,255,255,.14);margin-top:8px}}
.warnings{{padding:0 28px 30px;display:grid;gap:8px}}
.warning{{background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.18);border-radius:16px;padding:12px 16px;color:#fde68a}}
.muted-warning{{color:#94a3b8;background:rgba(255,255,255,.04);border-color:rgba(255,255,255,.08)}}
.footer{{color:#64748b;padding:0 36px 28px;font-size:12px}}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="eyebrow">G.A.I.A Link Audit</div>
    <h1>Discord ↔ Clash Account Health</h1>
    <p class="subtitle">A cleaner audit of who is linked, who is missing, and which Discord members may need review.</p>
  </div>
  <div class="stats">
    <div class="stat"><div class="num">{int(stats.get("guild_members",0))}</div><div class="label">Discord Members</div></div>
    <div class="stat"><div class="num">{int(stats.get("clan_members",0))}</div><div class="label">Clan Accounts</div></div>
    <div class="stat"><div class="num">{int(stats.get("linked_in_clan",0))}</div><div class="label">Healthy Links</div></div>
    <div class="stat"><div class="num">{int(stats.get("needs_link",0))}</div><div class="label">Need Link</div></div>
    <div class="stat"><div class="num">{int(stats.get("kick_candidates",0))}</div><div class="label">Review</div></div>
  </div>
  <div class="grid">
    <div class="section"><div class="section-title"><span>🚨 Review / Kick Candidates</span><span class="count">{len(audit_data.get("kick_candidates",[]))}</span></div><div class="section-body">{render_rows(audit_data.get("kick_candidates",[]),"No obvious review candidates.","discord")}</div></div>
    <div class="section"><div class="section-title"><span>❌ Discord Members With No Link</span><span class="count">{len(audit_data.get("unlinked_discord",[]))}</span></div><div class="section-body">{render_rows(audit_data.get("unlinked_discord",[]),"Everyone has at least one linked Clash account.","discord")}</div></div>
    <div class="section"><div class="section-title"><span>⚠️ Linked But Not In Clan</span><span class="count">{len(audit_data.get("linked_not_in_clan",[]))}</span></div><div class="section-body">{render_rows(audit_data.get("linked_not_in_clan",[]),"No linked Discord members are outside the tracked clans.","linked_not_clan")}</div></div>
    <div class="section"><div class="section-title"><span>🧩 Clan Accounts Not Linked</span><span class="count">{len(audit_data.get("clan_not_linked",[]))}</span></div><div class="section-body">{render_rows(audit_data.get("clan_not_linked",[]),"Every clan account is linked to Discord.","clan_not_linked")}</div></div>
    <div class="section full"><div class="section-title"><span>✅ Linked And In Clan</span><span class="count">{len(audit_data.get("linked_in_clan",[]))}</span></div><div class="section-body">{render_rows(audit_data.get("linked_in_clan",[]),"No healthy links found yet.","good",24)}</div></div>
  </div>
  <div class="warnings">{warning_html}</div>
  <div class="footer">Generated {esc(generated_at)} • Showing top rows only when sections are long</div>
</div>
</body>
</html>"""

        os.makedirs(os.path.dirname(image_path) or ".", exist_ok=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox"])
            page = await browser.new_page(viewport={"width": 1110, "height": 1500})
            page.set_default_timeout(10000)
            await page.set_content(html, wait_until="domcontentloaded")
            await page.wait_for_timeout(700)
            await page.screenshot(path=image_path, full_page=True)
            await browser.close()
        return open(image_path, "rb")

    @bot.tree.command(name="linkaudit", description="Audit Discord members vs linked Clash accounts vs clan roster")
    async def linkaudit(interaction: discord.Interaction):
        # Defer immediately so Discord does not show "The application did not respond" while this audit runs.
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

        if interaction.guild is None:
            await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.followup.send("❌ Could not verify your server roles.", ephemeral=True)
            return

        roles = [role.id for role in interaction.user.roles]
        if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return

        guild = interaction.guild
        try:
            await asyncio.wait_for(guild.chunk(cache=True), timeout=8)
        except Exception as e:
            print(f"[LINKAUDIT MEMBER CACHE WARNING] {type(e).__name__}: {e}")

        linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
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
            await interaction.followup.send("❌ Could not fetch current clan members from the Clash API.", ephemeral=True)
            return

        clan_lookup = []
        clan_tags = set()
        for m in all_clan_members:
            tag = normalize_tag(m.get("tag", ""))
            if tag and tag not in clan_tags:
                clan_lookup.append({"tag": tag, "name": m.get("name", "Unknown"), "clan_label": tag_to_clan_label.get(tag, "Clan")})
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
            linked_tags = [normalize_tag(e.get("tag")) for e in entries if e.get("tag")]
            payload = {"display_name": member.display_name, "discord_id": user_id}

            if not linked_tags:
                unlinked_discord.append(payload)
                kick_candidates.append({**payload, "reason": "No linked Clash account"})
                continue

            in_clan_tags = [tag for tag in linked_tags if tag in clan_tags]
            if in_clan_tags:
                accounts = [
                    {
                        "name": e.get("name", "Unknown"),
                        "tag": normalize_tag(e.get("tag")),
                        "clan_label": tag_to_clan_label.get(normalize_tag(e.get("tag"))),
                    }
                    for e in entries
                    if normalize_tag(e.get("tag")) in in_clan_tags
                ]
                linked_in_clan.append({**payload, "accounts": accounts})
            else:
                accounts = [
                    {"name": e.get("name", "Unknown"), "tag": normalize_tag(e.get("tag"))}
                    for e in entries
                    if e.get("tag")
                ]
                linked_not_in_clan.append({**payload, "accounts": accounts})
                kick_candidates.append({**payload, "reason": "Linked, but no linked accounts are in clan"})

        for m in clan_lookup:
            if m["tag"] not in tag_to_discord:
                clan_not_linked.append(m)

        audit_data = {
            "stats": {
                "guild_members": len([m for m in guild.members if not m.bot]),
                "clan_members": len(clan_lookup),
                "linked_in_clan": len(linked_in_clan),
                "needs_link": len(unlinked_discord) + len(clan_not_linked),
                "kick_candidates": len(kick_candidates),
            },
            "kick_candidates": kick_candidates,
            "unlinked_discord": unlinked_discord,
            "linked_not_in_clan": linked_not_in_clan,
            "clan_not_linked": clan_not_linked,
            "linked_in_clan": linked_in_clan,
            "warnings": [f"Could not fetch members for: {', '.join(failed_clan_tags)}"] if failed_clan_tags else [],
        }

        try:
            image_buffer = await create_link_audit_image(audit_data)
            file = discord.File(fp=image_buffer, filename="link_audit.png")
            embed = discord.Embed(
                title="🧩 G.A.I.A Link Audit",
                description=(
                    f"**Healthy links:** {len(linked_in_clan)}\n"
                    f"**Discord members with no link:** {len(unlinked_discord)}\n"
                    f"**Clan accounts not linked:** {len(clan_not_linked)}\n"
                    f"**Review candidates:** {len(kick_candidates)}"
                ),
                color=0xFF7A1A,
            )
            embed.set_image(url="attachment://link_audit.png")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            return
        except Exception as e:
            print(f"[LINKAUDIT RENDER ERROR] {e}")

        await interaction.followup.send(
            f"**🧩 G.A.I.A Link Audit**\n"
            f"Healthy links: **{len(linked_in_clan)}**\n"
            f"Discord members with no link: **{len(unlinked_discord)}**\n"
            f"Clan accounts not linked: **{len(clan_not_linked)}**\n"
            f"Review candidates: **{len(kick_candidates)}**",
            ephemeral=True,
        )

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

