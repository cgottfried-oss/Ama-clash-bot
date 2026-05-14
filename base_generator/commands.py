from __future__ import annotations

import discord
from discord import app_commands

from .experimental import analyze_layout_link, compare_layout_links, official_link_generation_status
from .generator import generate_base_plan
from .renderer import build_base_plan_html
from .scorer import score_base
from .storage import save_base_entry, search_saved_bases

TH_CHOICES = [app_commands.Choice(name=f"TH{th}", value=th) for th in [14, 15, 16, 17]]
STYLE_CHOICES = [app_commands.Choice(name="War", value="war"), app_commands.Choice(name="CWL", value="cwl"), app_commands.Choice(name="Legends", value="legend"), app_commands.Choice(name="Farming", value="farming")]
META_CHOICES = [app_commands.Choice(name="Root Rider", value="root_rider"), app_commands.Choice(name="Fireball", value="fireball"), app_commands.Choice(name="Blimp", value="blimp"), app_commands.Choice(name="Air Spam", value="air_spam"), app_commands.Choice(name="Hybrid", value="hybrid")]
SYMMETRY_CHOICES = [app_commands.Choice(name="Ring", value="ring"), app_commands.Choice(name="Box", value="box"), app_commands.Choice(name="Diamond", value="diamond"), app_commands.Choice(name="Random", value="random")]

def _copy_link_is_plausible(link: str) -> bool:
    return link.startswith("https://link.clashofclans.com/") and ("OpenLayout" in link or "OpenPlayerLayout" in link)

