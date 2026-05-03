from __future__ import annotations

import random
from typing import Any, Awaitable, Callable

import discord


CLUTCH_REASON_LABELS = {
    "top_base": "top base",
    "top_three_triple": "enemy top 3 triple",
    "underdog_triple": "town hall upset",
    "rank_upset": "reach triple",
    "lead_flip": "war swing",
    "keep_alive": "kept us alive",
    "last_stand": "late cleanup",
}


def build_clutch_message_templates(clan_name: str, mention: str, defender_pos_display: Any) -> dict[str, list[str]]:
    return {
        "top_base": [
            f"\U0001F6A8 **{clan_name} WAR SWING**\n\n{mention} just tripled #{defender_pos_display} \U0001F624\U0001F525",
            f"\U0001F525 **{clan_name} BIG HIT**\n\n{mention} demolished #{defender_pos_display} — huge for us",
        ],
        "lead_flip": [
            f"\U0001F4C8 **{clan_name} MOMENTUM SHIFT**\n\n{mention} just flipped the war with that hit on #{defender_pos_display} \U0001F440\U0001F525",
            f"\U0001F6A8 **{clan_name} CLUTCH SWING**\n\n{mention} just changed the war math on #{defender_pos_display} \U0001F624",
        ],
        "keep_alive": [
            f"\U0001FAC0 **{clan_name} STILL ALIVE**\n\n{mention} kept us in this war with a huge triple on #{defender_pos_display} \U0001F525",
            f"\u2694\ufe0f **{clan_name} COMEBACK HIT**\n\n{mention} just pulled us right back into it on #{defender_pos_display}",
        ],
        "last_stand": [
            f"\u23F0 **{clan_name} LAST STAND**\n\n{mention} cleaned up #{defender_pos_display} when it mattered most \U0001F440\U0001F525",
            f"\U0001F6A8 **{clan_name} LAST SECOND HERO**\n\n{mention} just saved that base at the buzzer \U0001F624",
        ],
        "top_three_triple": [
            f"\U0001F3AF **{clan_name} STATEMENT HIT**\n\n{mention} just tripled one of their top bases — #{defender_pos_display} got smoked \U0001F525",
            f"\U0001F4A5 **{clan_name} ELITE TRIPLE**\n\n{mention} took down enemy #{defender_pos_display} like it was light work \U0001F624",
        ],
        "underdog_triple": [
            f"\U0001F199 **{clan_name} UPSET ALERT**\n\n{mention} punched up and tripled #{defender_pos_display} \U0001F440\U0001F525",
            f"\u26A1 **{clan_name} TOWN HALL UPSET**\n\n{mention} just outclassed a stronger base at #{defender_pos_display}",
        ],
        "rank_upset": [
            f"\U0001F94A **{clan_name} REACH HIT**\n\n{mention} just took down a base above their rank — #{defender_pos_display} got folded \U0001F525",
            f"\U0001F680 **{clan_name} CLUTCH UPSET**\n\n{mention} reached up and buried #{defender_pos_display} \U0001F624",
        ],
    }


async def post_clutch_moment(
    *,
    channel: discord.abc.Messageable | None,
    attack: dict[str, Any],
    war: dict[str, Any],
    attacker_tag: str,
    attacker_name: str,
    attack_id: str,
    clutch_type: str | None,
    get_defender_position: Callable[[dict[str, Any], dict[str, Any]], Any],
    resolve_discord_mention: Callable[[str, str], Awaitable[str]],
    reward_clutch_coins: Callable[..., Awaitable[dict[str, Any]]],
    normalize_tag: Callable[[str], str],
) -> None:
    if not channel or not clutch_type:
        return

    defender_pos = get_defender_position(attack, war)
    defender_pos_display = defender_pos if defender_pos is not None else "?"
    clan_name = war.get("clan", {}).get("name", "Clan")
    mention = await resolve_discord_mention(attacker_tag, attacker_name)

    messages = build_clutch_message_templates(clan_name, mention, defender_pos_display)

    reward_result = await reward_clutch_coins(
        attacker_tag,
        attacker_name,
        attack_id,
        clutch_type=clutch_type,
    )

    fallback = f"\U0001F525 **{clan_name} HUGE HIT**\n\n{mention} came through big on #{defender_pos_display}"
    if reward_result and reward_result.get("ok"):
        reward_amount = int(reward_result.get("reward", 0) or 0)
        msg = random.choice(messages.get(clutch_type, [fallback])) + f"\n\n\U0001F4B0 +{reward_amount} coins"
    else:
        failure_reason = (reward_result or {}).get("reason", "unknown")
        print(
            f"[CLUTCH] Reward skipped for {attacker_name} ({normalize_tag(attacker_tag or '')}) "
            f"attack_id={attack_id} reason={failure_reason}"
        )
        msg = random.choice(messages.get(clutch_type, [fallback]))
        if failure_reason == "unlinked":
            msg += "\n\n⚠️ No linked Discord account found, so no coins were awarded."
        elif failure_reason == "duplicate":
            msg += "\n\n♻️ This clutch hit was already rewarded earlier."

    await channel.send(msg)


async def post_clutch_summary(
    *,
    channel: discord.abc.Messageable | None,
    war: dict[str, Any],
    clutch_hits: list[dict[str, Any]],
    get_defender_position: Callable[[dict[str, Any], dict[str, Any]], Any],
    get_clutch_reward_amount: Callable[[str | None], int],
) -> None:
    if not channel or not clutch_hits:
        return

    clan_name = war.get("clan", {}).get("name", "Clan")
    lines = []

    for hit in clutch_hits[:5]:
        defender_pos = get_defender_position(hit["attack"], war)
        defender_pos_display = defender_pos if defender_pos is not None else "?"
        reason = CLUTCH_REASON_LABELS.get(hit.get("clutch_type"), "clutch hit")
        reward_amount = get_clutch_reward_amount(hit.get("clutch_type"))
        lines.append(f"• {hit['attacker_name']} tripled #{defender_pos_display} ({reason}, +{reward_amount} coins)")

    extra_count = len(clutch_hits) - len(lines)
    extra_line = f"\n…and {extra_count} more." if extra_count > 0 else ""

    msg = (
        f"\U0001F525 **{clan_name} CLUTCH RECAP**\n\n"
        f"Detected {len(clutch_hits)} new clutch hits since the last check, so I bundled them instead of spamming the chat.\n\n"
        + "\n".join(lines)
        + extra_line
    )
    await channel.send(msg)
