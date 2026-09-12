from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.rotation_dd_component_identity_gap_service import (
    RotationDDComponentIdentityGapService,
)
from tools.audit_rotation_dd_periodic_semantics import _is_dd_role, _resolve_build


DEFAULT_BUILDS = get_data_dir() / "builds.json"


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
            "This tool audits DD component identity only."
        )
        return 4

    report = RotationDDComponentIdentityGapService(database_path).inspect(build)

    print()
    print("============================================")
    print(" DD COMPONENT IDENTITY GAP AUDIT")
    print("============================================")
    print(f"Character: {build.Name or '(unnamed)'}")
    print(f"Build:     {build.BuildName or '(unnamed)'}")
    print(f"Role:      {build.Role or '(unset)'}")

    print()
    print(f"Damage components inspected: {len(report.rows)}")
    if not report.rows:
        print("  - none")
    for row in report.rows:
        canonical = row.canonical_effect_kind.value
        canonical_dot = (
            "unknown" if row.canonical_is_dot is None else str(row.canonical_is_dot).lower()
        )
        text_kind = row.text_evidence.effect_kind or "unresolved"
        text_dot = (
            "unknown"
            if row.text_evidence.is_dot is None
            else str(row.text_evidence.is_dot).lower()
        )
        status = "REVIEW" if row in report.review_candidates else "CANONICAL"
        print(
            f"  - [{status}] {row.skill_name} coeff {row.coefficient_number} "
            f"(rank={row.skill_rank_id}, {row.bar} slot {row.slot})"
        )
        print(
            f"      canonical: kind={canonical}, dot={canonical_dot}, "
            f"damage_type={row.canonical_damage_type or 'unknown'}"
        )
        print(
            f"      text evidence: kind={text_kind}, dot={text_dot}, "
            f"damage_type={row.text_evidence.damage_type or 'unknown'}"
        )
        if row.text_evidence.fragment:
            print(f"      fragment: {row.text_evidence.fragment}")

    print()
    print(f"Review candidates: {len(report.review_candidates)}")
    if report.review_candidates:
        for row in report.review_candidates:
            reasons = []
            if row.needs_damage_identity_review:
                reasons.append("damage identity")
            if row.needs_periodic_identity_review:
                reasons.append("periodic identity")
            print(
                f"  - {row.skill_name} coeff {row.coefficient_number}: "
                + ", ".join(reasons)
            )
    else:
        print("  - none")

    print()
    print(f"Unresolved evidence: {len(report.unresolved)}")
    if report.unresolved:
        for message in report.unresolved:
            print(f"  - {message}")
    else:
        print("  - none")

    print()
    print(
        "Result: REVIEW REPORT ONLY — coefficient text may nominate canonical "
        "classification work, but this tool never writes or promotes mechanics."
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit one saved DD build for coefficient-level damage component identity "
            "gaps using read-only coefficient-local text evidence."
        )
    )
    parser.add_argument(
        "--build",
        required=True,
        help="Saved BuildName, unique character name, or exact 'BuildName | CharacterName' display",
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
    return audit_saved_build(
        database_path=args.database,
        builds_path=args.builds,
        build_name=args.build,
    )


if __name__ == "__main__":
    raise SystemExit(main())
