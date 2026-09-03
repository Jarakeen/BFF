from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.build_service import BuildService
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_provider_assignment import EncounterProviderAssignmentService
from services.encounter_provider_candidate import EncounterProviderCandidateService
from services.encounter_repository import EncounterRepository
from services.encounter_requirement_overlay import EncounterRequirementOverlayService
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.paths import DATA
from services.phase10_closeout_audit import audit_phase10_roster_inventory, is_real_saved_build
from services.raid_coverage_encounter_adapter import RaidCoverageEncounterAdapter
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.saved_build_capability_service import SavedBuildCapabilityService


def _label(candidate) -> str:
    return candidate.character_name or candidate.build_name or candidate.member_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the real local saved roster against one canonical encounter plus "
            "the mapped default raid coverage provider requirements"
        )
    )
    parser.add_argument("--encounter", default="oaxiltso")
    parser.add_argument("--difficulty", default="veteran")
    args = parser.parse_args()

    database = DATA / "eso.db"
    builds_path = DATA / "builds.json"
    if not database.exists():
        print(f"BLOCKED: database file does not exist: {database}")
        return 2
    if not builds_path.exists():
        print(f"BLOCKED: saved builds file does not exist: {builds_path}")
        return 2

    build_service = BuildService(builds_path)
    capability_service = SavedBuildCapabilityService(build_service, database)
    all_audits = capability_service.audit_roster()
    audits = tuple(audit for audit in all_audits if is_real_saved_build(audit))
    inventory = audit_phase10_roster_inventory(audits)

    if not audits:
        print("BLOCKED: no real saved builds are available for provider validation")
        return 2
    if inventory.has_ambiguous_member_builds:
        print(
            "BLOCKED: multiple selected builds resolve to the same roster member: "
            + ", ".join(inventory.duplicate_member_ids)
        )
        return 2

    base_service = EncounterService(EncounterRepository.from_data_root(DATA))
    coverage = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)
    coverage_requirements = coverage.requirements(args.encounter)
    overlay = EncounterRequirementOverlayService(
        base_service,
        {args.encounter: coverage_requirements},
    )
    build_adapter = SavedBuildEncounterCapabilityAdapter(
        coverage.capability_identity_maps()
    )
    evaluator = EncounterRosterEvaluator(
        overlay,
        build_adapter,
        requirement_semantics=coverage.requirement_semantics(),
        required_provider_counts=coverage.required_provider_counts(args.encounter),
    )
    report = evaluator.evaluate_saved_build_audits(
        args.encounter,
        audits,
        difficulty=args.difficulty,
    )
    candidate_sets = EncounterProviderCandidateService().candidates(report, audits)
    assignments = EncounterProviderAssignmentService().assign(candidate_sets)

    print("=" * 76)
    print(" PHASE 11 DEFAULT RAID COVERAGE PROVIDER EVALUATION")
    print("=" * 76)
    print(f"encounter:                    {args.encounter}")
    print(f"difficulty:                   {args.difficulty}")
    print(f"real saved builds:            {inventory.real_build_count}")
    print(f"unique roster members:        {inventory.unique_member_count}")
    print(f"canonical mechanic rows:      {len(base_service.requirements(args.encounter))}")
    print(f"mapped coverage rows:         {len(coverage_requirements)}")
    print(f"unmapped required coverage:   {len(DEFAULT_RAID_COVERAGE_PROFILE.unmapped_required)}")
    print(f"provider evaluation rows:     {len(report.provider_results)}")
    print()

    print("=== REAL ROSTER ===")
    for audit in audits:
        identity = audit.character_id or audit.character_name or audit.build_name
        print(
            f"  - {audit.character_name} | {audit.build_name} | {identity} | "
            f"effects={len(audit.resolved_effects)} | capability_gaps={len(audit.capability_resolution_gaps)}"
        )
    print()

    print("=== PROVIDER REQUIREMENTS ===")
    if not assignments:
        print("  none")
    for candidate_set, assignment in zip(candidate_sets, assignments, strict=True):
        print(
            f"  {candidate_set.requirement_id} | capability={candidate_set.requirement_type} | "
            f"coverage={candidate_set.coverage_classification.value} | "
            f"assignment={assignment.status.value}"
        )
        for candidate in candidate_set.candidates:
            sources = "; ".join(candidate.evidence_sources) or "no source string"
            print(
                f"    candidate: {_label(candidate)} | {candidate.status.value} | {sources}"
            )
        if assignment.primary_providers:
            print(
                "    primary: "
                + ", ".join(_label(candidate) for candidate in assignment.primary_providers)
            )
        if assignment.backup_providers:
            print(
                "    backup: "
                + ", ".join(_label(candidate) for candidate in assignment.backup_providers)
            )
        if assignment.unresolved_candidates:
            print(
                "    unresolved: "
                + ", ".join(_label(candidate) for candidate in assignment.unresolved_candidates)
            )
        print(f"    reason: {assignment.explanation}")

    assigned = tuple(row for row in assignments if row.is_assigned)
    print()
    if assigned:
        print(
            f"RESULT: PASS - {len(assigned)} configured provider requirement(s) received "
            "a deterministic primary assignment from the real saved roster"
        )
        return 0

    print(
        "RESULT: UNRESOLVED - configured provider requirements reached Phase 11, "
        "but current evidence did not uniquely determine a primary provider"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
