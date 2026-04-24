from __future__ import annotations

STAR_COIN_REWARD = 10
WAR_MVP_BONUS = 150
CLUTCH_COIN_REWARD = 50
CLUTCH_REWARD_TIERS = {
    "top_base": 75,
    "lead_flip": 125,
    "keep_alive": 100,
    "last_stand": 60,
    "underdog_triple": 100,
    "top_three_triple": 90,
    "rank_upset": 80,
}
ADVISOR_DAILY_SYNC_REWARD = 10
ADVISOR_PROGRESS_REWARDS = {25: 50, 50: 100, 75: 200, 100: 500}
ADVISOR_GROUP_REWARDS = {
    "heroes_complete": 75,
    "offense_core_complete": 100,
    "builder_core_complete": 100,
    "war_ready": 150,
}


def mark_reward(mark: int) -> int:
    return ADVISOR_PROGRESS_REWARDS.get(int(mark), 0)
