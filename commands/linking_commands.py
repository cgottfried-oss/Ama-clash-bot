from __future__ import annotations

import asyncio
import html as html_lib
import io
import os
import traceback
from datetime import datetime, timezone

import discord
from discord import app_commands
from playwright.async_api import async_playwright


_LINKAUDIT_RENDER_SEMAPHORE = asyncio.Semaphore(1)


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

    async def create_link_audit_image(audit_data: dict) -> io.BytesIO:
        """Render the link audit as a Discord-ready PNG."""

        def esc(value) -> str:
            return html_lib.escape(str(value if value is not None else ""))

        def initials(name: str) -> str:
            parts = [p for p in str(name or "").replace("_", " ").split() if p]
            return ("".join(p[0] for p in parts[:2]).upper() or "?")[:2]

        def render_tag_chips(accounts: list[dict]) -> str:
            chips = []
            for account in accounts or []:
                tag = esc(account.get("tag", ""))
                player_name = esc(account.get("player_name") or account.get("name") or "Unknown")
                chips.append(f'<span class="tag-chip">{player_name} <b>{tag}</b></span>')
            return "".join(chips) or '<span class="muted">No tag data</span>'

        def render_linked_rows(rows: list[dict], empty_text: str) -> str:
            if not rows:
                return f'<div class="empty">{esc(empty_text)}</div>'

            output = []
            for index, row in enumerate(rows, start=1):
                display = row.get("discord_name") or row.get("display_name") or row.get("name") or "Unknown"
                output.append(
                    f"""
                    <div class="row linked-row">
                        <div class="index">{index}</div>
                        <div class="avatar">{esc(initials(display))}</div>
                        <div class="row-main">
                            <div class="row-title">{esc(display)}</div>
                            <div class="chips">{render_tag_chips(row.get("accounts", []))}</div>
                        </div>
                        <div class="badge linked">Linked</div>
                    </div>
                    """
                )
            return "".join(output)

        def render_unlinked_rows(rows: list[dict], empty_text: str) -> str:
            if not rows:
                return f'<div class="empty">{esc(empty_text)}</div>'

            output = []
            for index, row in enumerate(rows, start=1):
                name = row.get("player_name") or row.get("name") or "Unknown"
                tag = row.get("tag", "")
                output.append(
                    f"""
                    <div class="row unlinked-row">
                        <div class="index">{index}</div>
                        <div class="avatar danger">{esc(initials(name))}</div>
                        <div class="row-main">
                            <div class="row-title">{esc(name)}</div>
                            <div class="row-sub">{esc(tag)}</div>
                        </div>
                        <div class="badge missing">No Link</div>
                    </div>
                    """
                )
            return "".join(output)

        main = audit_data.get("main", {})
        feeder = audit_data.get("feeder", {})
        stats = audit_data.get("stats", {})
        warnings = audit_data.get("warnings", [])

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        main_linked = main.get("linked", [])
        feeder_linked = feeder.get("linked", [])
        main_unlinked = main.get("unlinked", [])
        feeder_unlinked = feeder.get("unlinked", [])

        warning_html = "".join(f'<div class="warning">⚠️ {esc(w)}</div>' for w in warnings)
        if not warning_html:
            warning_html = '<div class="success">✅ Clash API data loaded successfully.</div>'

        html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                * {{
                    box-sizing: border-box;
                }}

                body {{
                    margin: 0;
                    padding: 34px;
                    width: 1560px;
                    background:
                        radial-gradient(circle at top left, rgba(56, 189, 248, 0.22), transparent 34%),
                        radial-gradient(circle at bottom right, rgba(168, 85, 247, 0.20), transparent 36%),
                        #07111f;
                    font-family: Inter, Arial, Helvetica, sans-serif;
                    color: #e5f4ff;
                }}

                .card {{
                    width: 1490px;
                    border: 1px solid rgba(148, 163, 184, 0.30);
                    border-radius: 32px;
                    padding: 34px;
                    background: rgba(15, 23, 42, 0.94);
                    box-shadow: 0 28px 80px rgba(0, 0, 0, 0.42);
                }}

                .header {{
                    display: flex;
                    justify-content: space-between;
                    gap: 22px;
                    align-items: flex-start;
                    margin-bottom: 26px;
                }}

                .eyebrow {{
                    color: #38bdf8;
                    font-size: 22px;
                    font-weight: 800;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    margin-bottom: 8px;
                }}

                h1 {{
                    margin: 0;
                    font-size: 58px;
                    line-height: 1;
                    letter-spacing: -0.04em;
                }}

                .subtitle {{
                    margin-top: 12px;
                    color: #a9bdd5;
                    font-size: 24px;
                }}

                .generated {{
                    min-width: 290px;
                    padding: 18px 20px;
                    border-radius: 22px;
                    background: rgba(30, 41, 59, 0.88);
                    border: 1px solid rgba(148, 163, 184, 0.20);
                    text-align: right;
                    color: #cbd5e1;
                    font-size: 19px;
                }}

                .generated b {{
                    display: block;
                    color: #f8fafc;
                    font-size: 22px;
                    margin-top: 4px;
                }}

                .stats {{
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: 16px;
                    margin-bottom: 24px;
                }}

                .stat {{
                    padding: 20px;
                    border-radius: 24px;
                    background: rgba(30, 41, 59, 0.82);
                    border: 1px solid rgba(148, 163, 184, 0.18);
                }}

                .stat .num {{
                    font-size: 42px;
                    font-weight: 900;
                    color: #f8fafc;
                    line-height: 1;
                }}

                .stat .label {{
                    margin-top: 8px;
                    color: #9fb2c8;
                    font-size: 18px;
                    font-weight: 700;
                }}

                .grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 18px;
                    align-items: start;
                }}

                .panel {{
                    border-radius: 26px;
                    background: rgba(2, 6, 23, 0.54);
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    overflow: hidden;
                }}

                .panel-head {{
                    padding: 22px;
                    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
                    background: rgba(15, 23, 42, 0.70);
                }}

                .panel-title {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 12px;
                    font-size: 28px;
                    font-weight: 900;
                }}

                .panel-tag {{
                    color: #93c5fd;
                    font-size: 17px;
                    margin-top: 6px;
                    font-weight: 700;
                }}

                .pill {{
                    padding: 7px 12px;
                    border-radius: 999px;
                    background: rgba(56, 189, 248, 0.14);
                    border: 1px solid rgba(56, 189, 248, 0.32);
                    color: #7dd3fc;
                    font-size: 17px;
                    font-weight: 900;
                    white-space: nowrap;
                }}

                .mini-stats {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                    margin-top: 16px;
                }}

                .mini {{
                    border-radius: 16px;
                    padding: 12px;
                    background: rgba(30, 41, 59, 0.58);
                    color: #9fb2c8;
                    font-size: 14px;
                    font-weight: 800;
                }}

                .mini b {{
                    display: block;
                    font-size: 24px;
                    color: #f8fafc;
                    margin-bottom: 3px;
                }}

                .rows {{
                    padding: 14px;
                }}

                .section-label {{
                    margin: 10px 8px 12px;
                    color: #cbd5e1;
                    font-size: 18px;
                    font-weight: 900;
                }}

                .row {{
                    display: grid;
                    grid-template-columns: 42px 48px minmax(0, 1fr) auto;
                    gap: 12px;
                    align-items: center;
                    padding: 12px;
                    margin-bottom: 10px;
                    border-radius: 18px;
                    background: rgba(15, 23, 42, 0.78);
                    border: 1px solid rgba(148, 163, 184, 0.13);
                }}

                .index {{
                    color: #64748b;
                    font-size: 17px;
                    font-weight: 900;
                    text-align: center;
                }}

                .avatar {{
                    width: 48px;
                    height: 48px;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, rgba(56, 189, 248, 0.95), rgba(99, 102, 241, 0.95));
                    color: white;
                    font-size: 17px;
                    font-weight: 900;
                }}

                .avatar.danger {{
                    background: linear-gradient(135deg, rgba(248, 113, 113, 0.95), rgba(251, 146, 60, 0.95));
                }}

                .row-main {{
                    min-width: 0;
                }}

                .row-title {{
                    color: #f8fafc;
                    font-size: 20px;
                    font-weight: 900;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}

                .row-sub {{
                    color: #94a3b8;
                    font-size: 18px;
                    margin-top: 3px;
                    font-weight: 800;
                }}

                .chips {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    margin-top: 7px;
                }}

                .tag-chip {{
                    display: inline-block;
                    padding: 5px 9px;
                    border-radius: 999px;
                    background: rgba(56, 189, 248, 0.11);
                    border: 1px solid rgba(56, 189, 248, 0.20);
                    color: #bae6fd;
                    font-size: 14px;
                    font-weight: 800;
                    max-width: 310px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }}

                .badge {{
                    padding: 8px 10px;
                    border-radius: 999px;
                    font-size: 14px;
                    font-weight: 900;
                    white-space: nowrap;
                }}

                .badge.linked {{
                    background: rgba(34, 197, 94, 0.14);
                    color: #86efac;
                    border: 1px solid rgba(34, 197, 94, 0.28);
                }}

                .badge.missing {{
                    background: rgba(248, 113, 113, 0.14);
                    color: #fecaca;
                    border: 1px solid rgba(248, 113, 113, 0.30);
                }}

                .empty {{
                    padding: 18px;
                    border-radius: 18px;
                    background: rgba(15, 23, 42, 0.78);
                    color: #94a3b8;
                    font-size: 18px;
                    font-weight: 800;
                    text-align: center;
                }}

                .muted {{
                    color: #94a3b8;
                    font-weight: 800;
                }}

                .footer {{
                    margin-top: 20px;
                    display: grid;
                    gap: 10px;
                }}

                .warning, .success {{
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 18px;
                    font-weight: 800;
                }}

                .warning {{
                    color: #fde68a;
                    background: rgba(245, 158, 11, 0.10);
                    border: 1px solid rgba(245, 158, 11, 0.22);
                }}

                .success {{
                    color: #86efac;
                    background: rgba(34, 197, 94, 0.10);
                    border: 1px solid rgba(34, 197, 94, 0.22);
                }}

                .system {{
                    color: #64748b;
                    font-size: 16px;
                    font-weight: 800;
                    text-align: center;
                    margin-top: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <div>
                        <div class="eyebrow">G.A.I.A Link Audit</div>
                        <h1>Discord ↔ Clash Account Overview</h1>
                        <div class="subtitle">Main Clan and Feeder Clan links, plus clan accounts that still need a Discord link.</div>
                    </div>
                    <div class="generated">
                        Generated
                        <b>{esc(generated_at)}</b>
                    </div>
                </div>

                <div class="stats">
                    <div class="stat">
                        <div class="num">{int(stats.get("guild_members", 0))}</div>
                        <div class="label">Discord Members</div>
                    </div>
                    <div class="stat">
                        <div class="num">{len(main_linked)}</div>
                        <div class="label">Main Linked</div>
                    </div>
                    <div class="stat">
                        <div class="num">{len(feeder_linked)}</div>
                        <div class="label">Feeder Linked</div>
                    </div>
                    <div class="stat">
                        <div class="num">{len(main_unlinked) + len(feeder_unlinked)}</div>
                        <div class="label">No Link</div>
                    </div>
                    <div class="stat">
                        <div class="num">{int(stats.get("total_links", 0))}</div>
                        <div class="label">Total Linked Tags</div>
                    </div>
                </div>

                <div class="grid">
                    <div class="panel">
                        <div class="panel-head">
                            <div class="panel-title">
                                🛡️ Main Clan
                                <span class="pill">{len(main_linked)} Linked</span>
                            </div>
                            <div class="panel-tag">{esc(main.get("tag", "Main Clan"))}</div>
                            <div class="mini-stats">
                                <div class="mini"><b>{int(main.get("unique_members", len(main_linked)))}</b>Discord Users</div>
                                <div class="mini"><b>{int(main.get("total_accounts", len(main_linked)))}</b>Accounts</div>
                                <div class="mini"><b>{len(main_unlinked)}</b>Missing</div>
                            </div>
                        </div>
                        <div class="rows">
                            <div class="section-label">Linked Discord Users</div>
                            {render_linked_rows(main_linked, "No linked Main Clan accounts found.")}
                        </div>
                    </div>

                    <div class="panel">
                        <div class="panel-head">
                            <div class="panel-title">
                                🐉 Feeder Clan
                                <span class="pill">{len(feeder_linked)} Linked</span>
                            </div>
                            <div class="panel-tag">{esc(feeder.get("tag", "Feeder Clan"))}</div>
                            <div class="mini-stats">
                                <div class="mini"><b>{int(feeder.get("unique_members", len(feeder_linked)))}</b>Discord Users</div>
                                <div class="mini"><b>{int(feeder.get("total_accounts", len(feeder_linked)))}</b>Accounts</div>
                                <div class="mini"><b>{len(feeder_unlinked)}</b>Missing</div>
                            </div>
                        </div>
                        <div class="rows">
                            <div class="section-label">Linked Discord Users</div>
                            {render_linked_rows(feeder_linked, "No linked Feeder Clan accounts found.")}
                        </div>
                    </div>

                    <div class="panel">
                        <div class="panel-head">
                            <div class="panel-title">
                                ⛓️ Missing Links
                                <span class="pill">{len(main_unlinked) + len(feeder_unlinked)} Missing</span>
                            </div>
                            <div class="panel-tag">Clan accounts missing Discord links</div>
                            <div class="mini-stats">
                                <div class="mini"><b>{len(main_unlinked)}</b>Main Clan</div>
                                <div class="mini"><b>{len(feeder_unlinked)}</b>Feeder Clan</div>
                                <div class="mini"><b>{len(main_unlinked) + len(feeder_unlinked)}</b>Total</div>
                            </div>
                        </div>
                        <div class="rows">
                            <div class="section-label">Main Clan Missing Links</div>
                            {render_unlinked_rows(main_unlinked, "Every Main Clan account is linked.")}
                            <div class="section-label">Feeder Clan Missing Links</div>
                            {render_unlinked_rows(feeder_unlinked, "Every Feeder Clan account is linked.")}
                        </div>
                    </div>
                </div>

                <div class="footer">
                    {warning_html}
                </div>
                <div class="system">Keep accounts linked to earn rewards and stay on leaderboards. · G.A.I.A System Audit</div>
            </div>
        </body>
        </html>
        """

        async with _LINKAUDIT_RENDER_SEMAPHORE:
            playwright = None
            browser = None
            context = None
            page = None

            try:
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-setuid-sandbox",
                        "--disable-background-networking",
                        "--disable-extensions",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1560, "height": 1200},
                    device_scale_factor=1,
                )
                page = await context.new_page()
                page.set_default_timeout(20000)

                await page.emulate_media(media="screen")
                await page.set_content(html, wait_until="domcontentloaded", timeout=20000)

                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception as e:
                    print(f"[LINKAUDIT RENDER WARN] networkidle skipped: {type(e).__name__}: {e}")

                await page.wait_for_timeout(700)

                dims = await page.evaluate(
                    """() => {
                        const body = document.body;
                        const doc = document.documentElement;
                        return {
                            width: Math.max(body.scrollWidth, body.offsetWidth, doc.clientWidth, doc.scrollWidth, doc.offsetWidth),
                            height: Math.max(body.scrollHeight, body.offsetHeight, doc.clientHeight, doc.scrollHeight, doc.offsetHeight)
                        };
                    }"""
                )

                viewport_width = max(1560, min(int(dims.get("width", 1560)) + 40, 2200))
                viewport_height = max(1200, min(int(dims.get("height", 1200)) + 80, 12000))
                await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                await page.wait_for_timeout(150)

                png_bytes = await page.screenshot(full_page=True, timeout=20000)
                image_buffer = io.BytesIO(png_bytes)
                image_buffer.seek(0)
                return image_buffer

            except Exception as e:
                print(f"[LINKAUDIT RENDER ERROR] {type(e).__name__}: {e}")
                traceback.print_exc()
                raise

            finally:
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if browser is not None:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                if playwright is not None:
                    try:
                        await playwright.stop()
                    except Exception:
                        pass

    def build_linkaudit_text_details(audit_data: dict) -> str:
        """Fallback file that still shows actual linked/missing member rows if PNG rendering fails."""

        def rows(title: str, linked_rows: list[dict], unlinked_rows: list[dict]) -> list[str]:
            output = [f"## {title}", "", "### Linked Discord users"]

            if linked_rows:
                for row in linked_rows:
                    discord_name = row.get("discord_name") or row.get("display_name") or row.get("name") or "Unknown"
                    account_text = ", ".join(
                        f"{account.get('player_name') or account.get('name') or 'Unknown'} ({account.get('tag', '')})"
                        for account in row.get("accounts", [])
                    )
                    output.append(f"- **{discord_name}**: {account_text or 'No tag data'}")
            else:
                output.append("- None")

            output.extend(["", "### Clan accounts missing Discord links"])

            if unlinked_rows:
                for row in unlinked_rows:
                    output.append(f"- **{row.get('player_name') or row.get('name') or 'Unknown'}** ({row.get('tag', '')})")
            else:
                output.append("- None")

            output.append("")
            return output

        main = audit_data.get("main", {})
        feeder = audit_data.get("feeder", {})
        stats = audit_data.get("stats", {})
        warnings = audit_data.get("warnings", [])

        lines = [
            "# G.A.I.A Link Audit Details",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Summary",
            f"- Discord members scanned: {int(stats.get('guild_members', 0))}",
            f"- Main linked Discord users: {len(main.get('linked', []))}",
            f"- Feeder linked Discord users: {len(feeder.get('linked', []))}",
            f"- Main missing links: {len(main.get('unlinked', []))}",
            f"- Feeder missing links: {len(feeder.get('unlinked', []))}",
            f"- Total linked Clash tags: {int(stats.get('total_links', 0))}",
            "",
        ]

        lines += rows("Main Clan", main.get("linked", []), main.get("unlinked", []))
        lines += rows("Feeder Clan", feeder.get("linked", []), feeder.get("unlinked", []))

        if warnings:
            lines += ["## Warnings"]
            lines += [f"- {warning}" for warning in warnings]
            lines.append("")

        return "\n".join(lines)

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

        discord_names = {
            str(member.id): member.display_name
            for member in guild.members
            if not member.bot
        }

        clan_blocks = {
            "main": {
                "label": "Main Clan",
                "tag": normalized_main_tag or "Main Clan",
                "linked": [],
                "unlinked": [],
                "unique_members": 0,
                "total_accounts": 0,
            },
            "feeder": {
                "label": "Feeder Clan",
                "tag": "Feeder Clan",
                "linked": [],
                "unlinked": [],
                "unique_members": 0,
                "total_accounts": 0,
            },
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

            try:
                _, clan_members = await fetch_clan_data(clan_tag)
            except Exception as e:
                print(f"[LINKAUDIT CLAN FETCH ERROR] {clan_tag}: {type(e).__name__}: {e}")
                traceback.print_exc()
                warnings.append(f"Could not fetch members for {clan_label} ({clan_tag}).")
                continue

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
                    linked_entry = linked_by_discord.setdefault(
                        discord_id,
                        {
                            "discord_id": discord_id,
                            "discord_name": discord_names.get(discord_id, f"Discord ID {discord_id}"),
                            "accounts": [],
                        },
                    )
                    linked_entry["accounts"].append(
                        {
                            "player_name": player_name,
                            "name": player_name,
                            "tag": player_tag,
                            "clan_label": clan_label,
                        }
                    )
                else:
                    unlinked_rows.append(
                        {
                            "player_name": player_name,
                            "name": player_name,
                            "tag": player_tag,
                            "clan_label": clan_label,
                        }
                    )

            linked_rows = sorted(
                linked_by_discord.values(),
                key=lambda row: (str(row.get("discord_name", "")).lower(), str(row.get("discord_id", ""))),
            )
            unlinked_rows = sorted(unlinked_rows, key=lambda row: str(row.get("player_name", "")).lower())

            clan_blocks[block_key]["linked"] = linked_rows
            clan_blocks[block_key]["unlinked"] = unlinked_rows
            clan_blocks[block_key]["unique_members"] = len(linked_rows)
            clan_blocks[block_key]["total_accounts"] = sum(len(row.get("accounts", [])) for row in linked_rows)

        total_links = clan_blocks["main"]["total_accounts"] + clan_blocks["feeder"]["total_accounts"]
        no_link_total = len(clan_blocks["main"]["unlinked"]) + len(clan_blocks["feeder"]["unlinked"])

        audit_data = {
            "main": clan_blocks["main"],
            "feeder": clan_blocks["feeder"],
            "stats": {
                "guild_members": len([member for member in guild.members if not member.bot]),
                "main_linked": len(clan_blocks["main"]["linked"]),
                "feeder_linked": len(clan_blocks["feeder"]["linked"]),
                "no_link": no_link_total,
                "total_links": total_links,
            },
            "warnings": warnings,
        }

        try:
            image_buffer = await create_link_audit_image(audit_data)
            file = discord.File(fp=image_buffer, filename="link_audit.png")

            embed = discord.Embed(
                title="G.A.I.A Link Audit",
                description=(
                    f"**Main linked:** {len(clan_blocks['main']['linked'])}\n"
                    f"**Feeder linked:** {len(clan_blocks['feeder']['linked'])}\n"
                    f"**Main missing links:** {len(clan_blocks['main']['unlinked'])}\n"
                    f"**Feeder missing links:** {len(clan_blocks['feeder']['unlinked'])}"
                ),
                color=0x38BDF8,
            )
            embed.set_image(url="attachment://link_audit.png")

            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            return

        except Exception as e:
            print(f"[LINKAUDIT RENDER FALLBACK] {type(e).__name__}: {e}")
            traceback.print_exc()

            details = build_linkaudit_text_details(audit_data)
            details_buffer = io.BytesIO(details.encode("utf-8"))
            details_buffer.seek(0)
            details_file = discord.File(fp=details_buffer, filename="link_audit_details.md")

            await interaction.followup.send(
                (
                    "⚠️ **G.A.I.A Link Audit image render failed**, but I attached the full member/tag audit "
                    "instead of only counts.\n\n"
                    f"Main linked: **{len(clan_blocks['main']['linked'])}**\n"
                    f"Feeder linked: **{len(clan_blocks['feeder']['linked'])}**\n"
                    f"Main missing links: **{len(clan_blocks['main']['unlinked'])}**\n"
                    f"Feeder missing links: **{len(clan_blocks['feeder']['unlinked'])}**"
                ),
                file=details_file,
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
            ", ".join(f"{entry['name']} ({entry['tag']})" for entry in tags)
            if tags else
            "None"
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
                f"Already linked to {tag}",
                ephemeral=True,
            )
            return

        encoded_tag = tag.replace("#", "%23")
        url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"
        data = await get_cached_or_fetch(f"player_{tag}", url, ttl=300)

        if not data:
            await interaction.response.send_message(
                "❌ Could not fetch player. Check the tag.",
                ephemeral=True,
            )
            return

        player_name = data.get("name", "Unknown")

        def _update_linked(data):
            data = normalize_linked_data(data)
            data.setdefault(user_id, [])

            if not any(normalize_tag(entry["tag"]) == tag for entry in data[user_id]):
                data[user_id].append({"tag": tag, "name": player_name})

            return data

        await update_json_file(LINKED_FILE, _update_linked)

        await interaction.response.send_message(
            f"✅ Linked **{player_name}** ({tag})",
            ephemeral=True,
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
                entry
                for entry in entries
                if normalize_tag(entry["tag"]) != tag
            ]

            if not data[user_id]:
                data.pop(user_id, None)

            return data

        await update_json_file(LINKED_FILE, _update_unlinked)

        await interaction.followup.send(
            f"✅ Unlinked {tag} from your Discord.",
            ephemeral=True,
        )
