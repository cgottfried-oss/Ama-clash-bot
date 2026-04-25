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
        "description": "Use /useitem war_banner to equip a cosmetic banner for future profile/card displays.",
        "type": "cosmetic",
    },
}

LOOT_DROP_STYLES = [
    {
        "name": "loot_crate",
        "weight": 50,
        "rewards": [50, 75],
        "spawn_messages": [
            "📦 **LOOT CRATE FOUND!**\n\nFirst person to type `claim` gets **{reward}** coins.",
            "💰 **SUPPLY DROP!**\n\nType `claim` before someone else snags **{reward}** coins.",
            "🎁 **BONUS DROP!**\n\nFirst `claim` takes **{reward}** coins.",
            "📬 **CLAN DELIVERY!**\n\nA crate just hit the chat. Type `claim` for **{reward}** coins.",
            "🧰 **MYSTERY BOX!**\n\nFastest `claim` cracks it open for **{reward}** coins.",
            "🚚 **LOOT TRUCK ARRIVED!**\n\nType `claim` to unload **{reward}** coins.",
            "📦 **UNMARKED CRATE!**\n\nProbably safe. Probably. First `claim` gets **{reward}** coins.",
            "🪂 **AIR DROP INBOUND!**\n\nType `claim` before it gets raided for **{reward}** coins.",
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
            "🪙 **HIDDEN STASH!**\n\nType `claim` to grab **{reward}** coins before it disappears.",
            "💎 **TREASURE CACHE!**\n\nFastest `claim` wins **{reward}** coins.",
            "🏴‍☠️ **RAID LOOT FOUND!**\n\nType `claim` to take **{reward}** coins.",
            "🗺️ **SECRET MAP FOUND!**\n\nFollow it with `claim` and collect **{reward}** coins.",
            "🔐 **LOCKBOX SPOTTED!**\n\nFirst `claim` pops it open for **{reward}** coins.",
            "🪨 **BURIED LOOT!**\n\nDig fast. Type `claim` for **{reward}** coins.",
            "💰 **GOBLIN STASH!**\n\nSomeone left coins unattended. Type `claim` for **{reward}**.",
            "🏦 **VAULT LEAK!**\n\nFirst `claim` catches **{reward}** coins before they vanish.",
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
            "⚔️ **WAR SPOILS!**\n\nThe clan found extra loot. Type `claim` to collect **{reward}** coins.",
            "🔥 **BATTLE BONUS!**\n\nFirst to type `claim` secures **{reward}** coins.",
            "🛡️ **VICTORY STASH!**\n\nClaim the spoils for **{reward}** coins before someone else does.",
            "🎯 **PERFECT RAID BONUS!**\n\nType `claim` to cash in **{reward}** coins.",
            "🏰 **CASTLE CACHE!**\n\nThe treasury cracked open. First `claim` gets **{reward}** coins.",
            "💥 **AFTERMATH LOOT!**\n\nType `claim` to sweep up **{reward}** coins.",
            "⚒️ **SIEGE SALVAGE!**\n\nFirst `claim` recovers **{reward}** coins.",
            "🧨 **BASE GOT COOKED!**\n\nClaim the leftovers for **{reward}** coins.",
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
            "👑 **JACKPOT DROP!**\n\nType `claim` right now for **{reward}** coins.",
            "💥 **MEGA STASH!**\n\nFirst `claim` gets the full **{reward}** coin haul.",
            "🏆 **GOLD RUSH!**\n\nOne person is about to walk away with **{reward}** coins.",
            "🚨 **RARE DROP!**\n\nNo time to think. Type `claim` for **{reward}** coins.",
            "🐉 **DRAGON HOARD!**\n\nFirst `claim` steals **{reward}** coins from the pile.",
            "🌋 **VOLCANIC VAULT!**\n\nIt is literally raining coins. `claim` for **{reward}**.",
            "💫 **COSMIC DROP!**\n\nThe RNG gods chose violence. First `claim` gets **{reward}** coins.",
            "🤑 **BIG MONEY DROP!**\n\nType `claim` and try not to fumble **{reward}** coins.",
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
