from __future__ import annotations

# Shop and loot-drop content are intentionally separate from bot_runner.py so the
# economy can grow without turning the runner into a giant config file.

SHOP_ITEMS = {
    "lucky_charm": {
        "name": "Lucky Charm",
        "cost": 75,
        "description": "Adds +50 coins to your next claimed loot drop.",
        "type": "loot_bonus",
        "bonus": 50,
    },
    "clutch_boost": {
        "name": "Clutch Boost",
        "cost": 125,
        "description": "Adds +50 coins to your next clutch reward.",
        "type": "clutch_bonus",
        "bonus": 50,
    },
    "mvp_token": {
        "name": "MVP Token",
        "cost": 300,
        "description": "Adds +100 coins to your next war MVP bonus.",
        "type": "mvp_bonus",
        "bonus": 100,
    },
    "high_roller": {
        "name": "High Roller",
        "cost": 150,
        "description": "Your next loot drop is doubled, but has a 25% chance to bust.",
        "type": "loot_gamble",
        "multiplier": 2,
        "bust_chance": 0.25,
    },
    "loot_shield": {
        "name": "Loot Shield",
        "cost": 125,
        "description": "Passively blocks the next /steal attempt against you, then gets consumed.",
        "type": "steal_defense",
    },
    "drop_reroll": {
        "name": "Drop Reroll",
        "cost": 75,
        "description": "Use /useitem drop_reroll to reroll the current active loot drop reward once.",
        "type": "drop_reroll",
    },
    "war_banner": {
        "name": "War Banner",
        "cost": 250,
        "description": "Use /useitem war_banner to activate a 1-hour war buff: +20% war coin rewards, +10% war stat/MVP score, and -15% steal success chance against you.",
        "type": "timed_buff",
        "duration_seconds": 3600,
        "war_reward_multiplier": 1.20,
        "war_stat_multiplier": 1.10,
        "steal_resistance": 0.15,
    },
    "training_potion": {
        "name": "Training Potion",
        "cost": 300,
        "description": "Use /useitem training_potion to make your next 1 raid earn +15% Gold and Clan XP.",
        "type": "raid_boost_charges",
        "charges": 1,
        "gold_multiplier": 1.15,
        "xp_multiplier": 1.15,
    },
    "resource_potion": {
        "name": "Resource Potion",
        "cost": 275,
        "description": "Use /useitem resource_potion to make your next 1 farm run earn +20% Gold.",
        "type": "farm_boost_charges",
        "charges": 1,
        "gold_multiplier": 1.20,
    },
    "builder_potion": {
        "name": "Builder Potion",
        "cost": 250,
        "description": "Use /useeconomyitem builder_potion to clear your raid cooldown once. Has a 30-minute use cooldown.",
        "type": "cooldown_clear",
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
            "🛡️ {user} secured the battlefield spoils and collected **{reward}** coins!",
            "🏆 {user} claimed the victory loot and earned **{reward}** coins for the clan!",
            "🎁 {user} gathered the battle rewards and pocketed **{reward}** coins!",
            "🏚️ {user} recovered loot from the fallen village and gained **{reward}** coins!",
            "⚔️ {user} returned from a successful attack with **{reward}** coins!",
            "📦 {user} unloaded the clan forces' hard-earned loot for **{reward}** coins!",
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
            "💰 {user} converted the Gold, Elixir, and Dark Elixir haul into **{reward}** coins!",
            "🏦 {user} emptied the enemy storages and banked **{reward}** coins!",
            "🪙 {user} seized the Gold and Elixir haul for **{reward}** coins!",
            "🛢️ {user} raided the Dark Elixir reserves and earned **{reward}** coins!",
            "📭 {user} swept the storages clean and collected **{reward}** coins!",
            "🚚 {user} delivered the resource haul and received **{reward}** coins!",
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
            "💥 {user} completed the destruction run and secured **{reward}** coins!",
            "⚔️ {user} locked in the successful attack and collected **{reward}** coins!",
            "🔥 {user} crushed the enemy defenses and acquired **{reward}** coins!",
            "🎯 {user} finished the raid and claimed **{reward}** coins!",
            "🗡️ {user} executed the strike and captured **{reward}** coins!",
            "🏁 {user} confirmed the victory and collected **{reward}** coins in war spoils!",
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
            "🐉 {user} reinforced the clan treasury and collected **{reward}** coins!",
            "🏰 {user} accepted the war tribute and received **{reward}** coins!",
            "💪 {user} made the clan stronger and earned **{reward}** coins!",
            "📦 {user} restocked the clan reserves with **{reward}** coins!",
            "👑 {user} fulfilled the Chief's orders and secured **{reward}** coins!",
            "🏆 {user} brought riches back to the clan and claimed **{reward}** coins in war spoils!",
        ],
    },
]
