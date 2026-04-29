from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import discord


async def post_war_mvp_announcement(
    *,
    war,
    channel,
    clan_chat_channel_id,
    bot,
    get_war_result,
    get_war_id,
    get_war_mvp_stats,
    load_war_banner_context,
    reward_war_coins,
    format_member_mention,
    generate_war_mvp_title,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
    current_war_mvp_file,
    war_mvp_role_id,
    safe_load_json,
    safe_save_json,
    war_rewards=None,
):
    target_channel = channel or bot.get_channel(clan_chat_channel_id)
    if not target_channel:
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    clan_name = clan.get("name", "Our Clan")
    opponent_name = opponent.get("name", "Opponent")

    tag_to_discord, shop_data, banner_now = await load_war_banner_context()
    best_member = get_war_mvp_stats(war, tag_to_discord, shop_data, banner_now)
    if not best_member:
        return

    mvp_reward = None
    if isinstance(war_rewards, dict):
        mvp_reward = war_rewards.get("mvp")

    if not mvp_reward:
        fallback_rewards = await reward_war_coins(war)
        if isinstance(fallback_rewards, dict):
            mvp_reward = fallback_rewards.get("mvp")

    mvp_display = format_member_mention(
        (mvp_reward or {}).get("discord_id"),
        best_member.get("name", "Unknown"),
    )
    mvp_total_reward = int((mvp_reward or {}).get("total_reward", 0))

    clan_stars = clan.get("stars", 0)
    opp_stars = opponent.get("stars", 0)
    clan_destruction = clan.get("destructionPercentage", 0)
    opp_destruction = opponent.get("destructionPercentage", 0)

    result_text, color, _result_hex = get_war_result(clan, opponent)
    mvp_title, mvp_flavor = generate_war_mvp_title()

    embed = discord.Embed(
        title=f"⚔️ {mvp_title} • {clan_name} vs {opponent_name}",
        description=(
            f"**{result_text}**\n"
            f"{clan_name}: **{clan_stars}** ⭐ • **{clan_destruction:.1f}%**\n"
            f"{opponent_name}: **{opp_stars}** ⭐ • **{opp_destruction:.1f}%**\n\n"
            f"🔥 {mvp_flavor}"
        ),
        color=color,
    )

    mvp_lines = [
        f"🏆 **{mvp_display}**",
        f"⭐ {best_member['stars']} stars • 💥 {best_member['destruction']:.1f}% destruction",
        f"🎯 {best_member['triples']} triples • ⚔️ {best_member['attacks']} attacks",
    ]

    if best_member.get("war_banner_active"):
        boost_pct = int(round((float(best_member.get("war_banner_multiplier", 1.0)) - 1) * 100))
        mvp_lines.append(f"🏴 War Banner active: **+{boost_pct}% MVP score**")

    if mvp_total_reward > 0:
        mvp_lines.append(f"🪙 **Coins Awarded:** {mvp_total_reward}")

    embed.add_field(name="MVP", value="\n".join(mvp_lines), inline=False)

    role_result = await rotate_war_mvp_role(
        guild=getattr(target_channel, "guild", None),
        role_id=war_mvp_role_id,
        mvp_discord_id=(mvp_reward or {}).get("discord_id"),
        state_file=current_war_mvp_file,
        war_id=get_war_id(war),
        player_name=best_member.get("name", "Unknown"),
        player_tag=best_member.get("tag", ""),
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        mvp_title=mvp_title,
    )

    presentation_result = await update_war_mvp_role_presentation(
        guild=getattr(target_channel, "guild", None),
        role_id=war_mvp_role_id,
        stars=best_member.get("stars", 0),
        destruction=best_member.get("destruction", 0),
        title=mvp_title,
        rename_role=False,
    )

    if role_result.get("ok"):
        role_note = "⚡ War MVP role assigned until the next War MVP is announced."
        if presentation_result.get("ok"):
            role_note += "\n🎨 Role color updated based on MVP performance."
        embed.add_field(name="Power Role", value=role_note, inline=False)
    elif not role_result.get("skipped"):
        embed.add_field(
            name="Power Role",
            value=f"⚠️ Could not update War MVP role: {role_result.get('reason', 'unknown error')}",
            inline=False,
        )

    content = mvp_display if str(mvp_display).startswith("<@") else None
    await asyncio.wait_for(target_channel.send(content=content, embed=embed), timeout=10)

