from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from minmax.rotation_plan import RotationActionKind
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerMultiDemandOutput,
    RotationCandidateHealerMultiDemandRoleOutputService,
)
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerCanonicalDemandEvidenceProvider,
)
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_healer_demand_criteria_service import (
    RotationHealerDemandCriteriaService,
)
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProvider,
)
from services.rotation_healer_encounter_demand_bundle_service import (
    RotationHealerEncounterDemandBundleService,
)
from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from tools.audit_phase13_healer_priority_comparison import _BASE_PRIORITIES, _audit_policy_set
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_threshold_rotation import (
    _DEMAND_NAME,
    _DEMAND_PRIORITIES,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _candidate(candidate_id: str, plan) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )


def _window_actions(plan, demand):
    return tuple(
        action
        for action in plan.actions
        if demand.start_seconds <= float(action.time_seconds) < demand.end_seconds
        and action.kind is not RotationActionKind.LIGHT_ATTACK
    )


def _print_candidate_output(
    label: str,
    *,
    candidate: GeneratedRotationCandidate,
    output: RotationCandidateHealerMultiDemandOutput,
) -> None:
    print(f"\n{label}")
    print("-" * 112)
    for window in output.windows:
        demand = window.demand
        evidence = window.evidence
        print(
            f"Demand: {demand.name} | {demand.start_seconds:.2f}s-{demand.end_seconds:.2f}s "
            f"| pattern={demand.pattern.value} | target_count={demand.target_count}"
        )
        actions = _window_actions(candidate.plan, demand)
        print("Scheduled non-LA actions inside window:")
        if not actions:
            print("  (none)")
        for action in actions:
            print(
                f"  {float(action.time_seconds):6.2f}s | {str(action.bar or '-'):5s} | "
                f"{action.kind.value:12s} | {str(action.name or '(unnamed)')}"
            )

        print(
            "Modeled healing evidence: "
            f"direct={evidence.modeled_direct_healing:g}, "
            f"periodic={evidence.modeled_periodic_healing:g}, "
            f"delayed={evidence.modeled_delayed_healing:g}, "
            f"total={evidence.modeled_total_healing:g}"
        )
        value = window.modeled_healing_per_demand_second
        print(
            "Modeled healing per demand-second: "
            + (f"{value:g}" if value is not None else "UNRESOLVED")
        )
        print(
            "Resolved events: "
            f"direct={len(evidence.direct_events)}, periodic={len(evidence.periodic_events)}, "
            f"delayed={len(evidence.delayed_events)}"
        )
        if window.unresolved:
            print("Unresolved canonical evidence:")
            for item in window.unresolved:
                print(f"  - {item}")
        else:
            print("Unresolved canonical evidence: none")

    weakest = output.weakest_window_value
    print(
        "Candidate weakest-window modeled output: "
        + (f"{weakest:g}" if weakest is not None else "UNRESOLVED")
    )


