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
        """Render a cleaner 3-column link audit card."""

        def esc(v):
            return html_lib.escape(str(v if v is not None else ""))

        def initials(name: str) -> str:
            parts = [p for p in str(name or "").replace("_", " ").split() if p]
            return ("".join(p[0] for p in parts[:2]).upper() or "?")[:2]

        def render_tag_chips(accounts):
            chips = []
            for account in accounts or []:
                tag = esc(account.get("tag", ""))
                player_name = esc(account.get("player_name") or account.get("name") or "Unknown")
                chips.append(f'<span class="tag-chip">{player_name} <b>{tag}</b></span>')
            return "".join(chips) or '<span class="tag-chip muted">No tag data</span>'

        def render_linked_rows(rows, accent: str, empty_text: str, limit: int = 24):
            if not rows:
                return f'<div class="empty">{esc(empty_text)}</div>'

            output = []
            for index, row in enumerate(rows[:limit], start=1):
                display = row.get("discord_name") or row.get("display_name") or row.get("name") or "Unknown"
                output.append(
                    f"""
                    <div class="member-row linked-row">
                        <div class="rank {accent}">{index}</div>
                        <div class="avatar {accent}">{esc(initials(display))}</div>
                        <div class="member-main">
                            <div class="member-name">{esc(display)}</div>
                            <div class="chip-wrap">{render_tag_chips(row.get("accounts", []))}</div>
                        </div>
                        <div class="status-pill linked">Linked</div>
                    </div>
                    """
                )

            if len(rows) > limit:
                output.append(f'<div class="more">+{len(rows) - limit} more linked members not shown</div>')
            return "".join(output)

        def render_unlinked_rows(rows, accent: str, empty_text: str, limit: int = 18):
            if not rows:
                return f'<div class="empty">{esc(empty_text)}</div>'

            output = []
            for index, row in enumerate(rows[:limit], start=1):
                name = row.get("player_name") or row.get("name") or "Unknown"
                tag = row.get("tag", "")
                output.append(
                    f"""
                    <div class="member-row unlinked-row">
                        <div class="rank {accent}">{index}</div>
                        <div class="avatar warning">{esc(initials(name))}</div>
                        <div class="member-main">
                            <div class="member-name">{esc(name)}</div>
                            <div class="member-sub">{esc(tag)}</div>
                        </div>
                        <div class="status-pill missing">No Link</div>
                    </div>
                    """
                )

            if len(rows) > limit:
                output.append(f'<div class="more">+{len(rows) - limit} more unlinked accounts not shown</div>')
            return "".join(output)

        main = audit_data.get("main", {})
        feeder = audit_data.get("feeder", {})
        stats = audit_data.get("stats", {})
        warnings = audit_data.get("warnings", [])
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        warning_html = "".join(f'<div class="warning">⚠️ {esc(w)}</div>' for w in warnings)
        if not warning_html:
            warning_html = '<div class="footer-note">✅ Clash API data loaded successfully.</div>'

        main_linked = main.get("linked", [])
        feeder_linked = feeder.get("linked", [])
        main_unlinked = main.get("unlinked", [])
        feeder_unlinked = feeder.get("unlinked", [])

        html = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:28px;background:#070b12;color:#f8fafc;font-family:Inter,Arial,sans-serif}}
