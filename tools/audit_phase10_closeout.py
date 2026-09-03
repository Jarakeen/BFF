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
from services.encounter_execution_audit import audit_encounter_execution
from services.encounter_repository import EncounterRepository
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.phase10_closeout_audit import (
    audit_phase10_roster_inventory,
    is_real_saved_build,
    saved_build_identity,
)
from services.saved_build_capability_service import SavedBuildCapabilityService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Phase 10 closeout and real-roster exit readiness.")
    parser.add_argument("--encounter", default="oaxiltso", help="Exact real encounter id used for the exit evaluation.")
    parser.add_argument("--difficulty", default="veteran", help="normal, veteran/vet, or hardmode/hm.")
    parser.add_argument(
        "--build",
        action="append",
        default=[],
        help="Exact saved build name or character name. Repeat for a deliberate multi-member roster.",
    )
    parser.add_argument("--builds", type=Path, default=get_data_dir() / "builds.json")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    return parser


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _select(audits, requested: list[str]):
    if not requested:
        return ()
    selected = []
    errors = []
    for raw in requested:
        target = _clean(raw).casefold()
        matches = [
            audit
            for audit in audits
            if _clean(audit.build_name).casefold() == target
            or _clean(audit.character_name).casefold() == target
        ]
        if len(matches) != 1:
            errors.append(f"{raw!r} matched {len(matches)} saved builds")
            continue
        selected.append(matches[0])
    if errors:
        raise ValueError("; ".join(errors))
    return tuple(selected)


def _auto_select(inventory):
    if inventory.has_ambiguous_member_builds:
        return ()
    return inventory.real_builds


def _print_detected_real_builds(inventory) -> None:
    if not inventory.real_builds:
        print("  Detected real builds:           (none)")
        return
    print("  Detected real builds:")
    for audit in inventory.real_builds:
        character = audit.character_name or "(unnamed character)"
        build = audit.build_name or "(unnamed build)"
        print(f"    - {character} | {build}")


def _print_excluded_builds(inventory) -> None:
    if not inventory.template_or_blank_builds:
        return
    print("  Ignored blank/template builds:")
    for audit in inventory.template_or_blank_builds:
        character = audit.character_name or "(blank character)"
        build = audit.build_name or "(blank build)"
        print(f"    - character={character!r} | build={build!r}")


def _encounter_service(database: Path) -> EncounterService:
    return EncounterService(
        EncounterRepository(
            ROOT / "data" / "eso_info" / "bosses",
            ROOT / "data" / "encounter_evidence",
            database_path=database,
        )
    )


def _print_execution_rows(report) -> None:
    print("  Execution detail:")
    if not report.execution_evaluation.results:
        print("    (none)")
        return
    for row in report.execution_evaluation.results:
        method = row.handling_method or "unresolved"
        interaction = f" / {row.interaction}" if row.interaction else ""
        print(
            f"    {row.classification.value.upper():11} "
            f"{row.mechanic_name} [{row.requirement_type}] -> {method}{interaction}"
        )
        print(f"      {row.explanation}")


