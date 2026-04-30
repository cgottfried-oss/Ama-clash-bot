@dataclass(frozen=True)
class ItemMeta:
    key: str
    label: str
    category: str
    offense: float
    farming: float
    defense: float
    utility: float
    time_weight: float
    cost_weight: float = 1.0
    lane: str = "builder" # builder | lab | hero
    blocks_progress: float = 0.0
    foundational: bool = False
    role_bonus: dict[str, float] = field(default_factory=dict)
    breakpoints: set[int] = field(default_factory=set)
    source: str = "manual"  # manual | hero | troop | spell | pet


ITEMS: dict[str, ItemMeta] = {
    # Heroes
    "barbarian_king": ItemMeta("barbarian_king", "Barbarian King", "hero", 9.0, 3.0, 2.0, 4.0, 5.0, cost_weight=4.8, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="hero"),
    "archer_queen": ItemMeta("archer_queen", "Archer Queen", "hero", 10.0, 4.0, 2.0, 5.0, 5.0, cost_weight=5.0, lane="hero", blocks_progress=1.4, role_bonus={"attacker": 7, "hybrid": 4, "farmer": 0}, source="hero"),
    "grand_warden": ItemMeta("grand_warden", "Grand Warden", "hero", 10.0, 2.0, 2.0, 7.0, 5.0, cost_weight=4.6, lane="hero", blocks_progress=1.5, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={10, 20, 30, 40, 50, 60, 70}, source="hero"),
    "royal_champion": ItemMeta("royal_champion", "Royal Champion", "hero", 9.5, 2.0, 2.5, 4.5, 5.0, cost_weight=4.7, lane="hero", blocks_progress=1.3, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 10, 20, 25, 35, 45}, source="hero"),
    "minion_prince": ItemMeta("minion_prince", "Minion Prince", "hero", 8.5, 2.0, 2.0, 4.0, 5.0, cost_weight=4.5, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="hero"),
    "dragon_duke": ItemMeta("dragon_duke", "Dragon Duke", "hero", 9.0, 2.0, 2.0, 4.0, 5.5, cost_weight=4.9, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -2}, source="hero"),

    # Buildings / structure priorities
    "army_camp": ItemMeta("army_camp", "Army Camp", "building", 10.0, 5.0, 0.0, 8.0, 4.0, cost_weight=3.8, lane="builder", blocks_progress=1.6, foundational=True, role_bonus={"attacker": 8, "hybrid": 7, "farmer": 2}, breakpoints={8, 9, 10, 11, 12, 13}),
    "clan_castle": ItemMeta("clan_castle", "Clan Castle", "building", 9.0, 2.0, 2.0, 8.0, 4.0, cost_weight=3.7, lane="builder", blocks_progress=1.4, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": 0}, breakpoints={7, 8, 9, 10, 11, 12}),
    "laboratory": ItemMeta("laboratory", "Laboratory", "building", 8.0, 3.0, 0.0, 10.0, 4.0, cost_weight=4.0, lane="builder", blocks_progress=1.8, foundational=True, role_bonus={"attacker": 8, "hybrid": 6, "farmer": 0}, breakpoints={8, 9, 10, 11, 12, 13, 14, 15, 16}),
    "spell_factory": ItemMeta("spell_factory", "Spell Factory", "building", 7.0, 1.0, 0.0, 7.0, 4.0, cost_weight=3.0, lane="builder", blocks_progress=1.0, foundational=True, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, breakpoints={5, 6, 7}),
    "pet_house": ItemMeta("pet_house", "Pet House", "building", 8.0, 1.0, 0.0, 7.0, 4.5, cost_weight=4.4, lane="builder", blocks_progress=1.4, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -1}, breakpoints={4, 8, 10}),
    "blacksmith": ItemMeta("blacksmith", "Blacksmith", "building", 8.0, 1.0, 0.0, 8.0, 4.5, cost_weight=4.3, lane="builder", blocks_progress=1.5, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={2, 4, 6, 8, 10}),
    "hero_hall": ItemMeta("hero_hall", "Hero Hall", "building", 9.0, 1.0, 0.0, 9.0, 5.0, cost_weight=4.5, lane="builder", blocks_progress=1.7, foundational=True, role_bonus={"attacker": 7, "hybrid": 5, "farmer": -2}, breakpoints={9, 10, 11}),

    # Troops
    "healers": ItemMeta("healers", "Healers", "troop", 9.0, 3.0, 0.0, 5.0, 3.0, cost_weight=2.8, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 3, "farmer": 0}, source="troop"),
    "balloons": ItemMeta("balloons", "Balloons", "troop", 9.0, 2.0, 0.0, 4.0, 3.0, cost_weight=2.8, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 6, "hybrid": 3, "farmer": -1}, source="troop"),
    "dragons": ItemMeta("dragons", "Dragons", "troop", 8.0, 2.0, 0.0, 4.0, 3.5, cost_weight=3.0, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "electro_dragon": ItemMeta("electro_dragon", "Electro Dragon", "troop", 8.5, 2.0, 0.0, 4.0, 3.8, cost_weight=3.4, lane="lab", blocks_progress=0.8, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "hog_rider": ItemMeta("hog_rider", "Hog Rider", "troop", 8.5, 2.0, 0.0, 4.0, 3.0, cost_weight=2.9, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="troop"),
    "miners": ItemMeta("miners", "Miners", "troop", 8.0, 3.0, 0.0, 4.0, 3.0, cost_weight=3.0, lane="lab", blocks_progress=0.8),
    "root_rider": ItemMeta("root_rider", "Root Rider", "troop", 9.0, 1.0, 0.0, 4.0, 4.0, cost_weight=3.8, lane="lab", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),
    "apprentice_warden": ItemMeta("apprentice_warden", "Apprentice Warden", "troop", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.6, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="troop"),

    # Siege machines
    "wall_wrecker": ItemMeta("wall_wrecker", "Wall Wrecker", "siege", 8.5, 1.0, 0.0, 5.0, 3.8, cost_weight=3.3, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={3, 4, 5, 6}, source="troop"),
    "battle_blimp": ItemMeta("battle_blimp", "Battle Blimp", "siege", 8.5, 1.0, 0.0, 5.5, 3.8, cost_weight=3.3, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={3, 4, 5}, source="troop"),
    "stone_slammer": ItemMeta("stone_slammer", "Stone Slammer", "siege", 9.0, 1.0, 0.0, 5.0, 3.8, cost_weight=3.4, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={3, 4, 5, 6}, source="troop"),
    "siege_barracks": ItemMeta("siege_barracks", "Siege Barracks", "siege", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "log_launcher": ItemMeta("log_launcher", "Log Launcher", "siege", 9.0, 1.0, 0.0, 6.0, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "flame_flinger": ItemMeta("flame_flinger", "Flame Flinger", "siege", 8.5, 1.0, 0.0, 5.5, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "battle_drill": ItemMeta("battle_drill", "Battle Drill", "siege", 8.5, 1.0, 0.0, 5.5, 4.0, cost_weight=3.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={4, 5}, source="troop"),
    "troop_launcher": ItemMeta("troop_launcher", "Troop Launcher", "siege", 8.0, 1.0, 0.0, 5.0, 4.0, cost_weight=3.4, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, breakpoints={3, 4}, source="troop"),

    # Spells
    "rage_spell": ItemMeta("rage_spell", "Rage Spell", "spell", 8.0, 1.0, 0.0, 5.0, 2.5, cost_weight=2.2, lane="lab", blocks_progress=0.8, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="spell"),
    "freeze_spell": ItemMeta("freeze_spell", "Freeze Spell", "spell", 9.0, 1.0, 0.0, 6.0, 2.5, cost_weight=2.4, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -1}, source="spell"),
    "invisibility_spell": ItemMeta("invisibility_spell", "Invisibility Spell", "spell", 8.5, 1.0, 0.0, 6.0, 3.0, cost_weight=2.5, lane="lab", blocks_progress=1.0, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="spell"),
    "recall_spell": ItemMeta("recall_spell", "Recall Spell", "spell", 7.0, 1.0, 0.0, 6.0, 3.0, cost_weight=2.6, lane="lab", blocks_progress=0.9, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -2}, source="spell"),
    
    # Pets
    "lassi": ItemMeta("lassi", "L.A.S.S.I", "pet", 7.5, 1.0, 0.0, 4.0, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "mighty_yak": ItemMeta("mighty_yak", "Mighty Yak", "pet", 8.0, 1.0, 0.0, 4.5, 3.0, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "electro_owl": ItemMeta("electro_owl", "Electro Owl", "pet", 8.0, 1.0, 0.0, 4.5, 3.0, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "unicorn": ItemMeta("unicorn", "Unicorn", "pet", 9.0, 1.0, 0.0, 5.0, 3.2, cost_weight=3.3, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),
    "phoenix": ItemMeta("phoenix", "Phoenix", "pet", 8.5, 1.0, 0.0, 5.0, 3.2, cost_weight=3.2, lane="hero", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -2}, source="pet"),
    "diggy": ItemMeta("diggy", "Diggy", "pet", 8.5, 1.0, 0.0, 5.5, 3.2, cost_weight=3.3, lane="hero", blocks_progress=1.1, role_bonus={"attacker": 5, "hybrid": 4, "farmer": -2}, source="pet"),
    "poison_lizard": ItemMeta("poison_lizard", "Poison Lizard", "pet", 8.0, 1.0, 0.0, 5.0, 3.1, cost_weight=3.1, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 5, "hybrid": 3, "farmer": -1}, source="pet"),
    "frosty": ItemMeta("frosty", "Frosty", "pet", 7.5, 1.0, 0.0, 5.0, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.9, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "spirit_fox": ItemMeta("spirit_fox", "Spirit Fox", "pet", 9.0, 1.0, 0.0, 6.0, 3.2, cost_weight=3.5, lane="hero", blocks_progress=1.2, role_bonus={"attacker": 6, "hybrid": 4, "farmer": -2}, source="pet"),
    "angry_jelly": ItemMeta("angry_jelly", "Angry Jelly", "pet", 7.5, 1.0, 0.0, 4.8, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "sneezy": ItemMeta("sneezy", "Sneezy", "pet", 7.5, 1.0, 0.0, 4.8, 3.0, cost_weight=3.0, lane="hero", blocks_progress=0.8, role_bonus={"attacker": 4, "hybrid": 3, "farmer": -1}, source="pet"),
    "greedy_raven": ItemMeta("greedy_raven", "Greedy Raven", "pet", 8.5, 2.0, 0.0, 5.0, 3.1, cost_weight=3.2, lane="hero", blocks_progress=1.0, role_bonus={"attacker": 5, "hybrid": 3, "farmer": 0}, source="pet"),
    
    # Economy / defensive options for farmer or hybrid preference
    "gold_mine": ItemMeta("gold_mine", "Gold Mine", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "elixir_collector": ItemMeta("elixir_collector", "Elixir Collector", "economy", 0.0, 9.0, 0.0, 2.0, 2.0, role_bonus={"attacker": -4, "hybrid": -1, "farmer": 7}),
    "dark_elixir_drill": ItemMeta("dark_elixir_drill", "Dark Elixir Drill", "economy", 0.0, 8.5, 0.0, 2.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 7}),
    "gold_storage": ItemMeta("gold_storage", "Gold Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "elixir_storage": ItemMeta("elixir_storage", "Elixir Storage", "economy", 0.0, 6.0, 0.5, 4.0, 2.5, role_bonus={"attacker": -3, "hybrid": 0, "farmer": 5}),
    "air_defense": ItemMeta("air_defense", "Air Defense", "defense", 0.0, 1.0, 8.0, 2.0, 3.5, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
    "inferno_tower": ItemMeta("inferno_tower", "Inferno Tower", "defense", 0.0, 1.0, 8.5, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "x_bow": ItemMeta("x_bow", "X-Bow", "defense", 0.0, 1.0, 7.0, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 3, "farmer": 2}),
    "scattershot": ItemMeta("scattershot", "Scattershot", "defense", 0.0, 1.0, 8.7, 2.2, 4.5, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "air_sweeper": ItemMeta("air_sweeper", "Air Sweeper", "defense", 0.0, 1.0, 6.8, 2.0, 3.0, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "hidden_tesla": ItemMeta("hidden_tesla", "Hidden Tesla", "defense", 0.0, 1.0, 6.5, 1.8, 3.2, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "bomb_tower": ItemMeta("bomb_tower", "Bomb Tower", "defense", 0.0, 1.0, 6.9, 1.8, 3.4, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "spell_tower": ItemMeta("spell_tower", "Spell Tower", "defense", 0.0, 1.0, 8.0, 2.2, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "monolith": ItemMeta("monolith", "Monolith", "defense", 0.0, 1.0, 9.0, 2.2, 4.8, role_bonus={"attacker": -4, "hybrid": 5, "farmer": 2}),
    "multi_archer_tower": ItemMeta("multi_archer_tower", "Multi-Archer Tower", "defense", 0.0, 1.0, 8.4, 2.0, 4.2, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "ricochet_cannon": ItemMeta("ricochet_cannon", "Ricochet Cannon", "defense", 0.0, 1.0, 8.6, 2.0, 4.2, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "multi_gear_tower": ItemMeta("multi_gear_tower", "Multi-Gear Tower", "defense", 0.0, 1.0, 8.3, 2.0, 4.3, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "firespitter": ItemMeta("firespitter", "Firespitter", "defense", 0.0, 1.0, 8.1, 2.0, 4.0, role_bonus={"attacker": -3, "hybrid": 4, "farmer": 2}),
    "super_wizard_tower": ItemMeta("super_wizard_tower", "Super Wizard Tower", "defense", 0.0, 1.0, 8.8, 2.2, 4.5, role_bonus={"attacker": -3, "hybrid": 5, "farmer": 2}),
    "revenge_tower": ItemMeta("revenge_tower", "Revenge Tower", "defense", 0.0, 1.0, 8.9, 2.2, 4.6, role_bonus={"attacker": -3, "hybrid": 5, "farmer": 2}),
    # Traps
    "bomb": ItemMeta("bomb", "Bomb", "trap", 0.0, 0.5, 5.0, 1.0, 2.0, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "giant_bomb": ItemMeta("giant_bomb", "Giant Bomb", "trap", 0.0, 0.5, 7.0, 1.2, 2.5, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "air_bomb": ItemMeta("air_bomb", "Air Bomb", "trap", 0.0, 0.5, 6.0, 1.0, 2.2, role_bonus={"attacker": -2, "hybrid": 2, "farmer": 1}),
    "seeking_air_mine": ItemMeta("seeking_air_mine", "Seeking Air Mine", "trap", 0.0, 0.5, 6.5, 1.0, 2.3, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "spring_trap": ItemMeta("spring_trap", "Spring Trap", "trap", 0.0, 0.5, 4.5, 0.8, 2.0, role_bonus={"attacker": -1, "hybrid": 2, "farmer": 1}),
    "skeleton_trap": ItemMeta("skeleton_trap", "Skeleton Trap", "trap", 0.0, 0.5, 5.0, 1.0, 2.1, role_bonus={"attacker": -1, "hybrid": 2, "farmer": 1}),
    "tornado_trap": ItemMeta("tornado_trap", "Tornado Trap", "trap", 0.0, 0.5, 7.5, 1.2, 2.8, role_bonus={"attacker": -2, "hybrid": 3, "farmer": 1}),
    "giga_bomb": ItemMeta("giga_bomb", "Giga Bomb", "trap", 0.0, 0.5, 8.0, 1.5, 3.0, role_bonus={"attacker": -2, "hybrid": 4, "farmer": 1}),
}