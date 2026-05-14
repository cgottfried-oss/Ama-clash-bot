from __future__ import annotations

import html as html_lib

import discord
from discord import app_commands

from html_renderer import render_html_to_png_buffer


SNAPSHOT_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0;
  width: 1400px;
  background: radial-gradient(circle at top left, #596b9a 0%, #39476b 40%, #232c45 75%, #182033 100%);
  font-family: Arial, Helvetica, sans-serif;
  color: white;
}
.card {
  width: 1340px;
  margin: 30px;
  border-radius: 28px;
  padding: 28px;
  background: linear-gradient(180deg, rgba(59,73,110,.95), rgba(24,31,52,.96));
  border: 3px solid rgba(255,255,255,.14);
  box-shadow: 0 18px 50px rgba(0,0,0,.45);
}
.header {
  display: grid;
  grid-template-columns: 170px 1fr;
  gap: 24px;
  align-items: center;
  margin-bottom: 24px;
}
.badge {
  width: 170px;
  height: 170px;
  object-fit: contain;
}
.title {
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 10px;
  text-shadow: 0 4px 0 rgba(0,0,0,.35);
}
.subtitle {
  font-size: 24px;
  opacity: .92;
  font-weight: 700;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat {
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(83,98,143,.92), rgba(42,52,88,.95));
  border: 2px solid rgba(255,255,255,.10);
}
.label {
  font-size: 15px;
  font-weight: 800;
  opacity: .8;
  margin-bottom: 6px;
}
.value {
  font-size: 28px;
  font-weight: 900;
}
.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}
.section {
  border-radius: 20px;
  padding: 20px;
  background: rgba(18,24,41,.58);
  border: 2px solid rgba(255,255,255,.08);
}
.section-title {
  font-size: 30px;
  font-weight: 900;
  margin-bottom: 14px;
}
ul {
  margin: 0;
  padding-left: 22px;
}
li {
  margin-bottom: 10px;
  font-size: 20px;
  line-height: 1.3;
  font-weight: 700;
}
.footer {
  margin-top: 22px;
  font-size: 22px;
  font-weight: 800;
  text-align: center;
  opacity: .92;
}
"""


def build_snapshot_html(clan: dict, requirements: str):
    wins = clan.get("warWins", 0)
    losses = clan.get("warLosses", 0)
    ties = clan.get("warTies", 0)
    total = wins + losses + ties
    win_rate = round((wins / total) * 100, 1) if total else 0

    badge = clan.get("badgeUrls", {}).get("large", "")
    capital_hall = clan.get("clanCapital", {}).get("capitalHallLevel", "?")

    return f"""
    <html>
    <head>
      <style>{SNAPSHOT_CSS}</style>
    </head>
    <body>
      <div class='card'>
        <div class='header'>
          <img class='badge' src='{html_lib.escape(badge)}'>
          <div>
            <div class='title'>{html_lib.escape(clan.get('name', 'Unknown Clan'))}</div>
            <div class='subtitle'>
              {html_lib.escape(clan.get('tag', ''))} • Level {clan.get('clanLevel', '?')} • {html_lib.escape(clan.get('warLeague', {}).get('name', 'Unranked'))}
            </div>
          </div>
        </div>

        <div class='grid'>
          <div class='stat'><div class='label'>Members</div><div class='value'>{clan.get('members', '?')}/50</div></div>
          <div class='stat'><div class='label'>Location</div><div class='value'>{html_lib.escape(clan.get('location', {}).get('name', 'International'))}</div></div>
          <div class='stat'><div class='label'>Language</div><div class='value'>English</div></div>

          <div class='stat'><div class='label'>Capital Hall</div><div class='value'>{capital_hall}</div></div>
          <div class='stat'><div class='label'>War Frequency</div><div class='value'>{html_lib.escape(clan.get('warFrequency', 'Unknown'))}</div></div>
          <div class='stat'><div class='label'>Status</div><div class='value'>{html_lib.escape(clan.get('type', 'Unknown'))}</div></div>

          <div class='stat'><div class='label'>War Record</div><div class='value'>{wins}W / {losses}L / {ties}D</div></div>
          <div class='stat'><div class='label'>Win Rate</div><div class='value'>{win_rate}%</div></div>
          <div class='stat'><div class='label'>Requirements</div><div class='value'>{html_lib.escape(requirements)}</div></div>
        </div>

        <div class='columns'>
          <div class='section'>
            <div class='section-title'>What We Provide</div>
            <ul>
              <li>Relaxed, but still competitive</li>
              <li>Heroes can be down for regular war (Feeder)</li>
              <li>Heroes should be up for CWL (Main)</li>
              <li>Fast donations</li>
              <li>Completed Clan Games</li>
              <li>Good communication</li>
              <li>Friendly, relaxed atmosphere</li>
              <li>Help & support for newer players</li>
            </ul>
          </div>

          <div class='section'>
            <div class='section-title'>What We Are Looking For</div>
            <ul>
              <li>Active daily</li>
              <li>Participation in Clan Games</li>
              <li>Capital Raids participation</li>
              <li>Clan War & CWL participation</li>
              <li>English speaking</li>
            </ul>
          </div>
        </div>

        <div class='footer'>Discord: https://discord.gg/x6X2MrzZE4</div>
      </div>
    </body>
    </html>
    """


def register_clan_snapshot_command(
    tree: app_commands.CommandTree,
    *,
    get_cached_or_fetch,
    normalize_tag,
    clan_tags,
    clash_api_base: str = "https://api.clashofclans.com/v1",
):
    @tree.command(name="clansnapshot", description="Generate a clan snapshot recruitment card")
    @app_commands.describe(clan="Choose which stored clan snapshot to display")
    @app_commands.choices(clan=[
        app_commands.Choice(name="Main Clan", value="main"),
        app_commands.Choice(name="Feeder Clan", value="feeder"),
    ])
    async def clansnapshot(interaction: discord.Interaction, clan: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True)

        try:
            selected_tag = clan_tags[0] if clan.value == "main" else clan_tags[1]
            normalized_tag = normalize_tag(selected_tag)

            encoded_tag = normalized_tag.replace("#", "%23")
            url = f"{clash_api_base}/clans/{encoded_tag}"

            clan_data = await get_cached_or_fetch(
                f"clan_snapshot_{normalized_tag}",
                url,
                ttl=120,
            )

            if not clan_data:
                await interaction.followup.send("❌ Failed to fetch clan data.", ephemeral=True)
                return

            requirements = "Town Hall 14+" if clan.value == "main" else "Town Hall 9+"

            html = build_snapshot_html(clan_data, requirements)

            buffer = await render_html_to_png_buffer(
                html,
                width=1400,
                height=1250,
                selector="body",
                wait_ms=700,
                timeout_ms=15000,
            )

            file = discord.File(buffer, filename="clan_snapshot.png")

            embed = discord.Embed(
                title=f"{clan_data.get('name')} — Clan Snapshot",
                color=discord.Color.blurple(),
            )
            embed.set_image(url="attachment://clan_snapshot.png")

            await interaction.followup.send(embed=embed, file=file)

        except Exception as exc:
            print(f"[CLAN SNAPSHOT ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send(
                "❌ Failed to generate clan snapshot.",
                ephemeral=True,
            )

    return clansnapshot
