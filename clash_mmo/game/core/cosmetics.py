def default_cosmetics():
    return {
        "owned": {
            "banners": [],
            "borders": [],
            "titles": [],
            "effects": [],
        },
        "equipped": {
            "banner": None,
            "border": None,
            "title": None,
            "effect": None,
        },
    }



def unlock_cosmetic(cosmetics: dict, category: str, cosmetic_id: str):
    cosmetics.setdefault("owned", {})
    cosmetics["owned"].setdefault(category, [])

    if cosmetic_id not in cosmetics["owned"][category]:
        cosmetics["owned"][category].append(cosmetic_id)

    return cosmetics



def equip_cosmetic(cosmetics: dict, slot: str, cosmetic_id: str):
    cosmetics.setdefault("equipped", {})
    cosmetics["equipped"][slot] = cosmetic_id
    return cosmetics