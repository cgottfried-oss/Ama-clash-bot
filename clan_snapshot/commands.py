from __future__ import annotations

import html as html_lib

import discord
from discord import app_commands

from html_renderer import render_html_to_png_buffer


SNAPSHOT_CSS = """
* { box-sizing: border-box; }
body { margin: 0; width: 1400px; min-height: 1120px; font-family: Arial, Helvetica, sans-serif; color: white; background: radial-gradient(circle at 8% 8%, rgba(255, 210, 75, .35) 0%, rgba(255, 210, 75, 0) 22%), radial-gradient(circle at 92% 10%, rgba(168, 86, 255, .30) 0%, rgba(168, 86, 255, 0) 26%), radial-gradient(circle at 50% 100%, rgba(60, 185, 255, .18) 0%, rgba(60, 185, 255, 0) 42%), linear-gradient(135deg, #111827 0%, #1a2440 43%, #111827 100%); overflow: hidden; }
body::before { content: ""; position: fixed; inset: -120px; background: linear-gradient(115deg, rgba(255,255,255,.055) 0 2px, transparent 2px 90px), linear-gradient(25deg, rgba(255,255,255,.04) 0 2px, transparent 2px 110px); opacity: .7; transform: rotate(-2deg); }
.card { position: relative; width: 1340px; margin: 30px; border-radius: 34px; padding: 30px; background: linear-gradient(180deg, rgba(48, 58, 94, .92), rgba(14, 20, 38, .96)), radial-gradient(circle at 50% 0%, rgba(255,255,255,.18), transparent 55%); border: 3px solid rgba(255,255,255,.18); box-shadow: 0 30px 70px rgba(0,0,0,.55), inset 0 2px 0 rgba(255,255,255,.16), inset 0 -2px 0 rgba(0,0,0,.35); overflow: hidden; }
.card::before { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(255,198,48,.95), rgba(151,70,255,.9), rgba(55,178,255,.85)); height: 9px; }
.header { position: relative; display: grid; grid-template-columns: 205px 1fr 235px; gap: 24px; align-items: center; margin-bottom: 24px; z-index: 1; }
.badge-wrap { width: 205px; height: 205px; border-radius: 32px; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle, rgba(255,215,76,.28), rgba(151,70,255,.12) 55%, rgba(0,0,0,.28)); border: 2px solid rgba(255,255,255,.16); box-shadow: inset 0 2px 0 rgba(255,255,255,.15), 0 12px 28px rgba(0,0,0,.38), 0 0 34px rgba(151,70,255,.22); }
.badge { width: 182px; height: 182px; object-fit: contain; filter: drop-shadow(0 10px 10px rgba(0,0,0,.45)); }
.title { font-size: 62px; font-weight: 1000; line-height: .96; margin-bottom: 12px; letter-spacing: .5px; text-transform: uppercase; text-shadow: 0 5px 0 rgba(0,0,0,.42), 0 0 24px rgba(255,255,255,.12); }
.subtitle { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.pill { display: inline-flex; align-items: center; gap: 7px; border-radius: 999px; padding: 8px 15px; font-size: 21px; font-weight: 900; background: rgba(8,13,28,.48); border: 1px solid rgba(255,255,255,.18); box-shadow: inset 0 1px 0 rgba(255,255,255,.10); }
.hero-stat { border-radius: 24px; padding: 18px; background: linear-gradient(180deg, rgba(255,198,48,.18), rgba(151,70,255,.16)); border: 2px solid rgba(255,255,255,.14); text-align: center; box-shadow: inset 0 2px 0 rgba(255,255,255,.12), 0 12px 25px rgba(0,0,0,.28); }
.hero-label { font-size: 16px; font-weight: 900; opacity: .78; text-transform: uppercase; letter-spacing: 1px; }
.hero-value { margin-top: 5px; font-size: 44px; font-weight: 1000; text-shadow: 0 4px 0 rgba(0,0,0,.35); }
.grid { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.stat { min-height: 96px; border-radius: 22px; padding: 15px 16px; background: linear-gradient(180deg, rgba(75, 91, 139, .82), rgba(31, 40, 72, .92)); border: 2px solid rgba(255,255,255,.12); box-shadow: inset 0 2px 0 rgba(255,255,255,.12), 0 8px 0 rgba(0,0,0,.20), 0 14px 22px rgba(0,0,0,.15); }
.stat.hot { border-color: rgba(255,198,48,.46); box-shadow: inset 0 2px 0 rgba(255,255,255,.14), 0 8px 0 rgba(0,0,0,.20), 0 0 24px rgba(255,198,48,.12); }
.stat.link-stat { grid-column: 2 / span 2; text-align: center; }
.label { font-size: 14px; font-weight: 1000; opacity: .72; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .8px; }
.value { font-size: 28px; line-height: 1.05; font-weight: 1000; text-shadow: 0 3px 0 rgba(0,0,0,.30); }
.value.link-value { font-size: 24px; white-space: nowrap; line-height: 1.16; }
.columns { position: relative; z-index: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.section { min-height: 330px; border-radius: 26px; padding: 24px; background: linear-gradient(180deg, rgba(10,16,33,.76), rgba(7,11,24,.88)); border: 2px solid rgba(255,255,255,.10); box-shadow: inset 0 2px 0 rgba(255,255,255,.08), 0 13px 26px rgba(0,0,0,.24); }
.section-title { display: inline-flex; align-items: center; gap: 10px; font-size: 32px; font-weight: 1000; margin-bottom: 16px; text-shadow: 0 4px 0 rgba(0,0,0,.40); }
ul { margin: 0; padding-left: 0; list-style: none; }
li { position: relative; margin-bottom: 11px; padding-left: 30px; font-size: 21px; line-height: 1.24; font-weight: 800; }
li::before { content: "✦"; position: absolute; left: 0; top: -1px; color: #ffd04a; text-shadow: 0 0 10px rgba(255,208,74,.5); }
.footer { position: relative; z-index: 1; margin-top: 24px; display: flex; align-items: center; justify-content: center; gap: 14px; font-size: 24px; font-weight: 1000; text-align: center; opacity: .97; }
.footer-pill { border-radius: 999px; padding: 12px 22px; background: linear-gradient(90deg, rgba(88,101,242,.75), rgba(151,70,255,.62)); border: 1px solid rgba(255,255,255,.18); box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 8px 20px rgba(0,0,0,.26); }
"""

