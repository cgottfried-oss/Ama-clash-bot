from __future__ import annotations

from dataclasses import dataclass, field

from .rarity import rarity_multiplier


@dataclass
class Modifier:
    stat: str
    value: float
    source: str = "unknown"
    mode: str = "flat"


@dataclass
class StatBlock:
    attack: float = 0
    defense: float = 0
    health: float = 0
    speed: float = 0
    crit: float = 0
    modifiers: list[Modifier] = field(default_factory=list)



def apply_modifier(base_value: float, modifier: Modifier):
    if modifier.mode == "percent":
        return base_value * (1 + modifier.value)

    return base_value + modifier.value



def calculate_effective_stats(base_stats: StatBlock, equipment_items: list[dict]):
    result = {
        "attack": base_stats.attack,
        "defense": base_stats.defense,
        "health": base_stats.health,
        "speed": base_stats.speed,
        "crit": base_stats.crit,
    }

    for item in equipment_items:
        rarity_multi = rarity_multiplier(item.get("rarity", "common"))

        for stat_name, stat_value in item.get("stat_modifiers", {}).items():
            if stat_name not in result:
                continue

            result[stat_name] = apply_modifier(
                result[stat_name],
                Modifier(
                    stat=stat_name,
                    value=float(stat_value) * rarity_multi,
                    source=item.get("item_id", "unknown"),
                    mode="flat",
                ),
            )

    return result