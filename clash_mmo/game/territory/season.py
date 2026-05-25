from __future__ import annotations

from datetime import datetime, timezone



def current_territory_season():
    return datetime.now(timezone.utc).strftime("%Y-%m")



def add_conquest_points(state: dict, clan_id: str, amount: int):
    season = current_territory_season()

    seasons = state.setdefault("season_points", {})
    seasons.setdefault(season, {})

    seasons[season][clan_id] = (
        int(seasons[season].get(clan_id, 0)) + int(amount)
    )

    return seasons[season][clan_id]