.card{{width:1500px;border-radius:30px;overflow:hidden;background:radial-gradient(circle at 12% 0%,rgba(14,165,233,.18),transparent 34%),radial-gradient(circle at 86% 2%,rgba(168,85,247,.16),transparent 30%),linear-gradient(145deg,#08111f 0%,#0f172a 46%,#111827 100%);border:2px solid rgba(56,189,248,.38);box-shadow:0 30px 90px rgba(0,0,0,.68)}}
.header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;padding:34px 40px 22px;border-bottom:1px solid rgba(148,163,184,.16)}}
.brand-row{{display:flex;gap:22px;align-items:center}}
.logo{{width:72px;height:72px;border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;background:linear-gradient(135deg,rgba(56,189,248,.22),rgba(59,130,246,.10));border:1px solid rgba(56,189,248,.38)}}
.eyebrow{{color:#fbbf24;text-transform:uppercase;letter-spacing:.18em;font-size:13px;font-weight:900}}
h1{{margin:4px 0 6px;font-size:46px;line-height:1;letter-spacing:.02em;text-shadow:0 4px 0 rgba(0,0,0,.25)}}
.subtitle{{margin:0;color:#cbd5e1;font-size:19px}}
.timestamp{{min-width:220px;text-align:right;color:#cbd5e1;background:rgba(15,23,42,.70);border:1px solid rgba(148,163,184,.18);border-radius:18px;padding:14px 18px;font-size:15px;line-height:1.5}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;padding:22px 26px 18px}}
.stat{{border-radius:18px;padding:16px 18px;background:linear-gradient(180deg,rgba(30,41,59,.92),rgba(15,23,42,.82));border:1px solid rgba(148,163,184,.17);box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}}
.stat.green{{border-color:rgba(34,197,94,.34);background:linear-gradient(180deg,rgba(20,83,45,.32),rgba(15,23,42,.82))}}
.stat.purple{{border-color:rgba(168,85,247,.36);background:linear-gradient(180deg,rgba(88,28,135,.30),rgba(15,23,42,.82))}}
.stat.orange{{border-color:rgba(249,115,22,.42);background:linear-gradient(180deg,rgba(124,45,18,.30),rgba(15,23,42,.82))}}
.num{{font-size:34px;font-weight:950;line-height:1}}
.stat.green .num{{color:#86efac}} .stat.purple .num{{color:#c084fc}} .stat.orange .num{{color:#fdba74}}
.label{{color:#cbd5e1;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-top:6px}}
.columns{{display:grid;grid-template-columns:1fr 1fr 1.04fr;gap:18px;padding:0 26px 28px}}
.panel{{border-radius:24px;overflow:hidden;min-height:760px;background:rgba(15,23,42,.58);border:1px solid rgba(148,163,184,.16)}}
.panel.main{{border-color:rgba(34,197,94,.48);box-shadow:0 0 0 1px rgba(34,197,94,.12),inset 0 1px 0 rgba(255,255,255,.05)}}
.panel.feeder{{border-color:rgba(168,85,247,.52);box-shadow:0 0 0 1px rgba(168,85,247,.12),inset 0 1px 0 rgba(255,255,255,.05)}}
.panel.missing-panel{{border-color:rgba(249,115,22,.55);box-shadow:0 0 0 1px rgba(249,115,22,.12),inset 0 1px 0 rgba(255,255,255,.05)}}
.panel-head{{padding:20px 22px 16px;border-bottom:1px solid rgba(148,163,184,.14)}}
.panel-title{{display:flex;align-items:center;gap:12px;font-size:27px;font-weight:950;text-transform:uppercase;letter-spacing:.04em}}
.panel-title .shield{{font-size:34px}}
.panel.main .panel-title{{color:#86efac}} .panel.feeder .panel-title{{color:#c084fc}} .panel.missing-panel .panel-title{{color:#fdba74}}
.clan-tag{{display:inline-block;margin-top:8px;padding:5px 10px;border-radius:999px;background:rgba(56,189,248,.10);border:1px solid rgba(56,189,248,.22);color:#bae6fd;font-size:12px;font-weight:850;letter-spacing:.04em}}
.mini-stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}}
.mini{{border-radius:14px;padding:11px;background:rgba(2,6,23,.42);border:1px solid rgba(148,163,184,.12)}}
.mini-num{{font-size:22px;font-weight:950}} .mini-label{{font-size:10px;text-transform:uppercase;color:#94a3b8;margin-top:2px}}
.panel-body{{padding:14px}}
.subsection{{margin-bottom:16px}}
.subsection-title{{padding:10px 12px;margin:2px 0 10px;border-radius:14px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.065);display:flex;justify-content:space-between;align-items:center;font-weight:900}}
.subsection-title.main-title{{color:#86efac}} .subsection-title.feeder-title{{color:#c084fc}}
.member-row{{display:flex;align-items:center;gap:10px;min-height:54px;padding:10px 10px;margin-bottom:8px;border-radius:15px;background:rgba(2,6,23,.40);border:1px solid rgba(148,163,184,.08)}}
.linked-row{{background:linear-gradient(90deg,rgba(15,23,42,.80),rgba(15,23,42,.44))}}
.unlinked-row{{background:linear-gradient(90deg,rgba(124,45,18,.18),rgba(15,23,42,.50))}}
.rank{{width:30px;text-align:center;font-weight:950;font-size:15px}}
.rank.main-accent{{color:#86efac}} .rank.feeder-accent{{color:#c084fc}} .rank.missing-accent{{color:#fdba74}}
.avatar{{width:38px;height:38px;border-radius:13px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:950;color:white;flex:0 0 auto}}
.avatar.main-accent{{background:linear-gradient(135deg,#16a34a,#22c55e)}}
.avatar.feeder-accent{{background:linear-gradient(135deg,#7c3aed,#a855f7)}}
.avatar.warning{{background:linear-gradient(135deg,#f97316,#f59e0b)}}
.member-main{{flex:1;min-width:0}}
.member-name{{font-size:15px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.member-sub{{font-size:12px;color:#94a3b8;margin-top:3px}}
.chip-wrap{{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}}
.tag-chip{{font-size:11px;color:#bbf7d0;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.22);border-radius:999px;padding:4px 8px}}
.panel.feeder .tag-chip{{color:#e9d5ff;background:rgba(168,85,247,.12);border-color:rgba(168,85,247,.22)}}
.tag-chip b{{font-weight:950;color:#e0f2fe;margin-left:4px}}
.muted{{color:#94a3b8!important;background:rgba(148,163,184,.08)!important;border-color:rgba(148,163,184,.12)!important}}
.status-pill{{border-radius:999px;padding:6px 9px;font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-weight:950;white-space:nowrap}}
.status-pill.linked{{color:#bbf7d0;background:rgba(34,197,94,.13);border:1px solid rgba(34,197,94,.22)}}
.status-pill.missing{{color:#fed7aa;background:rgba(249,115,22,.13);border:1px solid rgba(249,115,22,.28)}}
.empty,.more{{color:#94a3b8;text-align:center;padding:14px;border-radius:14px;background:rgba(255,255,255,.035);border:1px dashed rgba(148,163,184,.15)}}
.more{{margin-top:8px}}
.warnings{{padding:0 26px 20px;display:grid;gap:8px}}
.warning,.footer-note{{border-radius:16px;padding:12px 16px;background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.18);color:#fde68a}}
.footer-note{{background:rgba(34,197,94,.08);border-color:rgba(34,197,94,.16);color:#bbf7d0}}
.footer{{color:#94a3b8;padding:0 40px 28px;font-size:14px;display:flex;justify-content:space-between}}
</style>
</head>
<body>
<div class="card">
  <div class="header"><div class="brand-row"><div class="logo">🔗</div><div><div class="eyebrow">G.A.I.A Link Audit</div><h1>Discord ↔ Clash Account Overview</h1><p class="subtitle">Main Clan and Feeder Clan links, plus clan accounts that still need a Discord link.</p></div></div><div class="timestamp">Generated<br><b>{esc(generated_at)}</b></div></div>
  <div class="stats"><div class="stat"><div class="num">{int(stats.get("guild_members", 0))}</div><div class="label">Discord Members</div></div><div class="stat green"><div class="num">{len(main_linked)}</div><div class="label">Main Linked</div></div><div class="stat purple"><div class="num">{len(feeder_linked)}</div><div class="label">Feeder Linked</div></div><div class="stat orange"><div class="num">{len(main_unlinked) + len(feeder_unlinked)}</div><div class="label">No Link</div></div><div class="stat"><div class="num">{int(stats.get("total_links", 0))}</div><div class="label">Total Linked Tags</div></div></div>
  <div class="columns">
    <div class="panel main"><div class="panel-head"><div class="panel-title"><span class="shield">🛡️</span> Main Clan</div><div class="clan-tag">{esc(main.get("tag", "Main Clan"))}</div><div class="mini-stats"><div class="mini"><div class="mini-num">{len(main_linked)}</div><div class="mini-label">Linked</div></div><div class="mini"><div class="mini-num">{int(main.get("unique_members", len(main_linked)))}</div><div class="mini-label">Discord Users</div></div><div class="mini"><div class="mini-num">{int(main.get("total_accounts", len(main_linked)))}</div><div class="mini-label">Accounts</div></div></div></div><div class="panel-body">{render_linked_rows(main_linked, "main-accent", "No linked Main Clan accounts found.")}</div></div>
    <div class="panel feeder"><div class="panel-head"><div class="panel-title"><span class="shield">🛡️</span> Feeder Clan</div><div class="clan-tag">{esc(feeder.get("tag", "Feeder Clan"))}</div><div class="mini-stats"><div class="mini"><div class="mini-num">{len(feeder_linked)}</div><div class="mini-label">Linked</div></div><div class="mini"><div class="mini-num">{int(feeder.get("unique_members", len(feeder_linked)))}</div><div class="mini-label">Discord Users</div></div><div class="mini"><div class="mini-num">{int(feeder.get("total_accounts", len(feeder_linked)))}</div><div class="mini-label">Accounts</div></div></div></div><div class="panel-body">{render_linked_rows(feeder_linked, "feeder-accent", "No linked Feeder Clan accounts found.")}</div></div>
    <div class="panel missing-panel"><div class="panel-head"><div class="panel-title"><span class="shield">⛓️</span> No Linked Account</div><div class="clan-tag">Clan accounts missing Discord links</div><div class="mini-stats"><div class="mini"><div class="mini-num">{len(main_unlinked) + len(feeder_unlinked)}</div><div class="mini-label">Missing</div></div><div class="mini"><div class="mini-num">{len(main_unlinked)}</div><div class="mini-label">Main Clan</div></div><div class="mini"><div class="mini-num">{len(feeder_unlinked)}</div><div class="mini-label">Feeder Clan</div></div></div></div><div class="panel-body"><div class="subsection"><div class="subsection-title main-title"><span>🛡️ Main Clan Missing Links</span><span>{len(main_unlinked)}</span></div>{render_unlinked_rows(main_unlinked, "missing-accent", "Every Main Clan account is linked.")}</div><div class="subsection"><div class="subsection-title feeder-title"><span>🛡️ Feeder Clan Missing Links</span><span>{len(feeder_unlinked)}</span></div>{render_unlinked_rows(feeder_unlinked, "missing-accent", "Every Feeder Clan account is linked.")}</div></div></div>
  </div>
  <div class="warnings">{warning_html}</div><div class="footer"><span>Keep accounts linked to earn rewards and stay on leaderboards.</span><span>G.A.I.A System Audit</span></div>
</div>
</body>
</html>'''

        os.makedirs(os.path.dirname(image_path) or ".", exist_ok=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox"])
            page = await browser.new_page(viewport={"width": 1560, "height": 1100})
            page.set_default_timeout(10000)
            await page.set_content(html, wait_until="domcontentloaded")
            await page.wait_for_timeout(700)
            await page.screenshot(path=image_path, full_page=True)
            await browser.close()
        return open(image_path, "rb")

    @bot.tree.command(name="linkaudit", description="Audit Main and Feeder clan linked Clash accounts")
    async def linkaudit(interaction: discord.Interaction):
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
        tag_to_discord = build_tag_to_discord_map(linked)
        normalized_main_tag = normalize_tag(MAIN_CLAN_TAG)

        discord_names = {}
        for member in guild.members:
            if not member.bot:
                discord_names[str(member.id)] = member.display_name

        clan_blocks = {
            "main": {"label": "Main Clan", "tag": normalized_main_tag or "Main Clan", "linked": [], "unlinked": [], "unique_members": 0, "total_accounts": 0},
            "feeder": {"label": "Feeder Clan", "tag": "Feeder Clan", "linked": [], "unlinked": [], "unique_members": 0, "total_accounts": 0},
        }
        warnings = []
        seen_roster_tags = set()

        for clan_index, clan_tag in enumerate(CLAN_TAGS):
            if not clan_tag:
                continue

            normalized_clan_tag = normalize_tag(clan_tag)
            block_key = "main" if normalized_clan_tag == normalized_main_tag or clan_index == 0 else "feeder"
            clan_label = "Main Clan" if block_key == "main" else "Feeder Clan"
            clan_blocks[block_key]["tag"] = normalized_clan_tag or clan_label

            _, clan_members = await fetch_clan_data(clan_tag)
            if not clan_members:
                warnings.append(f"Could not fetch members for {clan_label} ({clan_tag}).")
                continue

            linked_by_discord = {}
            unlinked_rows = []

            for clan_member in clan_members:
                player_tag = normalize_tag(clan_member.get("tag", ""))
                player_name = clan_member.get("name", "Unknown")
                if not player_tag or player_tag in seen_roster_tags:
                    continue
                seen_roster_tags.add(player_tag)

                discord_id = tag_to_discord.get(player_tag)
                if discord_id:
                    discord_id = str(discord_id)
                    linked_entry = linked_by_discord.setdefault(discord_id, {"discord_id": discord_id, "discord_name": discord_names.get(discord_id, f"Discord ID {discord_id}"), "accounts": []})
                    linked_entry["accounts"].append({"player_name": player_name, "name": player_name, "tag": player_tag, "clan_label": clan_label})
                else:
                    unlinked_rows.append({"player_name": player_name, "name": player_name, "tag": player_tag, "clan_label": clan_label})

            linked_rows = sorted(linked_by_discord.values(), key=lambda row: (str(row.get("discord_name", "")).lower(), str(row.get("discord_id", ""))))
            unlinked_rows = sorted(unlinked_rows, key=lambda row: str(row.get("player_name", "")).lower())

            clan_blocks[block_key]["linked"] = linked_rows
            clan_blocks[block_key]["unlinked"] = unlinked_rows
            clan_blocks[block_key]["unique_members"] = len(linked_rows)
            clan_blocks[block_key]["total_accounts"] = sum(len(row.get("accounts", [])) for row in linked_rows)

        total_links = clan_blocks["main"]["total_accounts"] + clan_blocks["feeder"]["total_accounts"]
        no_link_total = len(clan_blocks["main"]["unlinked"]) + len(clan_blocks["feeder"]["unlinked"])
        audit_data = {"main": clan_blocks["main"], "feeder": clan_blocks["feeder"], "stats": {"guild_members": len([m for m in guild.members if not m.bot]), "main_linked": len(clan_blocks["main"]["linked"]), "feeder_linked": len(clan_blocks["feeder"]["linked"]), "no_link": no_link_total, "total_links": total_links}, "warnings": warnings}

        try:
            image_buffer = await create_link_audit_image(audit_data)
            file = discord.File(fp=image_buffer, filename="link_audit.png")
            embed = discord.Embed(
                title="🧩 G.A.I.A Link Audit",
                description=(f"**Main linked:** {len(clan_blocks['main']['linked'])}\n" f"**Feeder linked:** {len(clan_blocks['feeder']['linked'])}\n" f"**Main missing links:** {len(clan_blocks['main']['unlinked'])}\n" f"**Feeder missing links:** {len(clan_blocks['feeder']['unlinked'])}"),
                color=0x38BDF8,
            )
            embed.set_image(url="attachment://link_audit.png")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            return
        except Exception as e:
            print(f"[LINKAUDIT RENDER ERROR] {type(e).__name__}: {e}")

        await interaction.followup.send(
            f"**🧩 G.A.I.A Link Audit**\n"
            f"Main linked: **{len(clan_blocks['main']['linked'])}**\n"
            f"Feeder linked: **{len(clan_blocks['feeder']['linked'])}**\n"
            f"Main missing links: **{len(clan_blocks['main']['unlinked'])}**\n"
            f"Feeder missing links: **{len(clan_blocks['feeder']['unlinked'])}**",
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

