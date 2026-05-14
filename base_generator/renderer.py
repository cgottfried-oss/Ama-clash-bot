from __future__ import annotations

import html as html_lib

from .generator import BasePlan
from .scorer import score_base
from .tilemap import CENTER_INDEX

BASEGEN_CSS = """
* { box-sizing: border-box; }
body { margin: 0; width: 1400px; min-height: 1320px; font-family: Arial, Helvetica, sans-serif; color: #fff; background: radial-gradient(circle at 10% 8%, rgba(255,205,64,.30), transparent 25%), radial-gradient(circle at 90% 12%, rgba(80,155,255,.28), transparent 28%), linear-gradient(135deg, #101827, #18233f 48%, #0d1322); }
.card { width: 1340px; margin: 30px; padding: 30px; border-radius: 34px; background: linear-gradient(180deg, rgba(38,50,86,.94), rgba(9,14,28,.96)); border: 3px solid rgba(255,255,255,.14); box-shadow: 0 30px 70px rgba(0,0,0,.55); overflow: hidden; }
.header { display: grid; grid-template-columns: 1fr 220px; gap: 20px; align-items: center; margin-bottom: 20px; }
.title { font-size: 48px; font-weight: 1000; line-height: .98; text-transform: uppercase; text-shadow: 0 5px 0 rgba(0,0,0,.35); }
.sub { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 10px; }
.pill { padding: 9px 15px; border-radius: 999px; font-size: 20px; font-weight: 900; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.16); }
.score { border-radius: 28px; padding: 20px; text-align: center; background: linear-gradient(180deg, rgba(255,206,62,.22), rgba(55,142,255,.18)); border: 2px solid rgba(255,255,255,.16); }
.score-label { font-size: 15px; letter-spacing: 1px; text-transform: uppercase; font-weight: 1000; opacity: .75; }
.score-value { font-size: 58px; font-weight: 1000; text-shadow: 0 4px 0 rgba(0,0,0,.35); }
.main { display: grid; grid-template-columns: 600px 1fr; gap: 24px; }
.grid-wrap { padding: 14px; border-radius: 24px; background: rgba(0,0,0,.28); border: 2px solid rgba(255,255,255,.10); }
.grid { display: grid; grid-template-columns: 28px repeat(13, 1fr); gap: 4px; }
.coord { height: 34px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 1000; opacity: .72; }
.cell { height: 34px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 1000; background: rgba(255,255,255,.055); border: 1px solid rgba(255,255,255,.08); }
.cell.building { background: linear-gradient(180deg, rgba(255,206,62,.90), rgba(236,136,36,.90)); color: #111827; box-shadow: inset 0 2px 0 rgba(255,255,255,.35); }
.cell.wall { background: linear-gradient(180deg, rgba(126,140,165,.75), rgba(73,85,112,.75)); color: #fff; }
.cell.center { background: linear-gradient(180deg, rgba(80,210,255,.85), rgba(68,116,255,.85)); color: #fff; box-shadow: 0 0 14px rgba(80,210,255,.35); }
.legend { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; font-size: 15px; font-weight: 900; }
.key { padding: 7px 10px; border-radius: 999px; background: rgba(255,255,255,.09); border: 1px solid rgba(255,255,255,.13); }
.section { margin-bottom: 14px; padding: 16px; border-radius: 22px; background: rgba(0,0,0,.25); border: 1px solid rgba(255,255,255,.10); }
.section-title { font-size: 25px; font-weight: 1000; margin-bottom: 10px; }
ul { margin: 0; padding-left: 0; list-style: none; }
li { position: relative; margin-bottom: 7px; padding-left: 23px; font-size: 17px; line-height: 1.2; font-weight: 800; }
li::before { content: "✦"; position: absolute; left: 0; color: #ffd04a; }
.footer { margin-top: 14px; padding: 14px 18px; border-radius: 20px; background: rgba(88,101,242,.30); border: 1px solid rgba(255,255,255,.14); font-size: 18px; font-weight: 900; text-align: center; }
"""

def _items(items: list[str], limit: int = 5) -> str:
    return "".join(f"<li>{html_lib.escape(str(item))}</li>" for item in items[:limit])

def _grid_html(plan: BasePlan) -> str:
    cells = ["<div class='coord'></div>"]
    for col in range(13):
        offset = col - CENTER_INDEX
        cells.append(f"<div class='coord'>{offset:+d}</div>")
    for row_idx, row in enumerate(plan.grid):
        y = row_idx - CENTER_INDEX
        cells.append(f"<div class='coord'>{y:+d}</div>")
        for col_idx, value in enumerate(row):
            label = html_lib.escape(value or "")
            cls = "cell"
            if value == "C":
                cls += " center"
            elif value == "W":
                cls += " wall"
            elif value:
                cls += " building"
            cells.append(f"<div class='{cls}'>{label}</div>")
    return "".join(cells)

def _legend_html(plan: BasePlan) -> str:
    keys = ["C = Center", "W = Wall", "TH = Town Hall", "CC = Clan Castle", "MO = Monolith", "S1/S2 = Scattershots", "I1/I2/I3 = Infernos", "ST = Spell Tower"]
    return "".join(f"<span class='key'>{html_lib.escape(k)}</span>" for k in keys)

def build_base_plan_html(plan: BasePlan) -> str:
    rating = score_base(plan)
    vulnerabilities = rating.get("vulnerabilities", {})
    vulnerability_lines = [f"{k.replace('_', ' ').title()}: {v}/10 risk" for k, v in vulnerabilities.items()]
    compartment_lines = [f"{c['name']}: {c['purpose']}" for c in getattr(plan, "compartments", [])]
    return f"""
    <html><head><style>{BASEGEN_CSS}</style></head><body><div class='card'>
      <div class='header'>
        <div><div class='title'>{html_lib.escape(plan.title)}</div><div class='sub'>
          <span class='pill'>TH{plan.townhall}</span><span class='pill'>{html_lib.escape(plan.style.title())}</span><span class='pill'>{html_lib.escape(plan.anti_meta.replace('_',' ').title())}</span><span class='pill'>{html_lib.escape(plan.symmetry.title())}</span><span class='pill'>Center-Based Tile Map</span>
        </div></div>
        <div class='score'><div class='score-label'>Blueprint Score</div><div class='score-value'>{rating['overall_score']}</div></div>
      </div>
      <div class='main'>
        <div><div class='grid-wrap'><div class='grid'>{_grid_html(plan)}</div><div class='legend'>{_legend_html(plan)}</div></div><div class='footer'>Start from C/center. Positive X = right. Negative Y = up. Save the official Clash copy link after building with /savebase.</div></div>
        <div>
          <div class='section'><div class='section-title'>Placement Guide</div><ul>{_items(getattr(plan, 'placement_guide', []), 8)}</ul></div>
          <div class='section'><div class='section-title'>Compartments</div><ul>{_items(compartment_lines, 3)}</ul></div>
          <div class='section'><div class='section-title'>Trap Plan</div><ul>{_items(plan.trap_plan, 4)}</ul></div>
          <div class='section'><div class='section-title'>Vulnerability Readout</div><ul>{_items(vulnerability_lines, 4)}</ul></div>
          <div class='section'><div class='section-title'>Anti-Meta Rules</div><ul>{_items(plan.rules, 4)}</ul></div>
        </div>
      </div>
    </div></body></html>
    """