async def post_final_war_summary(
    *,
    war,
    war_rewards,
    bot,
    war_summary_channel_id,
    war_summary_posts_file,
    current_war_mvp_file,
    war_mvp_role_id,
    get_war_id,
    clan_scope_key,
    get_war_result,
    create_final_war_image,
    load_war_banner_context,
    get_war_mvp_stats,
    format_member_mention,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
    safe_load_json,
    safe_save_json,
):
    if war.get("state") != "warEnded":
        return

    summary_channel = bot.get_channel(war_summary_channel_id)
    if not summary_channel:
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    summary_key = f"{clan_scope_key(clan.get('tag'))}:{get_war_id(war)}"
    posted = await safe_load_json(war_summary_posts_file)
    if not isinstance(posted, dict):
        posted = {}

    if posted.get(summary_key):
        return

    result_text, color, _result_hex = get_war_result(clan, opponent)

    buffer = await create_final_war_image(war)
    file = discord.File(fp=buffer, filename="final_war.png")

    embed = discord.Embed(
        title=f"War Summary • {clan.get('name', 'Our Clan')} vs {opponent.get('name', 'Opponent')}",
        color=color,
    )
    embed.add_field(name="Result", value=f"**{result_text}**", inline=True)

    tag_to_discord, shop_data, banner_now = await load_war_banner_context()
    best_member = get_war_mvp_stats(war, tag_to_discord, shop_data, banner_now)

    mvp_reward = None

    if best_member:
        mvp_reward = war_rewards.get("mvp") if isinstance(war_rewards, dict) else None
        mvp_display = format_member_mention(
            (mvp_reward or {}).get("discord_id"),
            best_member.get("name", "Unknown"),
        )
        mvp_total_reward = int((mvp_reward or {}).get("total_reward", 0))

        description_lines = [
            f"🏆 **War MVP:** {mvp_display}",
            f"⭐ {best_member['stars']} stars • 💥 {best_member['destruction']:.1f}% destruction • 🎯 {best_member['triples']} triples",
        ]

        if mvp_total_reward > 0:
            description_lines.append(f"🪙 **MVP Coins Awarded:** {mvp_total_reward}")

        embed.description = "\n".join(description_lines)

    embed.set_image(url="attachment://final_war.png")

    mention_content = None
    if isinstance(war_rewards, dict):
        discord_id = ((war_rewards.get("mvp") or {}).get("discord_id"))
        if discord_id:
            mention_content = f"<@{discord_id}>"

    if best_member:
        role_result = await rotate_war_mvp_role(
            guild=getattr(summary_channel, "guild", None),
            role_id=war_mvp_role_id,
            mvp_discord_id=(mvp_reward or {}).get("discord_id"),
            state_file=current_war_mvp_file,
            war_id=get_war_id(war),
            player_name=best_member.get("name", "Unknown"),
            player_tag=best_member.get("tag", ""),
            safe_load_json=safe_load_json,
            safe_save_json=safe_save_json,
            mvp_title="War MVP",
        )

        presentation_result = await update_war_mvp_role_presentation(
            guild=getattr(summary_channel, "guild", None),
            role_id=war_mvp_role_id,
            stars=best_member.get("stars", 0),
            destruction=best_member.get("destruction", 0),
            title="War MVP",
            rename_role=False,
        )

        if role_result.get("ok"):
            note = "Assigned"
            if presentation_result.get("ok"):
                note += " + color updated"
            embed.add_field(name="War MVP Role", value=note, inline=True)
        elif not role_result.get("skipped"):
            embed.add_field(
                name="War MVP Role",
                value=f"⚠️ {role_result.get('reason', 'unknown error')}",
                inline=False,
            )

    await asyncio.wait_for(
        summary_channel.send(content=mention_content, embed=embed, file=file),
        timeout=10,
    )

    posted[summary_key] = {
        "clan_tag": clan.get("tag"),
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    await safe_save_json(war_summary_posts_file, posted)