from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [ROOT / "clash_mmo", ROOT / "clan_bot"]

PROFILE_KEY_PATTERNS = [
    re.compile(r"profile\[['\"]([^'\"]+)['\"]\]"),
    re.compile(r"profile\.get\(['\"]([^'\"]+)['\"]"),
    re.compile(r"profile\.setdefault\(['\"]([^'\"]+)['\"]"),
]

STATE_KEY_PATTERNS = [
    re.compile(r"state\[['\"]([^'\"]+)['\"]\]"),
    re.compile(r"state\.get\(['\"]([^'\"]+)['\"]"),
    re.compile(r"state\.setdefault\(['\"]([^'\"]+)['\"]"),
]

RESOURCE_KEYS = {
    "gold",
    "elixir",
    "dark_elixir",
    "gems",
    "raid_medals",
    "clan_xp",
    "shiny_ore",
    "glowy_ore",
    "starry_ore",
}


def iter_py_files():
    for root in SCAN_ROOTS:
        if root.exists():
            for path in sorted(root.rglob("*.py")):
                if "__pycache__" not in path.parts:
                    yield path


def collect_keys(patterns):
    counts = Counter()
    locations: dict[str, set[str]] = {}
    for path in iter_py_files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                key = match.group(1)
                counts[key] += 1
                locations.setdefault(key, set()).add(rel)
    return counts, locations


def write_schema(profile_counts, profile_locations, state_counts, state_locations):
    lines = ["# MMO STATE DATA SCHEMA", ""]
    lines.append("Generated from source-code access patterns.")
    lines.append("")
    lines.append("## Top-Level State Keys")
    lines.append("")
    for key, count in state_counts.most_common():
        files = ", ".join(sorted(state_locations.get(key, []))[:5])
        lines.append(f"- `{key}` — {count} reference(s) — {files}")
    lines.append("")
    lines.append("## Player Profile Keys")
    lines.append("")
    for key, count in profile_counts.most_common():
        files = ", ".join(sorted(profile_locations.get(key, []))[:5])
        lines.append(f"- `players[user_id][\"{key}\"]` — {count} reference(s) — {files}")
    lines.append("")
    lines.append("## Core Resource Keys")
    lines.append("")
    for key in sorted(RESOURCE_KEYS):
        lines.append(f"- `{key}` — profile resource field" if key in profile_counts else f"- `{key}` — not directly detected as profile key")
    (ROOT / "MMO_STATE_SCHEMA_GENERATED.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_resource_flow(profile_locations):
    lines = ["# RESOURCE FLOW GENERATED", ""]
    lines.append("Generated from detected resource-key locations.")
    lines.append("")
    for key in sorted(RESOURCE_KEYS):
        lines.append(f"## {key}")
        files = sorted(profile_locations.get(key, []))
        if files:
            for rel in files:
                lines.append(f"- `{rel}`")
        else:
            lines.append("- No direct profile-key references detected.")
        lines.append("")
    (ROOT / "RESOURCE_FLOW_GENERATED.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    profile_counts, profile_locations = collect_keys(PROFILE_KEY_PATTERNS)
    state_counts, state_locations = collect_keys(STATE_KEY_PATTERNS)
    write_schema(profile_counts, profile_locations, state_counts, state_locations)
    write_resource_flow(profile_locations)
    print(f"Detected {len(profile_counts)} profile keys and {len(state_counts)} state keys.")


if __name__ == "__main__":
    main()
