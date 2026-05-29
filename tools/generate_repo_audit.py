from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_ROOTS = [ROOT / "clash_mmo", ROOT / "clan_bot"]


def iter_py_files():
    for base in PY_ROOTS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" not in path.parts:
                yield path


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


def parse_file(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main():
    imports = defaultdict(set)
    imported_by = defaultdict(set)
    state_refs = Counter()
    large_files = []

    for path in iter_py_files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8", errors="ignore")
        line_count = text.count("\n") + 1
        if line_count >= 250:
            large_files.append((line_count, rel))

        for key in [
            "load_mmo_state",
            "update_mmo_state",
            "ensure_player_profile",
            "profile[",
            "profile.get",
            "cooldowns",
            "boosts",
            "inventory",
            "heroes",
            "territories",
            "marketplace",
            "cosmetics",
        ]:
            count = text.count(key)
            if count:
                state_refs[key] += count

        tree = parse_file(path)
        if tree is None:
            continue

        this_mod = module_name(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    imports[this_mod].add(name)
                    imported_by[name].add(this_mod)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports[this_mod].add(node.module)
                    imported_by[node.module].add(this_mod)

    audit = ROOT / "ARCHITECTURE_AUDIT.md"
    lines = ["# ARCHITECTURE AUDIT", ""]
    lines.append("## Large Files")
    lines.append("")
    for count, rel in sorted(large_files, reverse=True)[:30]:
        lines.append(f"- `{rel}` — {count} lines")
    lines.append("")

    lines.append("## MMO State / Domain Pattern Counts")
    lines.append("")
    for key, count in state_refs.most_common():
        lines.append(f"- `{key}` — {count}")
    lines.append("")

    lines.append("## Internal Dependency Hotspots")
    lines.append("")
    for mod, users in sorted(imported_by.items(), key=lambda item: len(item[1]), reverse=True)[:40]:
        if mod.startswith("clash_mmo") or mod.startswith("clan_bot"):
            lines.append(f"- `{mod}` imported by {len(users)} module(s)")
    lines.append("")

    lines.append("## Suggested Next Refactor Targets")
    lines.append("")
    lines.append("1. Continue reducing high-line-count command modules.")
    lines.append("2. Keep moving direct `profile[...]` parsing into shared helpers.")
    lines.append("3. Keep all player-facing docs generated from source with `tools/generate_clash_mmo_docs.py`.")
    lines.append("4. Keep black market, territory, cosmetics, and system guide documented together.")
    audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {audit.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
