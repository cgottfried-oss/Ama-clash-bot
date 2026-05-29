from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = ROOT / "clash_mmo" / "commands"
REGISTRY = COMMANDS_DIR / "__init__.py"


def discover_command_modules():
    modules = {}
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        slash_count = 0
        register_functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("register_"):
                    register_functions.append(node.name)
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute):
                        if deco.func.attr == "command":
                            slash_count += 1
        if slash_count or register_functions:
            modules[path.stem] = {
                "file": path.relative_to(ROOT).as_posix(),
                "slash_count": slash_count,
                "register_functions": register_functions,
            }
    return modules


def parse_registry():
    text = REGISTRY.read_text(encoding="utf-8")
    imported = set()
    called = set()
    tree = ast.parse(text)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("clash_mmo.commands."):
            module = node.module.rsplit(".", 1)[-1]
            imported.add(module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id.startswith("register_"):
                called.add(func.id)

    return imported, called


def main() -> int:
    modules = discover_command_modules()
    imported_modules, called_registers = parse_registry()

    failures = []
    warnings = []

    for module_name, data in modules.items():
        if data["slash_count"] > 0 and module_name not in imported_modules:
            warnings.append(f"{data['file']} defines slash commands but module is not imported in commands/__init__.py")

        registers = data["register_functions"]
        if data["slash_count"] > 0 and not registers:
            warnings.append(f"{data['file']} defines slash commands but no register_* function was detected")

        for register in registers:
            if module_name in imported_modules and register not in called_registers:
                warnings.append(f"{data['file']} exports {register} but commands/__init__.py does not call it")

    print("# COMMAND REGISTRATION VERIFY")
    print()
    print(f"Command modules scanned: {len(modules)}")
    print(f"Registry imports detected: {len(imported_modules)}")
    print(f"Registry register calls detected: {len(called_registers)}")
    print()

    if warnings:
        print("## Warnings")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("## Warnings")
        print("- none")

    print()
    if failures:
        print("## Failures")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("## Failures")
    print("- none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
