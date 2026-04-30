from __future__ import annotations

HERO_ORDER = ["barbarian_king", "archer_queen", "minion_prince", "grand_warden", "royal_champion", "dragon_duke"]
PET_ORDER = ["lassi", "mighty_yak", "electro_owl", "unicorn", "phoenix", "poison_lizard", "diggy", "frosty", "spirit_fox", "angry_jelly", "sneezy", "greedy_raven"]
TROOP_ORDER = ["barbarian", "archer", "giant", "goblin", "wall_breaker", "balloons", "wizard", "healers", "dragons", "pekka", "baby_dragon", "miners", "electro_dragon", "yeti", "dragon_rider", "electro_titan", "root_rider", "thrower", "meteor_golem", "apprentice_warden", "minion", "hog_rider", "valkyrie", "golem", "witch", "lava_hound", "bowler", "ice_golem", "headhunter", "druid", "furnace"]
SPELL_ORDER = ["lightning_spell", "healing_spell", "rage_spell", "poison_spell", "earthquake_spell", "jump_spell", "freeze_spell", "haste_spell", "skeleton_spell", "clone_spell", "bat_spell", "invisibility_spell", "recall_spell", "overgrowth_spell", "ice_block_spell", "revive_spell", "totem_spell"]
SIEGE_ORDER = ["wall_wrecker", "battle_blimp", "stone_slammer", "siege_barracks", "log_launcher", "flame_flinger", "battle_drill", "troop_launcher"]

PET_KEYS = set(PET_ORDER)
PERMANENT_TROOP_KEYS = set(TROOP_ORDER + SIEGE_ORDER)

ORDER_MAPS = {
    "Heroes": {key: idx for idx, key in enumerate(HERO_ORDER)},
    "Pets": {key: idx for idx, key in enumerate(PET_ORDER)},
    "Troops": {key: idx for idx, key in enumerate(TROOP_ORDER)},
    "Spells": {key: idx for idx, key in enumerate(SPELL_ORDER)},
    "Siege Machines": {key: idx for idx, key in enumerate(SIEGE_ORDER)},
}
