from __future__ import annotations


def clan_scope_key(clan_tag: str | None, normalize_tag) -> str:
    normalized = normalize_tag(clan_tag or "")
    return (normalized or "main").replace("#", "")


def is_main_clan_tag(clan_tag: str | None, main_clan_tag: str | None, normalize_tag) -> bool:
    return bool(main_clan_tag and normalize_tag(clan_tag or "") == normalize_tag(main_clan_tag))


def scoped_state_file(base_path: str, clan_tag: str | None, main_clan_tag: str | None, normalize_tag) -> str:
    import os

    if is_main_clan_tag(clan_tag, main_clan_tag, normalize_tag):
        return base_path

    root, ext = os.path.splitext(base_path)
    return f"{root}_{clan_scope_key(clan_tag, normalize_tag)}{ext or '.txt'}"


def war_channel_id_for_clan(
    clan_tag: str | None,
    *,
    main_clan_tag: str | None,
    war_channel_id: int,
    feeder_war_channel_id: int,
    normalize_tag,
) -> int:
    if is_main_clan_tag(clan_tag, main_clan_tag, normalize_tag):
        return war_channel_id
    return feeder_war_channel_id or war_channel_id
