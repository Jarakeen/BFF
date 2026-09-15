from __future__ import annotations

"""Static architecture audit for BFF / FoundryDock.

This audit reports architecture debt without mutating application data or importing UI
implementations. It complements ``tools/audit_service_catalog.py`` with checks for hidden
runtime authority, package-import mutation, monkey-patch/install fan-out, overlapping plan
persistence, stale RaidPlan identity boundaries, quarantine-boundary imports, legacy engine
duplication, legacy generated-roster compatibility aliases, and runtime path defaults.

The default command is report-only and returns success even when known architecture debt
is present. Use ``--strict`` when the goal is to fail on ERROR findings.
"""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_service_catalog import audit_service_catalog


_RUNTIME_ROOTS = ("engine", "minmax", "models", "services", "ui")
_QUARANTINE_ROOTS = ("legacy", "deprecated", "old_pages", "migration")
_SKIP_PARTS = frozenset({"tests", "test", "__pycache__", *_QUARANTINE_ROOTS})
_LEGACY_GENERATED_ROSTER_NAMES = frozenset(
    {"GeneratedRosterPlan", "GeneratedRosterPlanService", "GeneratedRosterPlanSlot"}
)


@dataclass(frozen=True)
class ArchitectureFinding:
    severity: str
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ArchitectureAuditResult:
    findings: tuple[ArchitectureFinding, ...]

    @property
    def errors(self) -> tuple[ArchitectureFinding, ...]:
        return tuple(row for row in self.findings if row.severity == "ERROR")

    @property
    def warnings(self) -> tuple[ArchitectureFinding, ...]:
        return tuple(row for row in self.findings if row.severity == "WARNING")

    @property
    def infos(self) -> tuple[ArchitectureFinding, ...]:
        return tuple(row for row in self.findings if row.severity == "INFO")


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _runtime_python_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for name in _RUNTIME_ROOTS:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel_parts = path.relative_to(root).parts
            if any(part in _SKIP_PARTS for part in rel_parts):
                continue
            files.append(path)
    return tuple(sorted(files))


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _string_contains_repo_data_path(node: ast.AST) -> bool:
    """Conservatively detect module-level repo-relative ``... / data / ...`` defaults."""
    text = ast.unparse(node) if hasattr(ast, "unparse") else ""
    normalized = text.replace("'", '"')
    return (
        'Path(__file__).resolve().parents[1] / "data"' in normalized
        or 'Path(__file__).resolve().parent.parent / "data"' in normalized
    )


def _duplicate_class_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    names: dict[str, int] = {}
    findings: list[ArchitectureFinding] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        names[node.name] = names.get(node.name, 0) + 1
    for name, count in sorted(names.items()):
        if count > 1:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "duplicate-class-definition",
                    _relative(root, path),
                    f"{name} is defined {count} times in the same runtime module",
                )
            )
    return findings


def _monkey_patch_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    if path.parent.name != "ui" and "ui" not in path.relative_to(root).parts:
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        assigned = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in assigned:
            dotted = _dotted_name(target)
            if not dotted or "." not in dotted:
                continue
            tail = dotted.rsplit(".", 1)[-1]
            if tail.startswith("_") and tail not in {"__init__"}:
                continue
            if tail in {"__init__", "refresh", "load", "save", "build_ui", "_build_ui"} or dotted.count(".") >= 1:
                owner = dotted.split(".")[-2] if dotted.count(".") else ""
                if owner and owner[:1].isupper():
                    targets.append(dotted)
    unique = tuple(dict.fromkeys(targets))
    if not unique:
        return []
    sample = ", ".join(unique[:5])
    suffix = f" (+{len(unique) - 5} more)" if len(unique) > 5 else ""
    return [
        ArchitectureFinding(
            "WARNING",
            "ui-class-monkey-patch",
            _relative(root, path),
            f"replaces {len(unique)} class method(s) at runtime: {sample}{suffix}",
        )
    ]


def _install_fanout_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    findings: list[ArchitectureFinding] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "install":
            continue
        calls: list[str] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            name = _dotted_name(child.func)
            short = name.rsplit(".", 1)[-1]
            if short.startswith("install_") or short.startswith("install") and short != "install":
                calls.append(short)
        unique = tuple(dict.fromkeys(calls))
        if len(unique) >= 5:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "installer-fanout",
                    _relative(root, path),
                    f"install() invokes {len(unique)} other installers; composition order is hidden inside a feature module",
                )
            )
    return findings


def _quarantine_import_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    """Reject normal runtime dependencies on archived/quarantined code roots."""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name == prefix or alias.name.startswith(prefix + ".") for prefix in _QUARANTINE_ROOTS):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if any(module == prefix or module.startswith(prefix + ".") for prefix in _QUARANTINE_ROOTS):
                imports.append(module)
    if not imports:
        return []
    return [
        ArchitectureFinding(
            "ERROR",
            "runtime-quarantine-import",
            _relative(root, path),
            "normal runtime imports quarantine/migration code: " + ", ".join(sorted(set(imports))),
        )
    ]


def _legacy_generated_roster_alias_findings(
    root: Path, path: Path, tree: ast.Module
) -> list[ArchitectureFinding]:
    """Flag live runtime callers that still use pre-draft GeneratedRosterPlan names."""
    imported: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if str(node.module or "") != "services.generated_roster_plan_service":
            continue
        for alias in node.names:
            if alias.name in _LEGACY_GENERATED_ROSTER_NAMES:
                imported.add(alias.name)
    if not imported:
        return []
    return [
        ArchitectureFinding(
            "WARNING",
            "legacy-generated-roster-plan-runtime-alias",
            _relative(root, path),
            "live runtime still imports compatibility GeneratedRosterPlan API: "
            + ", ".join(sorted(imported)),
        )
    ]


