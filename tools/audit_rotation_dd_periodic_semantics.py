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


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _is_dd_role(value: object) -> bool:
    normalized = " ".join(str(value or "").strip().casefold().split())
    return normalized in {"dd", "dps", "damage", "damage dealer"}


def _display_selector(build) -> str:
    build_name = str(getattr(build, "BuildName", "") or "").strip()
    character = str(getattr(build, "Name", "") or "").strip()
    return f"{build_name} | {character}" if character else build_name


def _resolve_build(builds, requested: str):
    key = str(requested or "").strip().casefold()
    if not key:
        raise ValueError("--build is required")

    def text(build, attr: str) -> str:
        return str(getattr(build, attr, "") or "").strip()

    build_name_matches = [
        build for build in builds if text(build, "BuildName").casefold() == key
    ]
    if len(build_name_matches) == 1:
        return build_name_matches[0]
    if len(build_name_matches) > 1:
        raise ValueError(f"Saved build name is ambiguous: {requested!r}")

    character_matches = [
        build for build in builds if text(build, "Name").casefold() == key
    ]
    if len(character_matches) == 1:
        return character_matches[0]
    if len(character_matches) > 1:
        names = ", ".join(
            sorted(text(build, "BuildName") or "(unnamed)" for build in character_matches)
        )
        raise ValueError(
            f"Character name {requested!r} matches multiple saved builds: {names}. "
            "Use the exact BuildName."
        )

    display_matches = [
        build for build in builds if _display_selector(build).casefold() == key
    ]
    if len(display_matches) == 1:
        return display_matches[0]

    raise ValueError(f"Saved build not found: {requested!r}")


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
        print(
            "    "
            f'python tools/audit_rotation_dd_periodic_semantics.py --build "{build_name}"'
        )
    return 0


def _format_partial_review(item) -> tuple[str, ...]:
    review = getattr(item, "partial_review", None)
    if review is None:
        return ()

    known: list[str] = []
    if review.duration_seconds is not None:
        known.append(f"duration={review.duration_seconds:g}s")
    if review.reviewed_interval_seconds is not None:
        known.append(f"interval={review.reviewed_interval_seconds:g}s")
    if review.first_tick_offset_seconds is not None:
        known.append(f"first_tick={review.first_tick_offset_seconds:g}s")
    if review.refresh_boundary is not None:
        known.append(f"refresh={review.refresh_boundary}")
    if review.magnitude_policy is not None:
        known.append(f"magnitude={review.magnitude_policy}")
    if review.successive_hit_multiplier is not None:
        known.append(f"successive_hit_multiplier={review.successive_hit_multiplier:g}")

    lines: list[str] = []
    if known:
        lines.append("      known: " + ", ".join(known))
    if review.unresolved_executable_fields:
        lines.append(
            "      still needed: " + ", ".join(review.unresolved_executable_fields)
        )
    if review.evidence:
        lines.append("      review evidence: " + " | ".join(review.evidence))
    return tuple(lines)


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
        build = _resolve_build(saved_members, build_name)
    except ValueError as exc:
        print(exc)
        return 3

    if not _is_dd_role(getattr(build, "Role", "")):
        role = str(getattr(build, "Role", "") or "(unset)").strip() or "(unset)"
        print(
            f"Saved build {build.BuildName!r} has role {role!r}. "
            "This tool audits DD periodic damage runtime semantics only."
        )
        print("Use --list-dd to show saved DD builds that are valid inputs.")
        return 4

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
            for line in _format_partial_review(item):
                print(line)
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
    selection.add_argument(
        "--build",
        help="Saved BuildName, unique character name, or exact 'BuildName | CharacterName' display",
    )
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
