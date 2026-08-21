from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def get_functions(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def get_dependencies(function):
    dependencies = set()

    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id.startswith("calculate_"):
                    dependencies.add(node.func.id)

            elif isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith("calculate_"):
                    dependencies.add(node.func.attr)

    return sorted(dependencies)


def main():
    print("=" * 100)
    print("MINMAX FORMULA DEPENDENCY MAP")
    print("=" * 100)

    for path in sorted(ROOT.glob("*.py")):
        if path.name.startswith("__"):
            continue

        if path.name in {
            "equation_inventory_audit.py",
            "dependency_audit.py",
            "inspect_dependencies.py",
        }:
            continue

        functions = get_functions(path)

        if not functions:
            continue

        print()
        print("=" * 100)
        print(path.name)
        print("=" * 100)

        for function in sorted(functions, key=lambda f: f.name):
            dependencies = get_dependencies(function)

            print()
            print(function.name)

            if dependencies:
                for dependency in dependencies:
                    print(f"    -> {dependency}")
            else:
                print("    -> [raw inputs / no formula calls]")


if __name__ == "__main__":
    main()