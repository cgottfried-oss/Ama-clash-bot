from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = ROOT / "clash_mmo" / "commands"


def command_name_from_decorator(deco, fallback: str) -> str | None:
    if not isinstance(deco, ast.Call):
        return None
    func = deco.func
    if not isinstance(func, ast.Attribute) or func.attr != "command":
        return None

    for kw in deco.keywords:
        if kw.arg == "name":
            try:
                return str(ast.literal_eval(kw.value))
            except Exception:
                return fallback
    return fallback


def main() -> int:
    commands = defaultdict(list)

    for path in sorted(COMMANDS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            print(f"Syntax error in {path.relative_to(ROOT)}: {exc}")
            return 1

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                name = command_name_from_decorator(deco, node.name)
                if name:
                    commands[name].append(f"{path.relative_to(ROOT)}::{node.name}")

    duplicates = {name: locs for name, locs in commands.items() if len(locs) > 1}

    print("# DUPLICATE COMMAND VERIFY")
    print()
    print(f"Commands discovered: {len(commands)}")
    print(f"Duplicate names: {len(duplicates)}")
    print()

    if duplicates:
        print("## Duplicates")
        for name, locs in sorted(duplicates.items()):
            print(f"- /{name}")
            for loc in locs:
                print(f"  - {loc}")
        return 1

    print("## Duplicates")
    print("- none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
