from __future__ import annotations

# Shop and loot-drop content are intentionally separate from bot_runner.py so the
# economy can grow without turning the runner into a giant config file.

SHOP_ITEMS = {
    "lucky_charm": {
        "name": "Lucky Charm",
        "cost": 150,
        "description": "Adds +50 coins to your next claimed loot drop.",
        "type": "loot_bonus",
        "bonus": 50,
    },
    "clutch_boost": {
        "name": "Clutch Boost",
        "cost": 200,
        "description": "Adds +50 coins to your next clutch reward.",
        "type": "clutch_bonus",
        "bonus": 50,
    },
    "mvp_token": {
        "name": "MVP Token",
        "cost": 500,
        "description": "Adds +100 coins to your next war MVP bonus.",
        "type": "mvp_bonus",
        "bonus": 100,
    },
    "high_roller": {
        "name": "High Roller",
        "cost": 250,
        "description": "Your next loot drop is doubled, but has a 25% chance to bust.",
        "type": "loot_gamble",
        "multiplier": 2,
        "bust_chance": 0.25,
    },
    "loot_shield": {
        "name": "Loot Shield",
        "cost": 175,
        "description": "Passively blocks the next /steal attempt against you, then gets consumed.",
        "type": "steal_defense",
    },
    "drop_reroll": {
        "name": "Drop Reroll",
        "cost": 125,
        "description": "Use /useitem drop_reroll to reroll the current active loot drop reward once.",
        "type": "drop_reroll",
    },
    "war_banner": {
        "name": "War Banner",
        "cost": 300,
        "description": "Use /useitem war_banner to activate a 1-hour war buff: +20% war coin rewards, +10% war stat/MVP score, and -15% steal success chance against you.",
        "type": "timed_buff",
        "duration_seconds": 3600,
        "war_reward_multiplier": 1.20,
        "war_stat_multiplier": 1.10,
        "steal_resistance": 0.15,
    },
}

