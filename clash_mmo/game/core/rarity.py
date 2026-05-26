RARITIES = {
    "common": {
        "color": 0x95A5A6,
        "multiplier": 1.0,
    },
    "rare": {
        "color": 0x3498DB,
        "multiplier": 1.15,
    },
    "epic": {
        "color": 0x9B59B6,
        "multiplier": 1.35,
    },
    "legendary": {
        "color": 0xF39C12,
        "multiplier": 1.65,
    },
}


def normalize_rarity(rarity: str) -> str:
    rarity = str(rarity or "common").strip().lower()

    if rarity not in RARITIES:
        return "common"

    return rarity



def rarity_multiplier(rarity: str) -> float:
    rarity = normalize_rarity(rarity)
    return float(RARITIES[rarity]["multiplier"])