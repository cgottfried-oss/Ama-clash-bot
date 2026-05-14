from __future__ import annotations

META_RULES = {
    "root_rider": {
        "label": "Anti Root Rider",
        "focus": ["broken pathing", "offset core", "staggered splash", "spring trap lanes"],
        "rules": [
            "Avoid long straight compartments that let Root Riders chain through the core.",
            "Offset the Town Hall so the strongest push cannot naturally collect every major defense.",
            "Use dead zones and staggered compartments to split heroes from Root Riders.",
            "Place spring traps and ground skeletons near likely entry lanes, not randomly in the core.",
            "Separate Monolith, Scattershots, Infernos, and Spell Towers to reduce spell value.",
        ],
        "weaknesses": ["Super Archer Blimp from a protected corner", "heavy air backend if air traps are too central"],
    },
    "fireball": {
        "label": "Anti Fireball",
        "focus": ["defense spacing", "warden angle denial", "low value bait", "split core"],
        "rules": [
            "Keep major defenses spread so one Fireball cannot hit 3+ premium targets.",
            "Place bait defenses on common Warden walk angles while protecting real value deeper inside.",
            "Avoid stacking Inferno, Scatter, Monolith, Spell Tower, and Town Hall in one radius.",
            "Create awkward outside pathing so Warden entry angles are predictable and punishable.",
            "Use Seeking Air Mines and air skeletons on likely Warden/Healer routes.",
        ],
        "weaknesses": ["Queen Charge into the isolated core", "smash attacks if compartments are too open"],
    },
    "blimp": {
        "label": "Anti Blimp",
        "focus": ["tornado trap", "black mine layers", "sweeper angles", "TH access denial"],
        "rules": [
            "Do not leave a clean straight-line blimp path to Town Hall or core value.",
            "Layer Seeking Air Mines before the core rather than only on the Town Hall tile.",
            "Use Tornado Trap near the highest-value blimp drop zone.",
            "Set sweepers to deny the most obvious Battle Blimp and Battle Drill style entries.",
            "Avoid giving clone value next to Town Hall, Monolith, and Spell Towers at once.",
        ],
        "weaknesses": ["ground smash from the opposite side", "Zap value if air defenses are too close"],
    },
    "air_spam": {
        "label": "Anti Air Spam",
        "focus": ["air trap layering", "sweeper coverage", "spread air defenses", "backend punish"],
        "rules": [
            "Spread air defenses so LavaLoon, Dragons, or Electro Dragons cannot roll one side for free.",
            "Place sweepers to push main air pathing away from Town Hall and high-value splash.",
            "Stack red air bombs in likely balloon clumps, not isolated corners.",
            "Keep Scattershots and multi Infernos protected from early hero trades.",
            "Use outside trash to make funneling less automatic.",
        ],
        "weaknesses": ["strong Queen Charge backend setup", "ground hero dive into air defenses"],
    },
    "hybrid": {
        "label": "Anti Hybrid",
        "focus": ["healer pressure", "bomb towers", "path split", "spring traps"],
        "rules": [
            "Use offset compartments to split Miners from Hogs after the first Heal spell.",
            "Place Bomb Towers and giant bombs where Hybrid must path, not at the edge.",
            "Protect key splash from an easy Queen Charge entry.",
            "Use spring traps in narrow Hog pathing lanes.",
            "Keep Clan Castle pull awkward and punish predictable Queen paths.",
        ],
        "weaknesses": ["Surgical Lalo", "Root Rider smash if walls are too connected"],
    },
}

STYLE_RULES = {
    "war": ["Prioritize anti-3-star value over loot protection.", "Accept some 2-star risk if it makes triple pathing harder."],
    "cwl": ["Prioritize safe Town Hall protection and anti-triple consistency.", "Reduce gimmick traps that only work once."],
    "legend": ["Balance anti-2-star and anti-3-star value.", "Protect Town Hall while denying easy percentage."],
    "farming": ["Protect storage zones more than perfect war pathing.", "Keep collectors outside as trash/funnel noise."],
}

TH_BUILDINGS = {
    14: ["Town Hall", "Clan Castle", "Eagle", "Scattershot A", "Scattershot B", "Inferno A", "Inferno B", "Inferno C", "X-Bows", "Builder Huts", "Bomb Towers", "Air Defenses"],
    15: ["Town Hall", "Clan Castle", "Monolith", "Spell Tower A", "Spell Tower B", "Eagle", "Scattershot A", "Scattershot B", "Infernos", "X-Bows", "Builder Huts"],
    16: ["Town Hall", "Clan Castle", "Monolith", "Spell Tower A", "Spell Tower B", "Merged Defenses", "Eagle", "Scattershots", "Infernos", "Ricochet Cannons", "Multi-Archer Towers"],
    17: ["Town Hall", "Clan Castle", "Hero Hall", "Firespitters", "Monolith", "Spell Towers", "Merged Defenses", "Scattershots", "Infernos", "Ricochet Cannons"],
}

def normalize_choice(value: str | None, default: str, allowed: set[str]) -> str:
    candidate = str(value or default).lower().strip().replace(" ", "_").replace("-", "_")
    return candidate if candidate in allowed else default

def get_meta_rule(meta: str) -> dict:
    return META_RULES.get(meta, META_RULES["root_rider"])

def get_style_rules(style: str) -> list[str]:
    return STYLE_RULES.get(style, STYLE_RULES["war"])

def get_buildings(th: int) -> list[str]:
    return TH_BUILDINGS.get(th, TH_BUILDINGS[16])
