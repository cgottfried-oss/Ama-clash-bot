from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_optional(name: str) -> str:
    path = ROOT / name
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def write_developer_guide():
    command_ref = read_optional("COMMAND_REFERENCE.md")
    schema = read_optional("MMO_STATE_SCHEMA_GENERATED.md") or read_optional("MMO_STATE_SCHEMA.md")
    architecture = read_optional("ARCHITECTURE_AUDIT.md")

    guide = [
        "# CLASH MMO DEVELOPER GUIDE",
        "",
        "This guide is generated from the current repository documentation and source-audit outputs.",
        "",
        "## Core rule",
        "",
        "`mmo_state.json` is the primary source of truth for player progression. New player-facing systems should read/write MMO profile state, not legacy wallet/shop JSON files.",
        "",
        "## Command registration",
        "",
        "Slash commands are registered from `clash_mmo/commands/__init__.py` through `register_clash_mmo_commands(bot, ctx)`.",
        "",
        "## Important generated references",
        "",
        "- `COMMAND_REFERENCE.md` — generated command inventory",
        "- `COMMAND_FILE_MAP.md` — command-to-file map",
        "- `ARCHITECTURE_AUDIT.md` — large files, import hotspots, MMO-state pattern counts",
        "- `MMO_STATE_SCHEMA_GENERATED.md` — generated state/profile key inventory",
        "- `RESOURCE_FLOW_GENERATED.md` — generated resource key flow map",
        "- `BALANCE_TABLES_GENERATED.md` — extracted literal balance tables",
        "",
        "## High-value maintenance rules",
        "",
        "1. Prefer shared helpers under `clash_mmo/game/core/` over copy-pasted profile parsing.",
        "2. Keep player-facing command names stable unless intentionally migrating commands.",
        "3. Preserve compatibility aliases only when they protect existing state or imports.",
        "4. Do not reintroduce `/steal`; `/raiduser` is the PvP loot command.",
        "5. Use generated docs after any command/schema/balance change.",
        "",
        "## Current command count",
        "",
    ]

    if command_ref:
        for line in command_ref.splitlines():
            if line.startswith("Total commands discovered:"):
                guide.append(line)
                break
    else:
        guide.append("Command reference missing. Run `python tools/generate_clash_mmo_docs.py`.")

    guide.extend([
        "",
        "## Current architecture snapshot",
        "",
        architecture[:4000] if architecture else "Architecture audit missing. Run `python tools/generate_repo_audit.py`.",
        "",
        "## Current schema snapshot",
        "",
        schema[:4000] if schema else "Schema documentation missing. Run `python tools/generate_data_schema_docs.py`.",
    ])

    (ROOT / "DEVELOPER_GUIDE.md").write_text("\n".join(guide) + "\n", encoding="utf-8")


def write_todo_roadmap():
    roadmap = """# TODO ROADMAP

## Highest priority

1. Add integration tests around command registration.
2. Add a smoke-test script that imports every command module and validates `register_clash_mmo_commands`.
3. Finish replacing direct profile parsing in large command files with shared helpers.
4. Keep `/raiduser` as the PvP loot path and do not restore `/steal`.

## Gameplay systems

### Territories
- Add better territory battle scaling using real clan/player power.
- Add region-specific rewards beyond flat Gold.
- Add admin reset/season rotation tooling.

### Clan War
- Keep clan war as the war-performance/MVP loop.
- Document how war rewards connect to MMO Gold and cosmetics.
- Add war-season rewards if not already active.

### Cosmetics
- Expand cosmetic catalog.
- Keep perks small so cosmetics do not become mandatory power items.
- Add event/season cosmetic rewards.

### Black Market
- Add rotating stock persistence instead of pure random stock every command call.
- Add stock refresh timer.
- Add limited quantity purchases.

## Documentation

- Regenerate command docs after every command patch.
- Regenerate schema docs after every state-model patch.
- Regenerate balance docs after every reward/cost patch.
- Rebuild the player PDF from generated docs after major system changes.

## Technical debt

- Reduce large command files.
- Move more admin view rendering into helper modules.
- Add explicit migrations for old compatibility fields.
- Remove old compatibility aliases only after deployment is verified.
"""
    (ROOT / "TODO_ROADMAP.md").write_text(roadmap, encoding="utf-8")


def write_architecture_diagram():
    diagram = """# ARCHITECTURE DIAGRAM

```text
Discord Slash Commands
        |
        v
clash_mmo/commands/
        |
        +--> core_economy_commands.py      (/village, /daily-style economy helpers, /cooldowns, /gems)
        +--> village_commands.py           (/daily, /farm, /train, /raidvillage, /upgradehall)
        +--> pvp_commands.py               (/raiduser)
        +--> raid_commands.py              (/bossattack and raid boss loop)
        +--> shop_commands.py              (/shop, /buy, /inventory, /useitem)
        +--> market_commands.py            (/market, /blackmarket, /blackmarketbuy, trades)
        +--> territory_commands.py         (/territorymap, /claimterritory, /attackterritory, /territoryincome)
        +--> cosmetic_commands.py          (/cosmetics, /equipcosmetic, /grantcosmetic)
        +--> systems_guide_commands.py     (/systemguide, /glossary)
        |
        v
Shared Game Logic
        |
        +--> clash_mmo/game/core/           profiles, resources, cooldowns, inventory, admin helpers
        +--> clash_mmo/game/raids/          boss/raid/chest/reward mechanics
        +--> clash_mmo/game/heroes/         hero unlocks/loadouts/progression
        +--> clash_mmo/game/equipment/      gear catalog/equip/effective stats
        +--> clash_mmo/game/marketplace/    listings, trades, black market, tax/gold sinks
        +--> clash_mmo/game/territory/      regions, conquest, income
        +--> clash_mmo/game/cosmetics/      catalog, grant/equip, formatting/perks
        |
        v
Persistence
        |
        +--> mmo_state.json                 primary player/source-of-truth state
        +--> legacy compatibility paths     kept only where needed during migration
```
"""
    (ROOT / "ARCHITECTURE_DIAGRAM.md").write_text(diagram, encoding="utf-8")


def main():
    write_developer_guide()
    write_todo_roadmap()
    write_architecture_diagram()
    print("Generated DEVELOPER_GUIDE.md, TODO_ROADMAP.md, and ARCHITECTURE_DIAGRAM.md")


if __name__ == "__main__":
    main()
