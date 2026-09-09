from __future__ import annotations

"""Audit the canonical BFF service catalog without importing service implementations."""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.service_catalog import (
    SERVICE_DESCRIPTORS,
    ServiceAuthority,
    ServiceDescriptor,
    ServiceLifecycle,
)

_NON_SERVICE_MODULES = frozenset(
    {
        "services.service_catalog",
        # Verified historical compatibility utilities. Their only application
        # consumers live under old_pages/, so cataloging them as current services
        # would misrepresent the runtime architecture merely to silence coverage.
        "services.ai_service",
        "services.json_service",
        "services.validation_service",
    }
)


@dataclass(frozen=True)
class CatalogFinding:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class ServiceCatalogAuditResult:
    findings: tuple[CatalogFinding, ...]

    @property
    def errors(self) -> tuple[CatalogFinding, ...]:
        return tuple(row for row in self.findings if row.severity == "ERROR")

    @property
    def warnings(self) -> tuple[CatalogFinding, ...]:
        return tuple(row for row in self.findings if row.severity == "WARNING")

    @property
    def ok(self) -> bool:
        return not self.errors


def _module_file(root: Path, implementation_path: str) -> Path:
    return root.joinpath(*implementation_path.split(".")).with_suffix(".py")


def _service_modules(root: Path) -> tuple[str, ...]:
    services_dir = root / "services"
    if not services_dir.exists():
        return ()
    modules: list[str] = []
    for path in services_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        if path.name.endswith(("_model.py", "_models.py", "_types.py", "_protocol.py")):
            continue
        module = f"services.{path.stem}"
        if module in _NON_SERVICE_MODULES:
            continue
        modules.append(module)
    return tuple(sorted(modules))


def _looks_like_service_module(path: Path) -> bool:
    """Conservatively classify top-level services modules for coverage warnings."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False

    if path.stem.endswith(("_service", "_repository", "_pipeline", "_optimizer")):
        return True

    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name.casefold()
            if name.endswith(("service", "repository")):
                return True
            if name.startswith(("run_", "optimize_", "evaluate_", "generate_", "project_")):
                return True
    return False


def _dependency_cycle(
    descriptors: tuple[ServiceDescriptor, ...],
) -> tuple[str, ...] | None:
    graph = {row.service_id: tuple(row.dependencies) for row in descriptors}
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(service_id: str) -> tuple[str, ...] | None:
        if service_id in visiting:
            start = stack.index(service_id)
            return tuple((*stack[start:], service_id))
        if service_id in visited:
            return None
        visiting.add(service_id)
        stack.append(service_id)
        for dependency in graph.get(service_id, ()):
            if dependency not in graph:
                continue
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        stack.pop()
        visiting.remove(service_id)
        visited.add(service_id)
        return None

    for service_id in graph:
        cycle = visit(service_id)
        if cycle is not None:
            return cycle
    return None


def audit_service_catalog(
    *,
    root: Path,
    descriptors: Iterable[ServiceDescriptor] = SERVICE_DESCRIPTORS,
) -> ServiceCatalogAuditResult:
    rows = tuple(descriptors)
    findings: list[CatalogFinding] = []

    by_id: dict[str, list[ServiceDescriptor]] = {}
    for row in rows:
        by_id.setdefault(row.service_id, []).append(row)

    for service_id, matches in sorted(by_id.items()):
        if len(matches) > 1:
            findings.append(
                CatalogFinding(
                    "ERROR",
                    "duplicate-service-id",
                    f"{service_id} is registered {len(matches)} times",
                )
            )

    registered_ids = set(by_id)
    registered_modules = {row.implementation_path for row in rows}
    for row in rows:
        implementation_file = _module_file(root, row.implementation_path)
        if row.lifecycle is not ServiceLifecycle.PLANNED and not implementation_file.is_file():
            findings.append(
                CatalogFinding(
                    "ERROR",
                    "broken-implementation-path",
                    f"{row.service_id}: missing {implementation_file.relative_to(root).as_posix()}",
                )
            )
        for dependency in row.dependencies:
            if dependency not in registered_ids:
                findings.append(
                    CatalogFinding(
                        "ERROR",
                        "missing-dependency",
                        f"{row.service_id}: dependency {dependency} is not registered",
                    )
                )

        if row.authority is ServiceAuthority.DEPRECATED and not row.superseded_by:
            findings.append(
                CatalogFinding(
                    "WARNING",
                    "deprecated-without-successor",
                    f"{row.service_id} is deprecated without superseded_by",
                )
            )
        if row.superseded_by and row.superseded_by not in registered_ids:
            findings.append(
                CatalogFinding(
                    "ERROR",
                    "missing-superseding-service",
                    f"{row.service_id}: superseded_by {row.superseded_by} is not registered",
                )
            )
        for superseded in row.supersedes:
            if superseded not in registered_ids:
                findings.append(
                    CatalogFinding(
                        "ERROR",
                        "missing-superseded-service",
                        f"{row.service_id}: supersedes {superseded}, which is not registered",
                    )
                )

    for responsibility in sorted(
        {item for row in rows for item in row.responsibilities}
    ):
        canonical = tuple(
            row
            for row in rows
            if responsibility in row.responsibilities
            and row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        if len(canonical) > 1:
            findings.append(
                CatalogFinding(
                    "ERROR",
                    "duplicate-canonical-responsibility",
                    f"{responsibility}: {', '.join(row.service_id for row in canonical)}",
                )
            )

    cycle = _dependency_cycle(rows)
    if cycle is not None:
        findings.append(
            CatalogFinding(
                "ERROR",
                "circular-dependency",
                " -> ".join(cycle),
            )
        )

    services_dir = root / "services"
    for module in _service_modules(root):
        if module in registered_modules:
            continue
        path = services_dir / f"{module.removeprefix('services.')}.py"
        if _looks_like_service_module(path):
            findings.append(
                CatalogFinding(
                    "WARNING",
                    "unregistered-service-module",
                    path.relative_to(root).as_posix(),
                )
            )

    for row in rows:
        if row.authority is ServiceAuthority.DEPRECATED:
            consumers = tuple(
                candidate.service_id
                for candidate in rows
                if row.service_id in candidate.dependencies
                and candidate.authority is ServiceAuthority.CANONICAL
            )
            if consumers:
                findings.append(
                    CatalogFinding(
                        "WARNING",
                        "canonical-depends-on-deprecated",
                        f"{', '.join(consumers)} depend on deprecated {row.service_id}",
                    )
                )

    return ServiceCatalogAuditResult(tuple(findings))


def _print_result(result: ServiceCatalogAuditResult) -> None:
    print("BFF SERVICE CATALOG AUDIT")
    print()
    print(f"Errors:   {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    if not result.findings:
        print("No findings.")
        return
    print()
    for finding in result.findings:
        print(f"{finding.severity:<7} {finding.code}: {finding.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the BFF service catalog.")
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root (defaults to the parent of tools/).",
    )
    args = parser.parse_args()
    result = audit_service_catalog(root=args.root.resolve())
    _print_result(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
