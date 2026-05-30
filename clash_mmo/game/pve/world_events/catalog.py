from __future__ import annotations

# World events are server-wide PvE modifiers. Reworked from the original
# pvp_commands EVENTS dict so they live with the other PvE systems.
# Each event has a key, display name, description, and a machine-readable
# `effects` block so consumers (raiduser, war rewards, hero costs) can react.

WORLD_EVENTS = {
    "goblin_invasion": {
        "name": "Goblin Invasion",
        "description": "+25% /raiduser steal cap and boosted war rewards while active.",
        "effects": {
            "raiduser_steal_cap_pct": 0.10,  # raised from default 0.08
            "war_reward_multiplier": 1.25,
        },
    },
    "double_loot": {
        "name": "Double Loot Weekend",
        "description": "+25% clan war rewards while active.",
        "effects": {
            "war_reward_multiplier": 1.25,
        },
    },
    "trader_weekend": {
        "name": "Trader Weekend",
        "description": "Hero upgrade costs are reduced by 20% while active.",
        "effects": {
            "hero_upgrade_cost_multiplier": 0.80,
        },
    },
}


def get_event_config(key: str) -> dict | None:
    return WORLD_EVENTS.get(str(key or "").strip().lower())


def event_keys() -> list[str]:
    return list(WORLD_EVENTS.keys())