def _load_reviewed_runtime_observations(
    database_path: Path,
    fixture_path: Path | None,
):
    if fixture_path is None:
        return (), ()
    report = RotationHealerPeriodicObservationFixtureService(database_path).load(fixture_path)
    return tuple(report.reviewed_observations), tuple(report.unresolved)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a saved healer build's canonical modeled healing inside the real projected "
            "Xalvakka Phase 2 preparation window. The audit compares an ordinary refined plan "
            "with an encounter-window-aware refined plan and never invents a survival threshold."
        )
    )
    parser.add_argument("--character", default="Magrat")
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--encounter", default="xalvakka")
    parser.add_argument(
        "--difficulty",
        choices=("normal", "veteran", "hardmode"),
        default="hardmode",
    )
    parser.add_argument("--raid-dps", type=float, default=2_000_000.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--runtime-observations",
        type=Path,
        default=None,
        help=(
            "optional reviewed healer periodic-runtime fixture; omitted means periodic first-tick/"
            "expiry/refresh evidence stays unresolved rather than being guessed"
        ),
    )
    parser.add_argument(
        "--reviewed-criterion-fact-id",
        action="append",
        default=[],
        help=(
            "exact healer_demand_criterion encounter fact id explicitly approved for hard-gate use; "
            "may be supplied more than once"
        ),
    )
    args = parser.parse_args()

    if float(args.raid_dps) <= 0:
        raise ValueError("--raid-dps must be positive")
    if float(args.duration) <= 0:
        raise ValueError("--duration must be positive")
    if float(args.lead_seconds) < 0:
        raise ValueError("--lead-seconds cannot be negative")
    if float(args.window_seconds) <= 0:
        raise ValueError("--window-seconds must be positive")

    data_root = get_data_dir()
    database_path = Path(args.database)
    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    guide = EncounterBossGuideService(database_path).get(args.encounter)

    encounter_repository = EncounterRepository(
        data_root / "eso_info" / "bosses",
        data_root / "encounter_evidence",
        database_path=database_path,
    )
    encounter_service = EncounterService(encounter_repository)
    criteria_provider = RotationHealerEncounterCriteriaProvider(encounter_service)
    bundle_service = RotationHealerEncounterDemandBundleService(
        criteria_provider=criteria_provider
    )
    bundle = bundle_service.project(
        guide=guide,
        difficulty=args.difficulty,
        damage_segments=(
            RaidDamageSegment(
                0.0,
                None,
                float(args.raid_dps),
                "caller-supplied constant raid DPS audit assumption",
            ),
        ),
        demand_policies=(
            EncounterThresholdRotationDemandPolicy(
                fact_key="phase_2",
                threshold_fraction=0.70,
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
                lead_seconds=float(args.lead_seconds),
                window_seconds=float(args.window_seconds),
                target_count=12,
                name=_DEMAND_NAME,
            ),
        ),
        reviewed_fact_ids=tuple(args.reviewed_criterion_fact_id),
    )
    if not bundle.demands:
        detail = "; ".join(bundle.unresolved) or "no Xalvakka healing demand projected"
        raise RuntimeError(detail)

    static_contexts = RotationStaticBuildContextService(
        builds_path=Path(args.builds),
        database_path=database_path,
    ).resolve(build)
    if not static_contexts.resolved:
        detail = "; ".join(static_contexts.unresolved) or "static build contexts unresolved"
        raise RuntimeError(f"saved-build static context is not fully resolved: {detail}")
    front_context = static_contexts.context_for("front")
    back_context = static_contexts.context_for("back")
    if front_context is None or back_context is None:
        raise RuntimeError("saved-build healer audit requires both front and back static contexts")
    contexts_by_bar = {"front": front_context, "back": back_context}

    runtime_observations, runtime_fixture_unresolved = _load_reviewed_runtime_observations(
        database_path,
        args.runtime_observations,
    )

    policy_set = _audit_policy_set(build, database_path=database_path)
    priorities = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
        demand_priorities=_DEMAND_PRIORITIES,
    )
    refinement = RotationDurationRefinementService(database_path=database_path)
    generator = RotationGenerationSupport(duration_refinement=refinement)
    definition = generator.build_definition(
        build=build,
        request=RotationGenerationRequest(
            duration_seconds=float(args.duration),
            ability_priorities=priorities.entries,
        ),
    )
    seed_plan = generator.planner.build_plan(definition, build)
    ordinary_plan = refinement.refine(
        seed_plan,
        priorities=priorities.priority_list,
    ).plan
    encounter_plan = refinement.refine(
        seed_plan,
        priorities=priorities.priority_list,
        demands=bundle.demands,
    ).plan

    demand_evidence_provider = RotationCandidateHealerCanonicalDemandEvidenceProvider(
        database_path=database_path,
        build=build,
        context=front_context,
        contexts_by_bar=contexts_by_bar,
        reviewed_runtime_observations=runtime_observations,
    )
    role_output = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=bundle.demands,
        demand_evidence_provider=demand_evidence_provider,
    )

    ordinary = _candidate("ordinary", ordinary_plan)
    encounter_aware = _candidate("xalvakka-aware", encounter_plan)
    ordinary_output = role_output.evaluate_windows(ordinary)
    encounter_output = role_output.evaluate_windows(encounter_aware)

    phase_2 = next(
        point
        for point in bundle.threshold_projection.points
        if point.fact_key == "phase_2" and abs(point.threshold_fraction - 0.70) <= 1e-9
    )

    print("=" * 112)
    print(" PHASE 13 XALVAKKA SAVED-BUILD HEALER ENCOUNTER OUTPUT AUDIT")
    print("=" * 112)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(f"Boss health: {bundle.threshold_projection.maximum_health:,}")
    print(f"Raid DPS trajectory: {float(args.raid_dps):,.0f} (caller supplied)")
    print(
        "Projected Phase 2 threshold: "
        + (f"{phase_2.time_seconds:.2f}s at 70% health" if phase_2.time_seconds is not None else "UNRESOLVED")
    )
    demand = bundle.demands[0]
    print(f"Healing prep window: {demand.start_seconds:.2f}s-{demand.end_seconds:.2f}s")
    print(
        "Static build state: exact front/back canonical contexts resolved; actions are evaluated "
        "against the bar on which they are scheduled."
    )
    print(
        "Healing unit: modeled pre-recipient, pre-overheal healing per demand-second. "
        "This is not observed HPS and is not a survival threshold."
    )
    print(
        "Encounter criteria: "
        + (f"{len(bundle.criteria)} selected structured criterion/criteria" if bundle.criteria else "none; no numeric healer floor is invented")
    )
    if runtime_fixture_unresolved:
        print("Reviewed periodic-runtime fixture unresolved evidence:")
        for item in runtime_fixture_unresolved:
            print(f"  - {item}")

    _print_candidate_output(
        "ORDINARY REFINED PLAN",
        candidate=ordinary,
        output=ordinary_output,
    )
    _print_candidate_output(
        "XALVAKKA-WINDOW-AWARE REFINED PLAN",
        candidate=encounter_aware,
        output=encounter_output,
    )

    if bundle.criteria:
        criteria_service = RotationHealerDemandCriteriaService()
        for label, output in (
            ("ordinary", ordinary_output),
            ("xalvakka-aware", encounter_output),
        ):
            assessment = criteria_service.assess(output=output, criteria=bundle.criteria)
            print(f"\n{label} encounter criteria:")
            for item in assessment.assessments:
                state = item.meets_threshold
                rendered = "UNKNOWN" if state is None else ("PASS" if state else "FAIL")
                authority = "verified" if item.criterion.authoritative else "diagnostic assumption"
                print(
                    f"  {item.criterion.demand_name}: {rendered} ({authority}) | "
                    f"minimum={item.criterion.minimum_modeled_healing_per_demand_second:g}"
                )

    print("\nBOUNDARIES")
    print("-" * 112)
    print("- 70% Phase 2 threshold is reviewed encounter truth; its clock time depends on supplied raid DPS.")
    print("- Healer demand priority is strategy/audit policy, not canonical encounter truth.")
    print("- No numeric healer survival threshold is inferred from prose such as 'continuous high flame damage'.")
    print("- Missing periodic/delayed runtime evidence remains unresolved and prevents a fake resolved output value.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
