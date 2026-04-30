from __future__ import annotations

# Account-completion-only items are modeled for TH-cap coverage and HTML rendering,
# but intentionally excluded from inferred advisor targets so they do not flood the
# recommendation engine or change the curated "top picks" behavior.
ACCOUNT_ONLY_CAP_NAME_MAP: dict[str, tuple[str, str]] = {
    # Troops
    "barbarian": ("troops", "Barbarian"),
    "archer": ("troops", "Archer"),
    "giant": ("troops", "Giant"),
    "goblin": ("troops", "Goblin"),
    "wall_breaker": ("troops", "Wall Breaker"),
    "wizard": ("troops", "Wizard"),
    "pekka": ("troops", "P.E.K.K.A"),
    "baby_dragon": ("troops", "Baby Dragon"),
    "yeti": ("troops", "Yeti"),
    "dragon_rider": ("troops", "Dragon Rider"),
    "electro_titan": ("troops", "Electro Titan"),
    "thrower": ("troops", "Thrower"),
    "meteor_golem": ("troops", "Meteor Golem"),
    "minion": ("troops", "Minion"),
    "valkyrie": ("troops", "Valkyrie"),
    "golem": ("troops", "Golem"),
    "witch": ("troops", "Witch"),
    "lava_hound": ("troops", "Lava Hound"),
    "bowler": ("troops", "Bowler"),
    "ice_golem": ("troops", "Ice Golem"),
    "headhunter": ("troops", "Headhunter"),
    "druid": ("troops", "Druid"),
    "furnace": ("troops", "Furnace"),
    # Spells
    "lightning_spell": ("spells", "Lightning Spell"),
    "healing_spell": ("spells", "Healing Spell"),
    "poison_spell": ("spells", "Poison Spell"),
    "earthquake_spell": ("spells", "Earthquake Spell"),
    "jump_spell": ("spells", "Jump Spell"),
    "haste_spell": ("spells", "Haste Spell"),
    "skeleton_spell": ("spells", "Skeleton Spell"),
    "clone_spell": ("spells", "Clone Spell"),
    "bat_spell": ("spells", "Bat Spell"),
    "overgrowth_spell": ("spells", "Overgrowth Spell"),
    "ice_block_spell": ("spells", "Ice Block Spell"),
    "revive_spell": ("spells", "Revive Spell"),
    "totem_spell": ("spells", "Totem Spell"),
    # Offense / utility buildings
    "barracks": ("offense_buildings", "Barracks"),
    "dark_barracks": ("offense_buildings", "Dark Barracks"),
    "dark_spell_factory": ("offense_buildings", "Dark Spell Factory"),
    "workshop": ("offense_buildings", "Workshop"),
    # Defenses
    "archer_tower": ("defenses", "Archer Tower"),
    "mortar": ("defenses", "Mortar"),
    "wizard_tower": ("defenses", "Wizard Tower"),
    "builder_hut": ("defenses", "Builder Hut"),
    # Resource buildings
    "dark_elixir_storage": ("resource_buildings", "Dark Elixir Storage"),
    "helper_hut": ("resource_buildings", "Helper Hut"),
    # Walls
    "wall": ("walls", "Wall"),
}

ACCOUNT_ONLY_ITEM_KEYS: set[str] = set(ACCOUNT_ONLY_CAP_NAME_MAP.keys())

TH_CAP_NAME_MAP.update(ACCOUNT_ONLY_CAP_NAME_MAP)
TH_CAP_LOOKUP_TO_KEY = rebuild_th_cap_lookup()

MIN_COPY_FALLBACK_COUNTS.update({
    "archer_tower": 8,
    "mortar": 4,
    "wizard_tower": 5,
    "builder_hut": 5,
    "dark_elixir_storage": 1,
    "helper_hut": 1,
    # Safety fallback only. Live wall counts should come from TH_CAPS; TH17/TH18 use 325.
    "wall": 325,
})

