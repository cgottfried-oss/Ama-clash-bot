from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "clash_mmo" / "game" / "progression" / "costs.py",
    ROOT / "clash_mmo" / "game" / "raids" / "chests.py",
    ROOT / "clash_mmo" / "config" / "economy_config.py",
]


def safe_literal_from_assignment(path: Path, names: set[str]):
    found = {}
    if not path.exists():
        return found
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    try:
                        found[target.id] = ast.literal_eval(node.value)
                    except Exception:
                        pass
    return found


def table_from_dict(title: str, data: dict) -> list[str]:
    lines = [f"## {title}", ""]
    if not data:
        lines.append("_No literal table found._")
        lines.append("")
        return lines
    for key, value in data.items():
        lines.append(f"### {key}")
        lines.append("```json")
        lines.append(repr(value))
        lines.append("```")
        lines.append("")
    return lines


def main():
    extracted = {}
    for path in TARGETS:
        extracted[str(path.relative_to(ROOT))] = safe_literal_from_assignment(
            path,
            {
                "TH_UPGRADE_COSTS",
                "TOWN_HALL_COSTS",
                "PVE_CHEST_DROPS",
                "RAIDVILLAGE_CHEST_DROPS",
                "CHEST_REWARD_TABLES",
                "CHEST_REWARDS",
                "SHOP_ITEMS",
            },
        )

    lines = ["# BALANCE TABLES GENERATED", ""]
    lines.append("Generated from literal Python balance tables where available.")
    lines.append("")
    for rel, tables in extracted.items():
        lines.append(f"# {rel}")
        lines.append("")
        for name, data in tables.items():
            lines.extend(table_from_dict(name, data))
    (ROOT / "BALANCE_TABLES_GENERATED.md").write_text("\n".join(lines), encoding="utf-8")

    summary = ["# BALANCE DOCS AUDIT", ""]
    for rel, tables in extracted.items():
        summary.append(f"- `{rel}`: {', '.join(tables.keys()) if tables else 'no supported literal tables found'}")
    (ROOT / "BALANCE_DOCS_AUDIT.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("Generated BALANCE_TABLES_GENERATED.md and BALANCE_DOCS_AUDIT.md")


if __name__ == "__main__":
    main()
