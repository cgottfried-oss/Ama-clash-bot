from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOTS = {
    "clash_mmo": ROOT / "clash_mmo",
    "clan_bot": ROOT / "clan_bot",
}


def module_exists(module: str) -> bool:
    parts = module.split(".")
    if not parts or parts[0] not in PACKAGE_ROOTS:
        return True

    base = PACKAGE_ROOTS[parts[0]]
    rest = parts[1:]

    module_file = base.joinpath(*rest).with_suffix(".py")
    package_init = base.joinpath(*rest) / "__init__.py"

    return module_file.exists() or package_init.exists()


def scan_file(path: Path):
    missing = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"SYNTAX ERROR: {path.relative_to(ROOT)}: {exc}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith(("clash_mmo.", "clan_bot.")) and not module_exists(name):
                    missing.append(f"{path.relative_to(ROOT)} imports missing module `{name}`")
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            name = node.module
            if name.startswith(("clash_mmo.", "clan_bot.")) and not module_exists(name):
                missing.append(f"{path.relative_to(ROOT)} imports from missing module `{name}`")
    return missing


def main() -> int:
    failures = []
    for package_root in PACKAGE_ROOTS.values():
        if not package_root.exists():
            continue
        for path in sorted(package_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            failures.extend(scan_file(path))

    if failures:
        print("INTERNAL IMPORT VERIFY FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("INTERNAL IMPORT VERIFY PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
