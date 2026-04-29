#CHECK = "\u2705"        # ✅
BRAIN = "\U0001F9E0"    # 🧠
CHART = "\U0001F4CA"    # 📊
FULL = "\u2588"         # █
EMPTY = "\u2591"        # ░


LANE_EMOJIS = {
    "hero": "👑",
    "lab": "🧪",
    "builder": "🛠️",
}
CATEGORY_EMOJIS = {
    "hero": "👑",
    "troop": "⚔️",
    "spell": "✨",
    "siege": "🚀",
    "pet": "🐾",
    "building": "🏰",
    "economy": "💰",
    "defense": "🛡️",
    "trap": "💣",
}
TIMING_EMOJIS = {
    "now": "🔥",
    "soon": "⚡",
    "save_for": "🪙",
    "wait": "⏳",
}
MODE_EMOJIS = {
    "war": "⚔️",
    "farm": "🌾",
    "auto": "🧠",
}


MODE_CATEGORY_BIAS: dict[str, dict[str, float]] = {
    "war": {
        "hero": 1.24,
        "pet": 1.18,
        "troop": 1.16,
        "spell": 1.14,
        "siege": 1.14,
        "building": 1.02,
        "economy": 0.90,
        "defense": 0.84,
        "trap": 0.72,
    },
    "farm": {
        "hero": 1.08,
        "pet": 1.06,
        "troop": 0.95,
        "spell": 0.95,
        "siege": 0.92,
        "building": 1.18,
        "economy": 1.22,
        "defense": 0.98,
        "trap": 0.85,
    },
}

MODE_LANE_BIAS: dict[str, dict[str, float]] = {
    "war": {"hero": 1.08, "lab": 1.06, "builder": 0.98},
    "farm": {"hero": 1.00, "lab": 0.97, "builder": 1.08},
}

ELIXIR_BUILDING_KEYS = {
    "army_camp",
    "barracks",
    "dark_barracks",
    "spell_factory",
    "dark_spell_factory",
    "laboratory",
    "workshop",
    "clan_castle",
    "pet_house",
}
GOLD_BUILDING_KEYS = {
    "hero_hall",
    "blacksmith",
}