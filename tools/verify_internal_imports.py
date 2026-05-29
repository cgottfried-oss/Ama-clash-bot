from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL_PREFIXES = ("clash_mmo", "clan_bot")


def iter_python_files():
    for path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        yield path


def module_to_path(module: str) -> Path:
    parts = module.split(".")
    return ROOT.joinpath(*parts)


def import_exists(module: str) -> bool:
    base = module_to_path(module)
    return base.with_suffix(".py").exists() or (base / "__init__.py").exists()


def main() -> int:
    failures = []
    scanned = 0

    for path in iter_python_files():
        scanned += 1
        rel = path.relative_to(ROOT)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            failures.append(f"SYNTAX {rel}: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith(INTERNAL_PREFIXES) and not import_exists(name):
                        failures.append(f"MISSING IMPORT {rel}: import {name}")
            elif isinstance(node, ast.ImportFrom):
                if not node.module:
                    continue
                name = node.module
                if name.startswith(INTERNAL_PREFIXES) and not import_exists(name):
                    failures.append(f"MISSING IMPORT {rel}: from {name} import ...")

    print("# INTERNAL IMPORT VERIFY")
    print()
    print(f"Python files scanned: {scanned}")
    print(f"Failures: {len(failures)}")
    print()

    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("- all internal imports resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
