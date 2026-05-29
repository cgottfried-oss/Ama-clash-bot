from __future__ import annotations

import discord


def format_event_summary(event: dict) -> str:
    name = event.get("name", "Unknown Event")
    emoji = event.get("emoji", "✨")
    description = event.get("description", "No description.")
    ends_at = int(event.get("ends_at", 0) or 0)
    target = event.get("target", "global")
    return f"{emoji} **{name}** — {description}\nTarget: `{target}` • Ends: <t:{ends_at}:R>"


def format_event_embed(event: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"{event.get('emoji', '✨')} {event.get('name', 'World Event')}",
        description=event.get("description", "No description."),
        color=0x9B59B6,
    )
    embed.add_field(name="Target", value=str(event.get("target", "global")).replace("_", " ").title(), inline=True)
    embed.add_field(name="Ends", value=f"<t:{int(event.get('ends_at', 0) or 0)}:R>", inline=True)
    effects = event.get("effects", {}) or {}
    if effects:
        effect_lines = [f"`{key}`: **{value}**" for key, value in effects.items()]
        embed.add_field(name="Effects", value="\n".join(effect_lines), inline=False)
    rewards = event.get("resolution_rewards", {}) or {}
    if rewards:
        reward_lines = [f"`{key}`: **{value:,}**" for key, value in rewards.items()]
        embed.add_field(name="Resolution Rewards", value="\n".join(reward_lines), inline=False)
    return embed
