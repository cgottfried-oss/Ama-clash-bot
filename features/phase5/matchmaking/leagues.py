LEAGUES = [
    (0, "Bronze"),
    (1000, "Silver"),
    (2000, "Gold"),
    (3200, "Crystal"),
    (4500, "Master"),
    (6000, "Champion"),
    (8000, "Titan"),
    (10000, "Legend"),
]



def league_for_rating(rating: int):
    current = "Bronze"

    for threshold, league in LEAGUES:
        if rating >= threshold:
            current = league

    return current



def next_league_progress(rating: int):
    for threshold, league in LEAGUES:
        if rating < threshold:
            return {
                "next_league": league,
                "required_rating": threshold,
                "remaining": threshold - rating,
            }

    return {
        "next_league": "MAX",
        "required_rating": rating,
        "remaining": 0,
    }
