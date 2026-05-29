def default_cosmetics():
    return {
        "owned": [],
        "equipped": {},
    }


def ensure_cosmetics(profile: dict) -> dict:
    cosmetics = profile.setdefault("cosmetics", default_cosmetics())
    if not isinstance(cosmetics, dict):
        cosmetics = default_cosmetics()
        profile["cosmetics"] = cosmetics
    cosmetics.setdefault("owned", [])
    cosmetics.setdefault("equipped", {})
    return cosmetics


def owns_cosmetic(profile: dict, cosmetic_id: str) -> bool:
    cosmetics = ensure_cosmetics(profile)
    return str(cosmetic_id) in {str(item) for item in cosmetics.get("owned", [])}


def grant_cosmetic(profile: dict, cosmetic_id: str) -> bool:
    cosmetics = ensure_cosmetics(profile)
    cosmetic_id = str(cosmetic_id)
    owned = cosmetics.setdefault("owned", [])
    if cosmetic_id in owned:
        return False
    owned.append(cosmetic_id)
    return True


def equip_cosmetic(profile: dict, slot: str, cosmetic_id: str) -> bool:
    if not owns_cosmetic(profile, cosmetic_id):
        return False
    cosmetics = ensure_cosmetics(profile)
    cosmetics.setdefault("equipped", {})[str(slot)] = str(cosmetic_id)
    return True
