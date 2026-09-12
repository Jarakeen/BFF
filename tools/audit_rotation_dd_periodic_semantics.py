from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.rotation_dd_periodic_runtime_semantics_gap_audit_service import (
    RotationDDPeriodicRuntimeSemanticsGapAuditService,
)
from tools.audit_phase12_saved_build_candidates import _find_build


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _is_dd_role(value: object) -> bool:
    normalized = " ".join(str(value or "").strip().casefold().split())
    return normalized in {"dd", "dps", "damage", "damage dealer"}


def list_dd_builds(*, builds_path: Path) -> int:
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    builds = tuple(
        build
        for build in BuildService(builds_path).load().Members
        if _is_dd_role(getattr(build, "Role", ""))
    )
    print("Saved DD builds:")
    if not builds:
        print("  - none")
        return 0

    for build in builds:
        character = str(getattr(build, "Name", "") or "").strip() or "(unnamed)"
        build_name = str(getattr(build, "BuildName", "") or "").strip() or "(unnamed)"
        print(f"  - {build_name} | {character}")
    return 0


def audit_saved_build(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    saved_members = BuildService(builds_path).load().Members
    try:
        build = _find_build(saved_members, build_name)
    except ValueError as exc:
        print(exc)
        return 3

    audit = RotationDDPeriodicRuntimeSemanticsGapAuditService(
        database_path
    ).audit_build(build)

    print()
    print("============================================")
    print(" DD PERIODIC RUNTIME SEMANTICS GAP AUDIT")
    print("============================================")
    print(f"Character: {build.Name or '(unnamed)'}")
    print(f"Build:     {build.BuildName or '(unnamed)'}")
    print(f"Role:      {build.Role or '(unset)'}")

    print()
    print(f"Reviewed periodic components: {len(audit.reviewed)}")
    if audit.reviewed:
        for item in audit.reviewed:
            print(
                "  - "
                f"{item.skill_entity_id} coeff {item.coefficient_number}: "
                f"first_tick={item.first_tick_offset_seconds:g}s, "
                f"refresh={item.refresh_boundary.value}, "
                f"magnitude={item.magnitude_policy.value if item.magnitude_policy is not None else 'unresolved'}"
            )
            print(f"      source: {item.source}")
    else:
        print("  - none")

    print()
    print(f"Missing reviewed semantics: {len(audit.missing)}")
    if audit.missing:
        for item in audit.missing:
            print(
                "  - "
                f"{item.skill_entity_id} coeff {item.coefficient_number} "
                f"(skill_rank_id={item.skill_rank_id})"
            )
            if item.classification_source:
                print(f"      component classification: {item.classification_source}")
    else:
        print("  - none")

    print()
    print(f"Unresolved component evidence: {len(audit.unresolved)}")
    if audit.unresolved:
        for message in audit.unresolved:
            print(f"  - {message}")
    else:
        print("  - none")

    print()
    if audit.complete:
        print("Result: COMPLETE — this build has no DD periodic runtime-semantics gaps.")
    else:
        print(
            "Result: RESEARCH REQUIRED — review only the missing/unresolved components above; "
            "do not infer runtime semantics from skill names or tooltip prose."
        )

    # Research incompleteness is an audit result, not a tool execution failure.
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit one saved DD build for periodic damage components that still lack "
            "reviewed Rotation Builder runtime semantics."
        )
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--build", help="Exact saved BuildName")
    selection.add_argument(
        "--list-dd",
        action="store_true",
        help="List saved DD build names and exit",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE),
        help="Canonical ESO SQLite database path",
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=DEFAULT_BUILDS,
        help="Saved builds JSON path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.list_dd:
        return list_dd_builds(builds_path=args.builds)
    return audit_saved_build(
        database_path=args.database,
        builds_path=args.builds,
        build_name=args.build,
    )


if __name__ == "__main__":
    raise SystemExit(main())
