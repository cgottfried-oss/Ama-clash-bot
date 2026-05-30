RAID_BOSSES = {
    "goblin_king": {
        "name": "Goblin King",
        "emoji": "👑",
        "max_hp": 25000,
        "phase_count": 3,
        "recommended_th": 7,
        "base_rewards": {"gold": 1500, "elixir": 1000, "clan_xp": 50},
    },
    "lava_golem": {
        "name": "Lava Golem",
        "emoji": "🌋",
        "max_hp": 50000,
        "phase_count": 4,
        "recommended_th": 10,
        "base_rewards": {"gold": 3000, "dark_elixir": 200, "shiny_ore": 25, "clan_xp": 90},
    },
    "storm_dragon": {
        "name": "Storm Dragon",
        "emoji": "🐉",
        "max_hp": 100000,
        "phase_count": 5,
        "recommended_th": 13,
        "base_rewards": {"gold": 6000, "raid_medals": 10, "glowy_ore": 15, "clan_xp": 160},
    },
}


def get_boss(boss_id: str) -> dict:
    return dict(RAID_BOSSES.get(boss_id, {}))


def boss_name(boss_id: str) -> str:
    return RAID_BOSSES.get(boss_id, {}).get("name", str(boss_id).replace("_", " ").title())