CLAN_LINKS = {"#2CYV200G": "https://link.clashofclans.com/en?action=OpenClanProfile&tag=2CYV200G", "#PL0QC090": "https://link.clashofclans.com/en?action=OpenClanProfile&tag=PL0QC090"}
CLAN_MESSAGES = {
    "main": {
        "provide": ["Competitive CWL focus with a relaxed day-to-day vibe", "Heroes expected up for CWL and serious war hits", "Fast donations and completed Clan Games", "Organized communication through Discord", "Strong war record and public war log", "Friendly atmosphere without the sweat-lord drama", "Help with attacks, planning, and account growth"],
        "want": ["TH14+ non-rushed players", "Active daily and responsive in Discord", "CWL ready with heroes available", "Clan Games and Capital Raid participation", "War participation when opted in", "English speaking team players"],
    },
    "feeder": {
        "provide": ["Relaxed feeder environment for growing accounts", "Heroes can be down for regular wars", "No-hero wars and lower pressure practice", "Fast donations and completed Clan Games", "Help and support for newer players", "Pathway into the main clan when ready", "Friendly, patient, low-drama atmosphere"],
        "want": ["TH9+ non-rushed players", "Active daily or close to daily", "Willing to learn and improve attacks", "Clan Games and Capital Raid participation", "War participation if opted in", "English speaking and respectful"],
    },
}

def _fmt_type(value: str) -> str:
    mapping = {"open": "Open", "inviteOnly": "Invite Only", "closed": "Closed"}
    return mapping.get(str(value or ""), str(value or "Unknown").title())

def _fmt_war_frequency(value: str | None) -> str:
    if not value:
        return "Not Set"
    normalized = str(value).strip()
    mapping = {"unknown": "Not Set", "always": "Always", "moreThanOncePerWeek": "2x+ Weekly", "oncePerWeek": "Weekly", "lessThanOncePerWeek": "Casual", "never": "Never"}
    return mapping.get(normalized, normalized.replace("_", " ").title())

def _display_clan_link(clan_link: str, clan_tag: str) -> str:
    return f"Open Clan Profile • {clan_tag.replace('#', '')}"

def _render_list(items: list[str]) -> str:
    return "".join(f"<li>{html_lib.escape(item)}</li>" for item in items)

