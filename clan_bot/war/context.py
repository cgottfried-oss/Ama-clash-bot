from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class WarRuntimeContext:
    bot: Any
    economy: Any

    data_dir: str
    assets_dir: str
    templates_dir: str

    war_channel_id: int
    feeder_war_channel_id: int
    clan_chat_channel_id: int
    war_summary_channel_id: int
    war_mvp_role_id: int

    main_clan_tag: str | None
    clan_tags: list[str]

    linked_file: str
    war_pings_file: str
    war_end_file: str
    war_summary_posts_file: str
    performance_file: str
    monthly_mvp_file: str
    current_war_mvp_file: str

    war_template_path: str
    final_war_template_path: str
    donation_template_path: str

    safe_load_json: Callable
    safe_save_json: Callable
    update_json_file: Callable
    normalize_tag: Callable
    normalize_linked_data: Callable
    build_tag_to_discord_map: Callable
    get_cached_or_fetch: Callable
    fetch_clan_data: Callable | None = None
