from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = ROOT / "clash_mmo" / "commands"


def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def discover_commands():
    rows = []
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                func = deco.func
                is_tree_command = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "command"
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "tree"
                )
                if not is_tree_command:
                    continue

                name = node.name
                description = ""
                for kw in deco.keywords:
                    if kw.arg == "name":
                        name = _literal(kw.value) or name
                    elif kw.arg == "description":
                        description = _literal(kw.value) or ""
                rows.append({
                    "command": f"/{name}",
                    "description": description,
                    "file": str(path.relative_to(ROOT)),
                    "function": node.name,
                })
    return sorted(rows, key=lambda row: row["command"])


def write_command_reference(rows):
    out = ROOT / "COMMAND_REFERENCE.md"
    lines = ["# COMMAND REFERENCE", "", f"Total commands discovered: {len(rows)}", ""]
    for row in rows:
        lines.append(f"## {row['command']}")
        lines.append(f"- Description: {row['description'] or 'No description provided'}")
        lines.append(f"- Source File: {row['file']}")
        lines.append(f"- Function: `{row['function']}`")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def write_command_file_map(rows):
    out = ROOT / "COMMAND_FILE_MAP.md"
    lines = ["# COMMAND FILE MAP", ""]
    for row in rows:
        lines.append(f"{row['command']} -> {row['file']}::{row['function']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_player_command_quickstart(rows):
    out = ROOT / "PLAYER_COMMAND_QUICKSTART.md"
    lines = [
        "# PLAYER COMMAND QUICKSTART",
        "",
        "This file is generated from the slash-command decorators in `clash_mmo/commands`.",
        "",
        "## Recommended first commands",
        "",
        "- `/village` — view your profile",
        "- `/daily` — claim timed rewards",
        "- `/farm` — earn steady resources",
        "- `/train` — progress army/training loop",
        "- `/raidvillage` — attack NPC villages",
        "- `/cooldowns` — see what is ready",
        "- `/systemguide` — learn what major systems are for",
        "- `/glossary` — quick term lookup",
        "",
        "## Full discovered command list",
        "",
    ]
    for row in rows:
        lines.append(f"- **{row['command']}** — {row['description'] or 'No description provided'}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = discover_commands()
    write_command_reference(rows)
    write_command_file_map(rows)
    write_player_command_quickstart(rows)
    print(f"Generated docs for {len(rows)} commands.")


if __name__ == "__main__":
    main()
