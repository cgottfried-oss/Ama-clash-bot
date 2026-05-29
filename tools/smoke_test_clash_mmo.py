from __future__ import annotations

from pathlib import Path
import py_compile
import sys

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    "clash_mmo/commands/__init__.py",
    "clash_mmo/commands/market_commands.py",
    "clash_mmo/commands/systems_guide_commands.py",
    "clash_mmo/commands/territory_commands.py",
    "clash_mmo/commands/cosmetic_commands.py",
    "clash_mmo/game/marketplace/black_market.py",
    "clash_mmo/game/cosmetics/service.py",
    "clash_mmo/game/territory/resources.py",
]


def main() -> int:
    failures = []
    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"MISSING: {rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"COMPILE ERROR: {rel}: {type(exc).__name__}: {exc}")

    if failures:
        print("SMOKE TEST FAILED")
        print("\n".join(failures))
        return 1

    print(f"SMOKE TEST PASSED: py_compile validated {len(TARGETS)} targeted files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Patch 63 note:
# Run `python tools/verify_internal_imports.py` for a stronger static check of
# internal clash_mmo/clan_bot imports without importing Discord at runtime.
