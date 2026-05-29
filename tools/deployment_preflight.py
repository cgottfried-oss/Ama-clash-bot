from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "bot_runner.py",
    "clash_mmo/commands/__init__.py",
    "clash_mmo/game/state.py",
]

OPTIONAL_BUT_EXPECTED = [
    "COMMAND_REFERENCE.md",
    "DEVELOPER_GUIDE.md",
    "PLAYER_COMMAND_QUICKSTART.md",
    "tools/verify_internal_imports.py",
    "tools/smoke_test_clash_mmo.py",
    "tools/verify_command_registration.py",
    "tools/verify_duplicate_commands.py",
]

COMMON_ENV_HINTS = [
    "DISCORD_TOKEN",
    "TOKEN",
    "BOT_TOKEN",
]


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    failures = []
    warnings = []

    for rel in REQUIRED_FILES:
        if not exists(rel):
            failures.append(f"Missing required file: {rel}")

    for rel in OPTIONAL_BUT_EXPECTED:
        if not exists(rel):
            warnings.append(f"Missing expected helper/doc file: {rel}")

    if not any(os.environ.get(name) for name in COMMON_ENV_HINTS):
        warnings.append(
            "No common Discord token env var detected. Coolify must define the token env var your bot_runner.py expects."
        )

    compile_code, compile_out, compile_err = run([sys.executable, "-m", "compileall", "-q", str(ROOT)])
    if compile_code != 0:
        failures.append("compileall failed")

    verifier = ROOT / "tools" / "verify_internal_imports.py"
    verify_code = 0
    verify_out = ""
    verify_err = ""
    if verifier.exists():
        verify_code, verify_out, verify_err = run([sys.executable, str(verifier)])
        if verify_code != 0:
            failures.append("internal import verifier failed")
    else:
        warnings.append("Internal import verifier not present.")

    duplicate_verifier = ROOT / "tools" / "verify_duplicate_commands.py"
    duplicate_verify_code = 0
    duplicate_verify_out = ""
    duplicate_verify_err = ""
    if duplicate_verifier.exists():
        duplicate_verify_code, duplicate_verify_out, duplicate_verify_err = run([sys.executable, str(duplicate_verifier)])
        if duplicate_verify_code != 0:
            failures.append("duplicate command verifier failed")
    else:
        warnings.append("Duplicate command verifier not present.")

    command_verifier = ROOT / "tools" / "verify_command_registration.py"
    command_verify_code = 0
    command_verify_out = ""
    command_verify_err = ""
    if command_verifier.exists():
        command_verify_code, command_verify_out, command_verify_err = run([sys.executable, str(command_verifier)])
        if command_verify_code != 0:
            failures.append("command registration verifier failed")
    else:
        warnings.append("Command registration verifier not present.")

    print("# DEPLOYMENT PREFLIGHT REPORT")
    print()
    print("## Required files")
    for rel in REQUIRED_FILES:
        print(f"- {'OK' if exists(rel) else 'MISSING'}: {rel}")

    print()
    print("## Expected docs/tools")
    for rel in OPTIONAL_BUT_EXPECTED:
        print(f"- {'OK' if exists(rel) else 'MISSING'}: {rel}")

    print()
    print("## Compile check")
    print(f"- return code: {compile_code}")
    if compile_out.strip():
        print(compile_out.strip())
    if compile_err.strip():
        print(compile_err.strip())

    print()
    print("## Internal import check")
    print(f"- return code: {verify_code}")
    if verify_out.strip():
        print(verify_out.strip())
    if verify_err.strip():
        print(verify_err.strip())

    print()
    print("## Duplicate command check")
    print(f"- return code: {duplicate_verify_code}")
    if duplicate_verify_out.strip():
        print(duplicate_verify_out.strip())
    if duplicate_verify_err.strip():
        print(duplicate_verify_err.strip())

    print()
    print("## Command registration check")
    print(f"- return code: {command_verify_code}")
    if command_verify_out.strip():
        print(command_verify_out.strip())
    if command_verify_err.strip():
        print(command_verify_err.strip())

    print()
    print("## Warnings")
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("- none")

    print()
    print("## Failures")
    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("- none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
