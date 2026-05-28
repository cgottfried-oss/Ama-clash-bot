from __future__ import annotations
from typing import Any


def normalize_tag(tag: Any) -> str:
    return str(tag or "").strip().upper().replace("O", "0")


def normalize_user_linked_data(data: Any) -> dict[str, list[dict[str, str]]]:
    """Normalize linked data to primary bot shape: discord_id -> [{tag, name}]."""
    if not isinstance(data, dict):
        return {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for key, value in data.items():
        key_str = str(key)
        # Legacy/simple inverted shape: player tag -> discord id
        if normalize_tag(key_str).startswith("#") and isinstance(value, str):
            normalized.setdefault(str(value), []).append({"tag": normalize_tag(key_str), "name": "Unknown"})
            continue

        entries = value if isinstance(value, list) else [value]
        clean_entries: list[dict[str, str]] = []
        for entry in entries:
            if isinstance(entry, str):
                tag = normalize_tag(entry)
                if tag:
                    clean_entries.append({"tag": tag, "name": "Unknown"})
            elif isinstance(entry, dict):
                # Current shape: discord id -> {tag/name} or list entries.
                if not entry.get("discord_id"):
                    tag = normalize_tag(entry.get("tag") or entry.get("player_tag"))
                    if tag:
                        clean_entries.append({"tag": tag, "name": str(entry.get("name", "Unknown"))})
                        continue
                # Legacy/inverted shape: player tag -> {discord_id/user_id/...}
                discord_id = entry.get("discord_id") or entry.get("user_id")
                tag = normalize_tag(entry.get("player_tag") or entry.get("tag") or key_str)
                if tag and discord_id is not None:
                    normalized.setdefault(str(discord_id), []).append(
                        {"tag": tag, "name": str(entry.get("name", "Unknown"))}
                    )
        if clean_entries:
            normalized.setdefault(key_str, []).extend(clean_entries)
    return normalized


def normalize_tag_linked_data(data: Any) -> dict[str, dict[str, str]]:
    """Normalize linked data to tag-keyed shape: tag -> metadata."""
    by_tag: dict[str, dict[str, str]] = {}
    for discord_id, entries in normalize_user_linked_data(data).items():
        for entry in entries:
            tag = normalize_tag(entry.get("tag"))
            if tag:
                by_tag[tag] = {
                    "player_tag": tag,
                    "tag": tag,
                    "discord_id": str(discord_id),
                    "name": str(entry.get("name", "Unknown")),
                }
    return by_tag


def build_tag_to_discord_map(linked_data: Any) -> dict[str, str]:
    return {
        tag: str(entry.get("discord_id"))
        for tag, entry in normalize_tag_linked_data(linked_data).items()
        if isinstance(entry, dict) and entry.get("discord_id")
    }