ITEMS.update({
    # Account-completion-only troops
    "barbarian": ItemMeta("barbarian", "Barbarian", "troop", 4.0, 2.0, 0.0, 1.0, 2.0, lane="lab", source="troop"),
    "archer": ItemMeta("archer", "Archer", "troop", 4.0, 2.0, 0.0, 1.0, 2.0, lane="lab", source="troop"),
    "giant": ItemMeta("giant", "Giant", "troop", 4.2, 2.0, 0.0, 1.0, 2.1, lane="lab", source="troop"),
    "goblin": ItemMeta("goblin", "Goblin", "troop", 3.8, 3.5, 0.0, 1.0, 2.0, lane="lab", source="troop"),
    "wall_breaker": ItemMeta("wall_breaker", "Wall Breaker", "troop", 4.1, 1.5, 0.0, 1.0, 2.0, lane="lab", source="troop"),
    "wizard": ItemMeta("wizard", "Wizard", "troop", 4.6, 1.5, 0.0, 1.0, 2.2, lane="lab", source="troop"),
    "pekka": ItemMeta("pekka", "P.E.K.K.A", "troop", 5.0, 1.0, 0.0, 1.0, 2.4, lane="lab", source="troop"),
    "baby_dragon": ItemMeta("baby_dragon", "Baby Dragon", "troop", 4.8, 1.5, 0.0, 1.0, 2.3, lane="lab", source="troop"),
    "yeti": ItemMeta("yeti", "Yeti", "troop", 5.0, 1.0, 0.0, 1.0, 2.4, lane="lab", source="troop"),
    "dragon_rider": ItemMeta("dragon_rider", "Dragon Rider", "troop", 5.0, 1.0, 0.0, 1.0, 2.4, lane="lab", source="troop"),
    "electro_titan": ItemMeta("electro_titan", "Electro Titan", "troop", 5.2, 1.0, 0.0, 1.0, 2.5, lane="lab", source="troop"),
    "thrower": ItemMeta("thrower", "Thrower", "troop", 5.2, 1.0, 0.0, 1.0, 2.4, lane="lab", source="troop"),
    "meteor_golem": ItemMeta("meteor_golem", "Meteor Golem", "troop", 5.2, 1.0, 0.0, 1.0, 2.6, lane="lab", source="troop"),
    "minion": ItemMeta("minion", "Minion", "troop", 4.0, 2.0, 0.0, 1.0, 2.0, lane="lab", source="troop"),
    "valkyrie": ItemMeta("valkyrie", "Valkyrie", "troop", 4.6, 1.5, 0.0, 1.0, 2.2, lane="lab", source="troop"),
    "golem": ItemMeta("golem", "Golem", "troop", 4.8, 1.0, 0.0, 1.0, 2.3, lane="lab", source="troop"),
    "witch": ItemMeta("witch", "Witch", "troop", 4.7, 1.0, 0.0, 1.0, 2.2, lane="lab", source="troop"),
    "lava_hound": ItemMeta("lava_hound", "Lava Hound", "troop", 4.6, 1.0, 0.0, 1.0, 2.3, lane="lab", source="troop"),
    "bowler": ItemMeta("bowler", "Bowler", "troop", 4.7, 1.0, 0.0, 1.0, 2.2, lane="lab", source="troop"),
    "ice_golem": ItemMeta("ice_golem", "Ice Golem", "troop", 4.5, 1.0, 0.0, 1.0, 2.1, lane="lab", source="troop"),
    "headhunter": ItemMeta("headhunter", "Headhunter", "troop", 4.8, 1.0, 0.0, 1.0, 2.2, lane="lab", source="troop"),
    "druid": ItemMeta("druid", "Druid", "troop", 4.8, 1.0, 0.0, 1.0, 2.3, lane="lab", source="troop"),
    "furnace": ItemMeta("furnace", "Furnace", "troop", 4.8, 1.0, 0.0, 1.0, 2.3, lane="lab", source="troop"),

    # Account-completion-only spells
    "lightning_spell": ItemMeta("lightning_spell", "Lightning Spell", "spell", 4.5, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "healing_spell": ItemMeta("healing_spell", "Healing Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "poison_spell": ItemMeta("poison_spell", "Poison Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "earthquake_spell": ItemMeta("earthquake_spell", "Earthquake Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "jump_spell": ItemMeta("jump_spell", "Jump Spell", "spell", 3.8, 1.0, 0.0, 1.0, 1.8, lane="lab", source="spell"),
    "haste_spell": ItemMeta("haste_spell", "Haste Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "skeleton_spell": ItemMeta("skeleton_spell", "Skeleton Spell", "spell", 3.8, 1.0, 0.0, 1.0, 1.9, lane="lab", source="spell"),
    "clone_spell": ItemMeta("clone_spell", "Clone Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "bat_spell": ItemMeta("bat_spell", "Bat Spell", "spell", 3.8, 1.0, 0.0, 1.0, 1.9, lane="lab", source="spell"),
    "overgrowth_spell": ItemMeta("overgrowth_spell", "Overgrowth Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "ice_block_spell": ItemMeta("ice_block_spell", "Ice Block Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "revive_spell": ItemMeta("revive_spell", "Revive Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),
    "totem_spell": ItemMeta("totem_spell", "Totem Spell", "spell", 4.0, 1.0, 0.0, 1.0, 2.0, lane="lab", source="spell"),

    # Account-completion-only buildings / defenses / resources
    "barracks": ItemMeta("barracks", "Barracks", "building", 1.0, 0.5, 0.0, 1.0, 3.0, lane="builder"),
    "dark_barracks": ItemMeta("dark_barracks", "Dark Barracks", "building", 1.0, 0.5, 0.0, 1.0, 3.0, lane="builder"),
    "dark_spell_factory": ItemMeta("dark_spell_factory", "Dark Spell Factory", "building", 1.0, 0.5, 0.0, 1.0, 3.0, lane="builder"),
    "workshop": ItemMeta("workshop", "Workshop", "building", 1.5, 0.5, 0.0, 1.5, 3.0, lane="builder"),
    "archer_tower": ItemMeta("archer_tower", "Archer Tower", "defense", 0.0, 0.5, 4.5, 1.0, 2.5),
    "mortar": ItemMeta("mortar", "Mortar", "defense", 0.0, 0.5, 4.2, 1.0, 2.4),
    "wizard_tower": ItemMeta("wizard_tower", "Wizard Tower", "defense", 0.0, 0.5, 4.5, 1.0, 2.5),
    "builder_hut": ItemMeta("builder_hut", "Builder Hut", "defense", 0.0, 0.5, 4.0, 1.0, 2.4),
    "dark_elixir_storage": ItemMeta("dark_elixir_storage", "Dark Elixir Storage", "economy", 0.0, 3.0, 0.5, 1.0, 2.0),
    "helper_hut": ItemMeta("helper_hut", "Helper Hut", "economy", 0.0, 1.0, 0.0, 1.0, 1.0),
    "wall": ItemMeta("wall", "Wall", "building", 0.0, 0.0, 3.8, 0.5, 1.5, lane="builder"),
})



def apply_account_only_items(*, th_cap_name_map, min_copy_fallback_counts, items, item_meta, rebuild_th_cap_lookup):
    ...
    return account_only_item_keys, rebuilt_lookup