def build_snapshot_html(clan: dict, requirements: str, clan_link: str, clan_kind: str):
    wins = clan.get("warWins", 0); losses = clan.get("warLosses", 0); ties = clan.get("warTies", 0)
    total = wins + losses + ties
    win_rate = round((wins / total) * 100, 1) if total else 0
    badge = clan.get("badgeUrls", {}).get("large", "")
    capital_hall = clan.get("clanCapital", {}).get("capitalHallLevel", "?")
    war_frequency = html_lib.escape(_fmt_war_frequency(clan.get("warFrequency")))
    status = html_lib.escape(_fmt_type(clan.get("type", "Unknown")))
    raw_clan_tag = clan.get("tag", "")
    clan_name = html_lib.escape(clan.get("name", "Unknown Clan"))
    clan_tag = html_lib.escape(raw_clan_tag)
    clan_level = clan.get("clanLevel", "?")
    war_league = html_lib.escape(clan.get("warLeague", {}).get("name", "Unranked"))
    clan_link_display = html_lib.escape(_display_clan_link(clan_link, raw_clan_tag))
    messages = CLAN_MESSAGES.get(clan_kind, CLAN_MESSAGES["main"])
    return f"""
    <html><head><style>{SNAPSHOT_CSS}</style></head><body><div class='card'>
      <div class='header'><div class='badge-wrap'><img class='badge' src='{html_lib.escape(badge)}'></div><div><div class='title'>{clan_name}</div><div class='subtitle'><span class='pill'>{clan_tag}</span><span class='pill'>Level {clan_level}</span><span class='pill'>{war_league}</span></div></div><div class='hero-stat'><div class='hero-label'>Win Rate</div><div class='hero-value'>{win_rate}%</div></div></div>
      <div class='grid'>
        <div class='stat hot'><div class='label'>Members</div><div class='value'>{clan.get('members', '?')}/50</div></div>
        <div class='stat'><div class='label'>Location</div><div class='value'>{html_lib.escape(clan.get('location', {}).get('name', 'International'))}</div></div>
        <div class='stat'><div class='label'>Language</div><div class='value'>English</div></div>
        <div class='stat'><div class='label'>Status</div><div class='value'>{status}</div></div>
        <div class='stat hot'><div class='label'>Capital Hall</div><div class='value'>{capital_hall}</div></div>
        <div class='stat'><div class='label'>War Frequency</div><div class='value'>{war_frequency}</div></div>
        <div class='stat hot'><div class='label'>War Record</div><div class='value'>{wins}W / {losses}L / {ties}D</div></div>
        <div class='stat hot'><div class='label'>Requirements</div><div class='value'>{html_lib.escape(requirements)}</div></div>
        <div class='stat link-stat'><div class='label'>Clan Link</div><div class='value link-value'>{clan_link_display}</div></div>
      </div>
      <div class='columns'><div class='section'><div class='section-title'>What We Provide</div><ul>{_render_list(messages['provide'])}</ul></div><div class='section'><div class='section-title'>What We Want</div><ul>{_render_list(messages['want'])}</ul></div></div>
      <div class='footer'><span class='footer-pill'>Join the Discord: https://discord.gg/x6X2MrzZE4</span></div>
    </div></body></html>"""

def register_clan_snapshot_command(tree: app_commands.CommandTree, *, get_cached_or_fetch, normalize_tag, clan_tags, clash_api_base: str = "https://api.clashofclans.com/v1"):
    @tree.command(name="clansnapshot", description="Generate a clan snapshot recruitment card")
    @app_commands.describe(clan="Choose which stored clan snapshot to display")
    @app_commands.choices(clan=[app_commands.Choice(name="Main Clan", value="main"), app_commands.Choice(name="Feeder Clan", value="feeder")])
    async def clansnapshot(interaction: discord.Interaction, clan: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True)
        try:
            if not clan_tags:
                await interaction.followup.send("❌ No clan tags are configured.", ephemeral=True); return
            selected_tag = clan_tags[0] if clan.value == "main" else (clan_tags[1] if len(clan_tags) > 1 else clan_tags[0])
            normalized_tag = normalize_tag(selected_tag)
            encoded_tag = normalized_tag.replace("#", "%23")
            clan_data = await get_cached_or_fetch(f"clan_snapshot_{normalized_tag}", f"{clash_api_base}/clans/{encoded_tag}", ttl=120)
            if not clan_data:
                await interaction.followup.send("❌ Failed to fetch clan data.", ephemeral=True); return
            requirements = "Town Hall 14+" if clan.value == "main" else "Town Hall 9+"
            clan_link = CLAN_LINKS.get(normalized_tag, f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={normalized_tag.replace('#', '')}")
            buffer = await render_html_to_png_buffer(build_snapshot_html(clan_data, requirements, clan_link, clan.value), width=1400, height=1120, selector="body", wait_ms=700, timeout_ms=15000)
            file = discord.File(buffer, filename="clan_snapshot.png")
            embed = discord.Embed(title=f"{clan_data.get('name')} — Clan Snapshot", color=discord.Color.gold(), url=clan_link)
            embed.set_image(url="attachment://clan_snapshot.png")
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open Clan", url=clan_link))
            view.add_item(discord.ui.Button(label="Join Discord", url="https://discord.gg/x6X2MrzZE4"))
            await interaction.followup.send(embed=embed, file=file, view=view)
        except Exception as exc:
            print(f"[CLAN SNAPSHOT ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to generate clan snapshot.", ephemeral=True)
    return clansnapshot
