from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_difficulty import normalize_encounter_difficulty
from services.encounter_repository import EncounterRepository
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.saved_build_capability_service import SavedBuildCapabilityService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a real saved-build roster against one Phase 10 encounter."
    )
    parser.add_argument("encounter_id", help="Exact canonical encounter id.")
    parser.add_argument(
        "--difficulty",
        default="veteran",
        help="Encounter difficulty: normal, veteran/vet, hardmode/hm. Default: veteran.",
    )
    parser.add_argument(
        "--build",
        action="append",
        default=[],
        help="Exact saved build name or character name. Repeat to select multiple roster members.",
    )
    parser.add_argument(
        "--builds",
        type=Path,
        default=get_data_dir() / "builds.json",
        help="Saved builds compatibility mirror.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="ESO reference database.",
    )
    return parser


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _select_audits(audits, requested: list[str]):
    if not requested:
        return tuple(audits)

    selected = []
    missing = []
    for raw in requested:
        target = _clean(raw).casefold()
        matches = [
            audit
            for audit in audits
            if _clean(audit.build_name).casefold() == target
            or _clean(audit.character_name).casefold() == target
        ]
        if len(matches) != 1:
            missing.append((raw, len(matches)))
            continue
        selected.append(matches[0])

    if missing:
        details = ", ".join(f"{name!r} matched {count}" for name, count in missing)
        raise ValueError(f"Each --build must match exactly one saved build: {details}")
    return tuple(selected)


def _identity(audit) -> str:
    return audit.character_id or audit.character_name or audit.build_name


def main() -> int:
    args = _parser().parse_args()
    try:
        difficulty = normalize_encounter_difficulty(args.difficulty)
    except ValueError as exc:
        print(exc)
        return 2

    encounter_service = EncounterService(
        EncounterRepository.from_data_root(ROOT / "data")
    )
    if args.encounter_id not in encounter_service.encounter_ids():
        print(f"Unknown exact encounter id: {args.encounter_id}")
        return 2

    capability_service = SavedBuildCapabilityService(
        BuildService(args.builds),
        args.database,
    )
    all_audits = capability_service.audit_roster()
    try:
        audits = _select_audits(all_audits, args.build)
    except ValueError as exc:
        print(exc)
        return 2

    if not audits:
        print("No saved builds selected.")
        return 2

    identities = [_identity(audit) for audit in audits]
    duplicates = sorted(
        identity for identity, count in Counter(identities).items()
        if identity and count > 1
    )
    if duplicates:
        print("Ambiguous roster: more than one selected build resolves to the same character.")
        for identity in duplicates:
            print(f"  {identity}")
            for audit in audits:
                if _identity(audit) == identity:
                    print(f"    - {audit.character_name} | {audit.build_name}")
        print("Select one authoritative --build per character for this encounter.")
        return 2

    evaluator = EncounterRosterEvaluator(
        encounter_service,
        SavedBuildEncounterCapabilityAdapter(()),
    )
    report = evaluator.evaluate_saved_build_audits(
        args.encounter_id,
        audits,
        difficulty=difficulty,
    )

    print("PHASE 10 REAL SAVED-ROSTER ENCOUNTER EVALUATION")
    print(f"Encounter: {args.encounter_id}")
    print(f"Difficulty: {report.difficulty.value}")
    print(f"Builds: {args.builds}")
    print(f"Database: {args.database}")
    print(f"Selected roster members: {len(audits)}")
    for audit in audits:
        state = "resolved" if audit.resolved else f"unresolved={len(audit.unresolved)}"
        capability_gaps = len(audit.capability_resolution_gaps)
        print(
            f"  {audit.character_name or '(unnamed)'} | {audit.build_name or '(unnamed build)'} "
            f"| id={_identity(audit) or '(none)'} | effects={len(audit.resolved_effects)} "
            f"| {state} | capability_gaps={capability_gaps}"
        )
        if audit.unresolved:
            for message in audit.unresolved:
                scope = (
                    "CAPABILITY-GAP"
                    if message in audit.capability_resolution_gaps
                    else "STAT/STATE-GAP"
                )
                print(f"    {scope}: {message}")
        if audit.boundaries:
            for message in audit.boundaries:
                print(f"    BOUNDARY: {message}")

    print()
    print("EXECUTION READINESS")
    if not report.execution_evaluation.results:
        print("  (no structured encounter requirements)")
    for row in report.execution_evaluation.results:
        method = row.handling_method or "unresolved"
        interaction = f" / {row.interaction}" if row.interaction else ""
        print(
            f"  {row.classification.value.upper():11} {row.mechanic_name} "
            f"[{row.requirement_type}] -> {method}{interaction}"
        )
        print(f"    {row.explanation}")

    print()
    print("PROVIDER COVERAGE")
    if not report.provider_results:
        print("  (no build-provider requirements in current structured encounter data)")
    for row in report.provider_results:
        print(
            f"  {row.classification.value.upper():11} {row.mechanic_name} "
            f"[{row.requirement_type}] providers={len(row.providers)} unknown={len(row.unknown_members)}"
        )
        print(f"    {row.explanation}")

    print()
    print("SUMMARY")
    print(f"Fully evaluable: {report.is_fully_evaluable}")
    print(f"Capability-ready: {report.is_fully_covered}")
    print()
    print("BOUNDARY")
    print("Capability-ready does not claim players will execute movement, positioning, bash, or encounter interactions correctly.")
    print("Provider assignment and optimization remain later phases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