def main() -> int:
    args = _parser().parse_args()
    try:
        difficulty = normalize_encounter_difficulty(args.difficulty)
    except ValueError as exc:
        print(exc)
        return 2

    encounter_service = _encounter_service(args.database)
    if args.encounter not in encounter_service.encounter_ids():
        print(f"Unknown exact encounter id: {args.encounter}")
        return 2

    capability_service = SavedBuildCapabilityService(BuildService(args.builds), args.database)
    audits = capability_service.audit_roster()
    inventory = audit_phase10_roster_inventory(audits)
    execution_audit = audit_encounter_execution(encounter_service)

    print("PHASE 10 CLOSEOUT AUDIT")
    print(f"Builds: {args.builds}")
    print(f"Database: {args.database}")
    print()
    print("EXECUTION CORPUS")
    print(f"  Encounters with requirements: {execution_audit.encounters_with_requirements}")
    print(f"  Fully evaluable encounters:   {execution_audit.fully_evaluable_encounters}")
    print(f"  Fully ready encounters:       {execution_audit.fully_ready_encounters}")
    print(f"  Covered requirements:         {execution_audit.covered_requirement_count}")
    print(f"  Unknown requirements:         {execution_audit.unknown_requirement_count}")
    print(f"  Conflicting requirements:     {execution_audit.conflict_requirement_count}")

    print()
    print("REAL SAVED-ROSTER INVENTORY")
    print(f"  Real saved builds:             {inventory.real_build_count}")
    print(f"  Unique real characters:        {inventory.unique_member_count}")
    print(f"  Blank/template builds ignored: {len(inventory.template_or_blank_builds)}")
    _print_detected_real_builds(inventory)
    _print_excluded_builds(inventory)
    if inventory.duplicate_member_ids:
        print("  Characters with multiple candidate builds:")
        for identity in inventory.duplicate_member_ids:
            print(f"    - {identity}")
    if inventory.unique_member_count < 2:
        print("  NOTE: no valid second --build value exists yet; save another real character/build first.")

    try:
        selected = _select(audits, args.build) if args.build else _auto_select(inventory)
    except ValueError as exc:
        print()
        print(f"ROSTER SELECTION ERROR: {exc}")
        print("Valid real saved-build selections currently detected:")
        if inventory.real_builds:
            for audit in inventory.real_builds:
                print(f"  --build {audit.build_name!r}")
        else:
            print("  (none)")
        if inventory.unique_member_count < 2:
            print("A second selection cannot succeed until another distinct real character/build is saved.")
        return 2

    if not args.build and inventory.has_ambiguous_member_builds:
        print()
        print("ROSTER SELECTION")
        print("  Automatic selection withheld because one or more real characters have multiple saved builds.")
        print("  Re-run with one exact --build per character for the encounter.")

    selected_real = tuple(audit for audit in selected if is_real_saved_build(audit))
    identities = tuple(saved_build_identity(audit) for audit in selected_real)
    duplicate_selected = tuple(
        identity for identity, count in Counter(identities).items() if identity and count > 1
    )

    print()
    print("EXIT ROSTER")
    if not selected_real:
        print("  (no unambiguous real roster selected)")
    for audit in selected_real:
        print(
            f"  {audit.character_name} | {audit.build_name} | id={saved_build_identity(audit)} "
            f"| effects={len(audit.resolved_effects)} | capability_gaps={len(audit.capability_resolution_gaps)}"
        )

    report = None
    evaluation_error = ""
    if selected_real and not duplicate_selected:
        try:
            evaluator = EncounterRosterEvaluator(
                encounter_service,
                SavedBuildEncounterCapabilityAdapter(()),
            )
            report = evaluator.evaluate_saved_build_audits(
                args.encounter,
                selected_real,
                difficulty=difficulty,
            )
        except (ValueError, LookupError) as exc:
            evaluation_error = str(exc)

    print()
    print("REAL ENCOUNTER EXIT EVALUATION")
    print(f"  Encounter:  {args.encounter}")
    print(f"  Difficulty: {difficulty.value}")
    if evaluation_error:
        print(f"  Evaluation error: {evaluation_error}")
    elif report is None:
        print("  Evaluation not run: no unique real roster was available.")
    else:
        print(f"  Fully evaluable:  {report.is_fully_evaluable}")
        print(f"  Capability-ready: {report.is_fully_covered}")
        print(f"  Execution rows:   {len(report.execution_evaluation.results)}")
        print(f"  Provider rows:    {len(report.provider_results)}")
        _print_execution_rows(report)

    roster_size_ok = len(selected_real) >= 2 and not duplicate_selected
    capability_sources_ok = bool(selected_real) and all(
        not audit.capability_resolution_gaps for audit in selected_real
    )
    encounter_ok = bool(report and report.is_fully_evaluable and report.is_fully_covered)

    print()
    print("PHASE 10 EXIT CRITERIA")
    print(f"  {'PASS' if inventory.real_build_count else 'BLOCK'} real saved-build data exists")
    print(f"  {'PASS' if roster_size_ok else 'BLOCK'} at least two unique real roster members selected")
    print(f"  {'PASS' if capability_sources_ok else 'BLOCK'} selected roster has no capability-resolution gaps")
    print(f"  {'PASS' if encounter_ok else 'BLOCK'} real roster is capability-ready for the selected real encounter")

    ready = roster_size_ok and capability_sources_ok and encounter_ok
    print()
    print(f"PHASE 10 EXIT READY: {ready}")
    if not ready and inventory.unique_member_count < 2:
        print("Boundary: local saved-build data does not yet contain two distinct non-template characters.")
        print("Next action: save one additional real character/build, then rerun this audit with no --build arguments.")
    if not ready and inventory.has_ambiguous_member_builds and not args.build:
        print("Boundary: choose one authoritative saved build per character with repeated --build options.")
    print("Provider assignment remains Phase 11; this audit proves capability/readiness only.")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