LOOT_DROP_STYLES = [
    {
        "name": "loot_crate",
        "weight": 50,
        "rewards": [50, 75],
        "spawn_messages": [
            "🛡️ **WAR SPOILS SECURED!**\n\nWar spoils secured from the battlefield. First Chief to type `claim` collects **{reward}** coins.",
            "🏆 **VICTORY LOOT!**\n\nVictory yields fresh spoils for the clan. Type `claim` to collect **{reward}** coins.",
            "🎁 **BATTLE REWARDS!**\n\nBattle rewards collected after the raid. First `claim` earns **{reward}** coins.",
            "🏚️ **FALLEN VILLAGE LOOT!**\n\nLoot recovered from the fallen village. Type `claim` before another Chief grabs **{reward}** coins.",
            "⚔️ **SUCCESSFUL ATTACK!**\n\nSpoils gathered from a successful attack. First `claim` takes **{reward}** coins.",
            "📦 **CLAN FORCES RETURN!**\n\nClan forces return with hard-earned loot. Type `claim` to secure **{reward}** coins.",
        ],
        "claim_messages": [
            "🎉 {user} cracked open the loot crate and got **{reward}** coins!",
            "💰 {user} grabbed the supply drop for **{reward}** coins!",
            "📦 {user} yoinked the crate and banked **{reward}** coins!",
            "🚚 {user} signed for the delivery and found **{reward}** coins!",
            "🧰 {user} opened the mystery box and scored **{reward}** coins!",
        ],
    },
    {
        "name": "treasure_stash",
        "weight": 30,
        "rewards": [75, 100, 125],
        "spawn_messages": [
            "💰 **GOLD, ELIXIR & DARK ELIXIR!**\n\nGold, Elixir, and Dark Elixir secured. Type `claim` to convert the haul into **{reward}** coins.",
            "🏦 **ENEMY STORAGE RAIDED!**\n\nResources plundered from enemy storage. First `claim` banks **{reward}** coins.",
            "🪙 **GOLD & ELIXIR SEIZED!**\n\nGold and Elixir seized in battle. Type `claim` to collect **{reward}** coins.",
            "🛢️ **DARK ELIXIR RAID!**\n\nDark Elixir reserves successfully raided. First `claim` earns **{reward}** coins.",
            "📭 **STORAGES EMPTIED!**\n\nStorages emptied — loot collected. Type `claim` before the haul disappears for **{reward}** coins.",
            "🚚 **RESOURCE HAUL DELIVERED!**\n\nResource haul delivered to your clan. First `claim` receives **{reward}** coins.",
        ],
        "claim_messages": [
            "💎 {user} found the hidden stash and earned **{reward}** coins!",
            "🪙 {user} secured the treasure cache for **{reward}** coins!",
            "🏴‍☠️ {user} raided the stash and hauled off **{reward}** coins!",
            "🔐 {user} opened the lockbox and pocketed **{reward}** coins!",
            "🗺️ {user} followed the map straight to **{reward}** coins!",
        ],
    },
    {
        "name": "war_spoils",
        "weight": 15,
        "rewards": [75, 100],
        "spawn_messages": [
            "💥 **DESTRUCTION COMPLETE!**\n\nDestruction complete — rewards claimed. First `claim` secures **{reward}** coins.",
            "⚔️ **ATTACK SUCCESSFUL!**\n\nAttack successful. War gains secured. Type `claim` to collect **{reward}** coins.",
            "🔥 **DEFENSES CRUSHED!**\n\nEnemy defenses crushed. Loot acquired. First `claim` takes **{reward}** coins.",
            "🎯 **RAID COMPLETE!**\n\nRaid complete. Rewards delivered. Type `claim` before another attacker grabs **{reward}** coins.",
            "🗡️ **STRIKE EXECUTED!**\n\nStrike executed. Resources captured. First `claim` earns **{reward}** coins.",
            "🏁 **VICTORY CONFIRMED!**\n\nVictory confirmed. War spoils collected. Type `claim` to claim **{reward}** coins.",
        ],
        "claim_messages": [
            "⚔️ {user} secured the war spoils and earned **{reward}** coins!",
            "🔥 {user} claimed the battle bonus for **{reward}** coins!",
            "🏰 {user} raided the castle cache for **{reward}** coins!",
            "💥 {user} cleaned up the aftermath and found **{reward}** coins!",
            "🛡️ {user} locked down the victory stash for **{reward}** coins!",
        ],
    },
    {
        "name": "jackpot",
        "weight": 5,
        "rewards": [150, 200, 250],
        "spawn_messages": [
            "🐉 **CLAN TREASURY REINFORCED!**\n\nClan treasury reinforced with new plunder. First `claim` collects **{reward}** coins.",
            "🏰 **WAR TRIBUTE DELIVERED!**\n\nWar tribute delivered to the clan. Type `claim` to receive **{reward}** coins.",
            "💪 **CLAN GROWS STRONGER!**\n\nThe clan grows stronger with each raid. First `claim` earns **{reward}** coins.",
            "📦 **CLAN RESERVES RESTOCKED!**\n\nPlunder added to the clan’s reserves. Type `claim` to collect **{reward}** coins.",
            "👑 **CHIEF'S ORDERS FULFILLED!**\n\nChief's orders fulfilled — loot secured. First `claim` takes **{reward}** coins.",
            "🏆 **RICHES RETURNED!**\n\nVictory brings riches back to the clan. Type `claim` to secure **{reward}** coins.",
        ],
        "claim_messages": [
            "👑 {user} hit the jackpot and walked away with **{reward}** coins!",
            "💥 {user} claimed the mega stash for **{reward}** coins!",
            "🐉 {user} robbed the dragon hoard for **{reward}** coins!",
            "🚨 {user} grabbed the rare drop and banked **{reward}** coins!",
            "🏆 {user} won the gold rush and scored **{reward}** coins!",
        ],
    },
]
