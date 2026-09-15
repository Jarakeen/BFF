from __future__ import annotations

"""Report static inbound-import evidence for retirement candidates.

This tool is deliberately conservative. It does not delete, move, or declare code dead.
It answers a narrower question: which Python files import a candidate module, and from
which part of the repository?

Dynamic imports, installer registration, string references, subprocess entry points,
Qt signal wiring, and persisted-data dependencies can escape static import analysis.
A STATIC_ORPHAN_CANDIDATE result is therefore a prompt for deeper review, never proof
that deletion is safe.
"""

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_ROOTS = frozenset({"engine", "minmax", "models", "services", "ui"})
_QUARANTINE_ROOTS = frozenset({"legacy", "deprecated", "migration", "old_pages"})
_SKIP_DIRS = frozenset({".git", ".venv", "venv", "__pycache__", ".pytest_cache"})


@dataclass(frozen=True)
class Consumer:
    path: str
    kind: str


@dataclass(frozen=True)
class RetirementEvidence:
    candidate_path: str
    module: str
    consumers: tuple[Consumer, ...]

    @property
    def runtime_consumers(self) -> tuple[Consumer, ...]:
        return tuple(row for row in self.consumers if row.kind == "runtime")

    @property
    def tool_consumers(self) -> tuple[Consumer, ...]:
        return tuple(row for row in self.consumers if row.kind == "tool")

    @property
    def test_consumers(self) -> tuple[Consumer, ...]:
        return tuple(row for row in self.consumers if row.kind == "test")

    @property
    def quarantine_consumers(self) -> tuple[Consumer, ...]:
        return tuple(row for row in self.consumers if row.kind == "quarantine")

    @property
    def status(self) -> str:
        if self.runtime_consumers:
            return "LIVE_RUNTIME"
        if self.tool_consumers:
            return "TOOLING_ONLY"
        if self.test_consumers:
            return "TEST_ONLY"
        if self.quarantine_consumers:
            return "QUARANTINE_REFERENCED"
        return "STATIC_ORPHAN_CANDIDATE"


def _python_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        files.append(path)
    return tuple(sorted(files))


def _module_for_path(root: Path, path: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _consumer_kind(root: Path, path: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    parts = rel.parts
    if any(part in {"tests", "test"} for part in parts) or path.name.startswith("test_"):
        return "test"
    if parts and parts[0] == "tools":
        return "tool"
    if parts and parts[0] in _QUARANTINE_ROOTS:
        return "quarantine"
    if rel.as_posix() == "app.py" or (parts and parts[0] in _RUNTIME_ROOTS):
        return "runtime"
    return "other"


def _resolve_from_module(root: Path, importer: Path, node: ast.ImportFrom) -> str:
    module = str(node.module or "")
    if not node.level:
        return module

    importer_module = _module_for_path(root, importer)
    package_parts = importer_module.split(".")[:-1]
    trim = max(0, node.level - 1)
    if trim:
        package_parts = package_parts[:-trim] if trim <= len(package_parts) else []
    if module:
        package_parts.extend(module.split("."))
    return ".".join(part for part in package_parts if part)


def _imports_module(root: Path, path: Path, target_module: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == target_module or name.startswith(target_module + "."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_from_module(root, path, node)
            if module == target_module or module.startswith(target_module + "."):
                return True
    return False


def inspect_candidate(root: Path, candidate: Path) -> RetirementEvidence:
    root = root.resolve()
    path = candidate if candidate.is_absolute() else root / candidate
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix != ".py":
        raise ValueError(f"retirement import audit currently supports Python files only: {path}")

    module = _module_for_path(root, path)
    consumers: list[Consumer] = []
    for other in _python_files(root):
        if other.resolve() == path:
            continue
        if _imports_module(root, other, module):
            consumers.append(
                Consumer(
                    path=other.relative_to(root).as_posix(),
                    kind=_consumer_kind(root, other),
                )
            )
    consumers.sort(key=lambda row: (row.kind, row.path.casefold()))
    return RetirementEvidence(
        candidate_path=path.relative_to(root).as_posix(),
        module=module,
        consumers=tuple(consumers),
    )


def _print_evidence(evidence: RetirementEvidence) -> None:
    print(evidence.candidate_path)
    print(f"  module={evidence.module}")
    print(f"  status={evidence.status}")
    if not evidence.consumers:
        print("  static_import_consumers=0")
    else:
        print(f"  static_import_consumers={len(evidence.consumers)}")
        for row in evidence.consumers:
            print(f"    {row.kind:<10} {row.path}")
    print(
        "  caution=static imports only; review dynamic installers, registrations, "
        "string references, entry points, and persisted-data dependencies before moving"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="candidate Python file paths")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    print("BFF CODE RETIREMENT INVENTORY")
    print("=" * 72)
    for index, candidate in enumerate(args.paths):
        if index:
            print()
        try:
            evidence = inspect_candidate(args.root, candidate)
        except (FileNotFoundError, ValueError) as exc:
            print(f"{candidate}\n  status=ERROR\n  error={exc}")
            continue
        _print_evidence(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
