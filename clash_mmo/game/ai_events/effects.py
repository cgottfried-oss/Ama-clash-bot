from __future__ import annotations


def apply_event_effects(rewards: dict, modifiers: dict) -> dict:
    rewards = dict(rewards or {})
    modifiers = dict(modifiers or {})

    bonus_rules = {
        "gold_bonus_pct": ["gold"],
        "elixir_bonus_pct": ["elixir"],
        "pve_gold_bonus_pct": ["gold"],
        "ore_bonus_pct": ["shiny_ore", "glowy_ore", "starry_ore"],
        "hero_xp_bonus_pct": ["hero_xp"],
    }

    for modifier_key, resources in bonus_rules.items():
        pct = int(modifiers.get(modifier_key, 0) or 0)
        if pct <= 0:
            continue
        for resource in resources:
            if resource not in rewards:
                continue
            rewards[resource] = int(rewards.get(resource, 0) or 0) + (int(rewards.get(resource, 0) or 0) * pct // 100)

    return rewards