def register_base_generator_commands(tree: app_commands.CommandTree, *, render_html_to_png_buffer, safe_load_json, safe_save_json, data_dir: str):
    @tree.command(name="basegen", description="Generate an anti-meta Clash base blueprint")
    @app_commands.describe(townhall="Town Hall level", style="Base type", anti_meta="Meta attack to defend against", symmetry="Layout style")
    @app_commands.choices(townhall=TH_CHOICES, style=STYLE_CHOICES, anti_meta=META_CHOICES, symmetry=SYMMETRY_CHOICES)
    async def basegen(interaction: discord.Interaction, townhall: app_commands.Choice[int], style: app_commands.Choice[str], anti_meta: app_commands.Choice[str], symmetry: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True)
        try:
            plan = generate_base_plan(townhall.value, style.value, anti_meta.value, symmetry.value)
            html = build_base_plan_html(plan)
            buffer = await render_html_to_png_buffer(html, width=1400, height=1320, selector="body", wait_ms=700, timeout_ms=15000)
            file = discord.File(buffer, filename="base_blueprint.png")
            rating = score_base(plan)
            embed = discord.Embed(title=plan.title, description="Tile-aware blueprint generated. Build it in-game, test it, then save the real Clash copy link with `/savebase`.", color=discord.Color.gold())
            embed.add_field(name="Blueprint Score", value=str(rating["overall_score"]), inline=True)
            embed.add_field(name="Anti-Meta", value=anti_meta.name, inline=True)
            embed.add_field(name="Style", value=style.name, inline=True)
            embed.set_image(url="attachment://base_blueprint.png")
            await interaction.followup.send(embed=embed, file=file)
        except Exception as exc:
            print(f"[BASEGEN ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to generate base blueprint.", ephemeral=True)

    @tree.command(name="savebase", description="Save an official Clash copy link to your private base library")
    @app_commands.describe(name="Short name for this base", townhall="Town Hall level", style="Base type", anti_meta="Meta this base targets", symmetry="Layout style", copy_link="Official Clash share/copy layout link", notes="Optional testing notes")
    @app_commands.choices(townhall=TH_CHOICES, style=STYLE_CHOICES, anti_meta=META_CHOICES, symmetry=SYMMETRY_CHOICES)
    async def savebase(interaction: discord.Interaction, name: str, townhall: app_commands.Choice[int], style: app_commands.Choice[str], anti_meta: app_commands.Choice[str], symmetry: app_commands.Choice[str], copy_link: str, notes: str | None = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            if not _copy_link_is_plausible(copy_link):
                await interaction.followup.send("❌ That does not look like an official Clash layout link. Use the in-game Share Layout link.", ephemeral=True)
                return
            entry = await save_base_entry(safe_load_json, safe_save_json, data_dir, user_id=interaction.user.id, name=name[:80], townhall=townhall.value, style=style.value, anti_meta=anti_meta.value, symmetry=symmetry.value, copy_link=copy_link, notes=notes)
            await interaction.followup.send(f"✅ Saved base #{entry['id']}: **{entry['name']}**", ephemeral=True)
        except Exception as exc:
            print(f"[SAVEBASE ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to save base.", ephemeral=True)

    @tree.command(name="bases", description="Search saved Clash base copy links")
    @app_commands.describe(townhall="Optional TH filter", anti_meta="Optional meta filter", style="Optional style filter")
    @app_commands.choices(townhall=TH_CHOICES, anti_meta=META_CHOICES, style=STYLE_CHOICES)
    async def bases(interaction: discord.Interaction, townhall: app_commands.Choice[int] | None = None, anti_meta: app_commands.Choice[str] | None = None, style: app_commands.Choice[str] | None = None):
        await interaction.response.defer(thinking=True)
        try:
            results = await search_saved_bases(safe_load_json, data_dir, townhall=townhall.value if townhall else None, anti_meta=anti_meta.value if anti_meta else None, style=style.value if style else None)
            if not results:
                await interaction.followup.send("No saved bases matched that search yet.", ephemeral=True)
                return
            embed = discord.Embed(title="Saved Clash Bases", description=f"Showing {min(len(results), 10)} of {len(results)} match(es).", color=discord.Color.blue())
            view = discord.ui.View()
            for entry in results[:10]:
                title = f"#{entry['id']} • {entry['name']}"
                value = f"TH{entry['townhall']} • {entry['style'].title()} • {entry['anti_meta'].replace('_',' ').title()} • {entry.get('notes') or 'No notes'}"
                embed.add_field(name=title, value=value[:1024], inline=False)
                view.add_item(discord.ui.Button(label=f"Copy Base #{entry['id']}", url=entry["copy_link"]))
            await interaction.followup.send(embed=embed, view=view)
        except Exception as exc:
            print(f"[BASES ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to search saved bases.", ephemeral=True)

    @tree.command(name="ratebase", description="Rate a generated base profile against the current meta")
    @app_commands.describe(townhall="Town Hall level", style="Base type", anti_meta="Meta to rate against", symmetry="Layout style")
    @app_commands.choices(townhall=TH_CHOICES, style=STYLE_CHOICES, anti_meta=META_CHOICES, symmetry=SYMMETRY_CHOICES)
    async def ratebase(interaction: discord.Interaction, townhall: app_commands.Choice[int], style: app_commands.Choice[str], anti_meta: app_commands.Choice[str], symmetry: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            plan = generate_base_plan(townhall.value, style.value, anti_meta.value, symmetry.value)
            rating = score_base(plan)
            vuln = "\n".join(f"• {k.replace('_',' ').title()}: {v}/10 risk" for k, v in rating["vulnerabilities"].items())
            recs = "\n".join(f"• {item}" for item in (rating["recommendations"] or ["No major fixes generated for this profile."]))
            embed = discord.Embed(title=f"RateBase: {plan.title}", color=discord.Color.orange())
            embed.add_field(name="Overall Score", value=f"{rating['overall_score']}/100", inline=False)
            embed.add_field(name="Vulnerabilities", value=vuln, inline=False)
            embed.add_field(name="Recommended Fixes", value=recs[:1024], inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            print(f"[RATEBASE ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to rate base.", ephemeral=True)

    @tree.command(name="baselab", description="Inspect an official Clash layout link structure")
    @app_commands.describe(link="Official Clash layout/copy link to inspect")
    async def baselab(interaction: discord.Interaction, link: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            analysis = analyze_layout_link(link)
            status = official_link_generation_status()
            embed = discord.Embed(title="BaseLab Link Analysis", color=discord.Color.purple())
            embed.add_field(name="Action", value=analysis.get("action", "unknown"), inline=True)
            embed.add_field(name="Host", value=analysis["host"] or "Unknown", inline=True)
            embed.add_field(name="Query Keys", value=", ".join(analysis["query_keys"]) or "None", inline=False)
            embed.add_field(name="Findings", value="\n".join(f"• {x}" for x in analysis["findings"]) or "No Clash-specific structure detected.", inline=False)
            embed.add_field(name="Official Link Generation", value=f"Status: {status['status']}\nCurrent workflow: {status['safe_current_workflow']}", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            print(f"[BASELAB ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to inspect link.", ephemeral=True)

    @tree.command(name="baselab_compare", description="Compare two Clash layout links for reverse-engineering research")
    @app_commands.describe(link_a="First official Clash layout link", link_b="Second official Clash layout link")
    async def baselab_compare(interaction: discord.Interaction, link_a: str, link_b: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            comparison = compare_layout_links(link_a, link_b)
            changed = comparison.get("changed_value_keys", [])
            changed_text = "\n".join(f"• {item['key']}: len {item['len_a']} -> {item['len_b']}" for item in changed) or "No changed shared values detected."
            embed = discord.Embed(title="BaseLab Link Comparison", color=discord.Color.purple())
            embed.add_field(name="Key Similarity", value=f"{comparison['key_similarity_percent']}%", inline=True)
            embed.add_field(name="Shared Keys", value=", ".join(comparison["shared_query_keys"]) or "None", inline=False)
            embed.add_field(name="Identical Value Keys", value=", ".join(comparison["identical_value_keys"]) or "None", inline=False)
            embed.add_field(name="Changed Value Keys", value=changed_text[:1024], inline=False)
            embed.add_field(name="Observations", value="\n".join(f"• {x}" for x in comparison["observations"]), inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as exc:
            print(f"[BASELAB COMPARE ERROR] {type(exc).__name__}: {exc}")
            await interaction.followup.send("❌ Failed to compare links.", ephemeral=True)

    return {"basegen": basegen, "savebase": savebase, "bases": bases, "ratebase": ratebase, "baselab": baselab, "baselab_compare": baselab_compare}