def _old_pages_import_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    """Compatibility wrapper for older focused tests/callers."""
    return [
        finding
        for finding in _quarantine_import_findings(root, path, tree)
        if "old_pages" in finding.message
    ]


def _runtime_path_findings(root: Path, path: Path, tree: ast.Module) -> list[ArchitectureFinding]:
    rel = _relative(root, path)
    if rel in {"engine/config.py", "services/paths.py"}:
        return []
    for node in tree.body:
        candidate: ast.AST | None = None
        if isinstance(node, ast.Assign):
            candidate = node.value
        elif isinstance(node, ast.AnnAssign):
            candidate = node.value
        if candidate is not None and _string_contains_repo_data_path(candidate):
            return [
                ArchitectureFinding(
                    "WARNING",
                    "runtime-local-data-path",
                    rel,
                    "defines a repo-relative runtime data default instead of using engine.config/services.paths or an explicit caller path",
                )
            ]
    return []


def _repo_contract_findings(root: Path) -> list[ArchitectureFinding]:
    findings: list[ArchitectureFinding] = []

    services_init = root / "services" / "__init__.py"
    if services_init.is_file():
        text = services_init.read_text(encoding="utf-8")
        if "BuildService.load = load" in text or "BuildService.save = save" in text:
            findings.append(
                ArchitectureFinding(
                    "ERROR",
                    "build-persistence-authority-bypass",
                    "services/__init__.py",
                    "package import replaces BuildService canonical bridge methods with direct builds.json persistence",
                )
            )
        if "_install_build_persistence()" in text:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "package-import-side-effect",
                    "services/__init__.py",
                    "importing services executes persistence installation/mutation",
                )
            )

    raid_model = root / "models" / "raid_plan.py"
    raid_repo = root / "services" / "raid_plan_repository.py"
    if raid_model.is_file():
        text = raid_model.read_text(encoding="utf-8")
        if raid_repo.is_file() and "deliberately persistence-neutral" in text:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "stale-raid-plan-persistence-doc",
                    "models/raid_plan.py",
                    "RaidPlan documentation says persistence-neutral although RaidPlanRepository is live",
                )
            )
        if "selected_build_name:" in text and "selected_build_id:" not in text:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "raid-plan-name-based-build-identity",
                    "models/raid_plan.py",
                    "RaidPlan persists selected build by display name without stable selected_build_id",
                )
            )

    generated = root / "services" / "generated_roster_plan_service.py"
    if generated.is_file() and raid_repo.is_file():
        findings.append(
            ArchitectureFinding(
                "WARNING",
                "overlapping-plan-persistence",
                "services/generated_roster_plan_service.py",
                "GeneratedRosterDraft still uses legacy generated_roster_plan SQLite compatibility storage alongside RaidPlan; migration/ownership boundary remains open",
            )
        )

    comp_catalog = root / "services" / "comp_maker_catalog_descriptors.py"
    if comp_catalog.is_file():
        text = comp_catalog.read_text(encoding="utf-8")
        foreign_families = (
            "RAID_PLAN_SERVICE_DESCRIPTORS",
            "EXTREME_SERVICE_DESCRIPTORS",
            "ROTATION_SERVICE_DESCRIPTORS",
            "TEAM_WORKFLOW_SERVICE_DESCRIPTORS",
        )
        if sum(name in text for name in foreign_families) >= 3:
            findings.append(
                ArchitectureFinding(
                    "WARNING",
                    "catalog-family-transitive-aggregation",
                    "services/comp_maker_catalog_descriptors.py",
                    "Comp Maker descriptor family re-exports multiple unrelated domain families, obscuring catalog ownership",
                )
            )

    return findings


def audit_system_architecture(*, root: Path) -> ArchitectureAuditResult:
    root = root.resolve()
    findings: list[ArchitectureFinding] = []

    catalog = audit_service_catalog(root=root)
    for item in catalog.findings:
        findings.append(
            ArchitectureFinding(
                item.severity,
                f"service-catalog:{item.code}",
                "services/service_catalog.py",
                item.message,
            )
        )

    for path in _runtime_python_files(root):
        tree = _parse(path)
        if tree is None:
            continue
        findings.extend(_duplicate_class_findings(root, path, tree))
        findings.extend(_monkey_patch_findings(root, path, tree))
        findings.extend(_install_fanout_findings(root, path, tree))
        findings.extend(_quarantine_import_findings(root, path, tree))
        findings.extend(_legacy_generated_roster_alias_findings(root, path, tree))
        findings.extend(_runtime_path_findings(root, path, tree))

    findings.extend(_repo_contract_findings(root))

    severity_rank = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    ordered = tuple(
        sorted(
            findings,
            key=lambda row: (
                severity_rank.get(row.severity, 9),
                row.code,
                row.path.casefold(),
                row.message.casefold(),
            ),
        )
    )
    return ArchitectureAuditResult(ordered)


def _print_result(result: ArchitectureAuditResult) -> None:
    print("BFF SYSTEM ARCHITECTURE AUDIT")
    print("=" * 72)
    print(f"Errors:   {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Info:     {len(result.infos)}")
    print()
    if not result.findings:
        print("No findings.")
        return
    for finding in result.findings:
        print(
            f"{finding.severity:<7} {finding.code:<42} "
            f"{finding.path}\n        {finding.message}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when ERROR findings are present",
    )
    args = parser.parse_args()
    result = audit_system_architecture(root=args.root)
    _print_result(result)
    return 1 if args.strict and result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
