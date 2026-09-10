from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.fight_damage_trajectory import RaidDamageSegment, project_health_threshold_times
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from minmax.rotation_plan import RotationActionKind
from services.encounter_boss_guide import (
    BossGuidePhase,
    EncounterBossGuide,
    EncounterBossGuideNotFound,
    EncounterBossGuideService,
)
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)
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
from services.rotation_healer_demand_criteria_service import RotationHealerDemandCriteriaService
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProvider,
)
from services.rotation_healer_encounter_demand_bundle_service import (
    RotationHealerEncounterDemandBundleService,
)
from services.rotation_healer_output_context_relevance_service import (
    RotationHealerOutputContextRelevanceService,
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
_PERCENT = re.compile(r"^\s*(100|[1-9]?\d(?:\.\d+)?)\s*%\s*$")
_HEALTH = re.compile(r"^\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\s*\([^()]*\))?\s*$")


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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")


def _guide_from_source_definition(definition) -> EncounterBossGuide:
    structural_phases = tuple(
        BossGuidePhase(
            phase_id=index,
            label=phase.label,
            threshold=phase.threshold,
            description=phase.description,
            source_section="source-backed structural phase",
            source_url=definition.source.url,
            source_revision_id=definition.source.revision_id,
        )
        for index, phase in enumerate(definition.phases, start=1)
    )
    return EncounterBossGuide(
        encounter_id=definition.encounter_id,
        content_id=definition.content_id,
        content_name=definition.content_id.replace("_", " ").title(),
        name=definition.name,
        summary="",
        location="",
        species=definition.actors[0].species if definition.actors else "",
        reaction="",
        health_record_present=bool(definition.difficulty_health),
        health=tuple(definition.difficulty_health),
        abilities=(),
        phases=structural_phases,
        structural_phases=structural_phases,
        timeline_facts=(),
        source_url=definition.source.url,
        source_page_title=definition.source.page_title,
        source_revision_id=definition.source.revision_id,
        retrieved_at=definition.source.retrieved_at,
        source_license=definition.source.license,
    )


class _SourceStructuralThresholdProjectionService:
    """Audit-only clock projection over exact source structural phase rows."""

    def project(self, *, guide, difficulty, damage_segments):
        difficulty_key = str(difficulty or "").strip().casefold()
        raw_health = dict(guide.health).get(difficulty_key, "")
        match = _HEALTH.fullmatch(raw_health)
        if match is None:
            return EncounterHealthThresholdProjection(
                encounter_id=guide.encounter_id,
                difficulty=difficulty_key,
                maximum_health=None,
                trajectory=None,
                points=(),
                unresolved=(
                    f"{difficulty_key}: source-backed encounter health is missing or not unambiguously numeric",
                ),
            )

        maximum_health = int(match.group(1).replace(",", ""))
        rows = []
        for phase in guide.structural_phases:
            threshold_match = _PERCENT.fullmatch(str(phase.threshold or ""))
            if threshold_match is None:
                continue
            percent = float(threshold_match.group(1))
            if 0 < percent < 100:
                rows.append((phase, percent / 100.0))

        if not rows:
            return EncounterHealthThresholdProjection(
                encounter_id=guide.encounter_id,
                difficulty=difficulty_key,
                maximum_health=maximum_health,
                trajectory=None,
                points=(),
                unresolved=("no source-backed structural health thresholds are available",),
            )

        trajectory = project_health_threshold_times(
            maximum_health=maximum_health,
            thresholds=tuple(fraction for _, fraction in rows),
            segments=tuple(damage_segments),
        )
        points = []
        unresolved = []
        for (phase, fraction), projected in zip(rows, trajectory.thresholds):
            fact_key = _slug(phase.label) or f"phase_{phase.phase_id}"
            reason = (
                "projected from exact source-backed structural phase threshold and supplied raid DPS"
                if projected.resolved
                else projected.reason
            )
            points.append(
                EncounterThresholdClockPoint(
                    fact_key=fact_key,
                    label=phase.label or fact_key.replace("_", " ").title(),
                    threshold_fraction=fraction,
                    time_seconds=projected.time_seconds,
                    resolved=projected.resolved,
                    reason=reason,
                )
            )
            if not projected.resolved:
                unresolved.append(f"{fact_key} at {fraction * 100:g}%: {reason}")

        return EncounterHealthThresholdProjection(
            encounter_id=guide.encounter_id,
            difficulty=difficulty_key,
            maximum_health=maximum_health,
            trajectory=trajectory,
            points=tuple(points),
            unresolved=tuple(unresolved),
        )


def _load_guide_for_audit(
    *,
    database_path: Path,
    repository: EncounterRepository,
    encounter_id: str,
):
    try:
        guide = EncounterBossGuideService(database_path).get(encounter_id)
    except EncounterBossGuideNotFound:
        definition = repository.get(encounter_id)
        return (
            _guide_from_source_definition(definition),
            _SourceStructuralThresholdProjectionService(),
            "source-backed structural fallback",
        )
    return guide, None, "persisted reviewed boss guide"


def _load_reviewed_runtime_observations(
    database_path: Path | None,
    fixture_path: Path | None,
):
    if fixture_path is None:
        return (), ()
    report = RotationHealerPeriodicObservationFixtureService(database_path).load(fixture_path)
    return tuple(report.reviewed_observations), tuple(report.unresolved)


def _with_static_context_blockers(
    output: RotationCandidateHealerMultiDemandOutput,
    blockers: tuple[str, ...],
) -> RotationCandidateHealerMultiDemandOutput:
    if not blockers:
        return output
    unresolved = tuple(
        dict.fromkeys(
            tuple(output.unresolved)
            + tuple(f"static healer-output context: {message}" for message in blockers)
        )
    )
    return RotationCandidateHealerMultiDemandOutput(
        candidate_id=output.candidate_id,
        windows=output.windows,
        unresolved=unresolved,
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

        provisional = bool(output.unresolved or window.unresolved)
        prefix = "Provisional modeled healing evidence" if provisional else "Modeled healing evidence"
        print(
            f"{prefix}: direct={evidence.modeled_direct_healing:g}, "
            f"periodic={evidence.modeled_periodic_healing:g}, "
            f"delayed={evidence.modeled_delayed_healing:g}, "
            f"total={evidence.modeled_total_healing:g}"
        )
        value = window.modeled_healing_per_demand_second
        print(
            "Per-window modeled healing per demand-second: "
            + (f"{value:g}" if value is not None else "UNRESOLVED")
        )
        print(
            "Resolved events: "
            f"direct={len(evidence.direct_events)}, periodic={len(evidence.periodic_events)}, "
            f"delayed={len(evidence.delayed_events)}"
        )
        if window.unresolved:
            print("Unresolved canonical window evidence:")
            for item in window.unresolved:
                print(f"  - {item}")
        else:
            print("Unresolved canonical window evidence: none")

    if output.unresolved:
        print("Aggregate blockers:")
        for item in output.unresolved:
            print(f"  - {item}")
    weakest = output.weakest_window_value
    print(
        "Candidate weakest-window modeled output: "
        + (f"{weakest:g}" if weakest is not None else "UNRESOLVED")
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a saved healer build's canonical modeled healing inside the projected "
            "Xalvakka Phase 2 preparation window without inventing a survival threshold."
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
        help="optional reviewed healer periodic-runtime observation fixture",
    )
    parser.add_argument(
        "--reviewed-criterion-fact-id",
        action="append",
        default=[],
        help="exact healer_demand_criterion fact id explicitly approved for hard-gate use",
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

    encounter_repository = EncounterRepository(
        data_root / "eso_info" / "bosses",
        data_root / "encounter_evidence",
        database_path=database_path,
    )
    guide, fallback_threshold_service, guide_source = _load_guide_for_audit(
        database_path=database_path,
        repository=encounter_repository,
        encounter_id=args.encounter,
    )
    encounter_service = EncounterService(encounter_repository)
    criteria_provider = RotationHealerEncounterCriteriaProvider(encounter_service)
    if fallback_threshold_service is None:
        bundle_service = RotationHealerEncounterDemandBundleService(
            criteria_provider=criteria_provider
        )
    else:
        bundle_service = RotationHealerEncounterDemandBundleService(
            criteria_provider=criteria_provider,
            threshold_projection_service=fallback_threshold_service,
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
    front_context = static_contexts.context_for("front")
    back_context = static_contexts.context_for("back")
    if front_context is None or back_context is None:
        detail = "; ".join(static_contexts.unresolved) or "no usable static contexts"
        raise RuntimeError(
            "saved-build healer audit requires front and back static contexts: " + detail
        )
    contexts_by_bar = {"front": front_context, "back": back_context}
    static_relevance = RotationHealerOutputContextRelevanceService().classify(
        static_contexts.unresolved
    )

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
    ordinary_output = _with_static_context_blockers(
        role_output.evaluate_windows(ordinary),
        static_relevance.relevant,
    )
    encounter_output = _with_static_context_blockers(
        role_output.evaluate_windows(encounter_aware),
        static_relevance.relevant,
    )

    phase_2 = next(
        point
        for point in bundle.threshold_projection.points
        if point.fact_key == "phase_2" and abs(point.threshold_fraction - 0.70) <= 1e-9
    )
    demand = bundle.demands[0]

    print("=" * 112)
    print(" PHASE 13 XALVAKKA SAVED-BUILD HEALER ENCOUNTER OUTPUT AUDIT")
    print("=" * 112)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(f"Encounter timing source: {guide_source}")
    print(f"Boss health: {bundle.threshold_projection.maximum_health:,}")
    print(f"Raid DPS trajectory: {float(args.raid_dps):,.0f} (caller supplied)")
    print(
        "Projected Phase 2 threshold: "
        + (
            f"{phase_2.time_seconds:.2f}s at 70% health"
            if phase_2.time_seconds is not None
            else "UNRESOLVED"
        )
    )
    print(f"Healing prep window: {demand.start_seconds:.2f}s-{demand.end_seconds:.2f}s")
    print("Static build state: front/back canonical contexts are evaluated on the scheduled action bar.")
    print(
        "Healing unit: modeled pre-recipient, pre-overheal healing per demand-second. "
        "This is not observed HPS or a survival threshold."
    )
    print(
        "Encounter criteria: "
        + (
            f"{len(bundle.criteria)} selected structured criterion/criteria"
            if bundle.criteria
            else "none; no numeric healer floor is invented"
        )
    )

    if static_relevance.ambient:
        print("Static context diagnostics irrelevant to modeled healer output:")
        for item in static_relevance.ambient:
            print(f"  - {item}")
    if static_relevance.relevant:
        print("Static context blockers retained fail-closed:")
        for item in static_relevance.relevant:
            print(f"  - {item}")
        print("  Result status: INCOMPLETE; component values below are diagnostic/provisional.")
    else:
        print("Static healer-output context blockers: none")

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
    if guide_source == "persisted reviewed boss guide":
        print("- 70% Phase 2 threshold came from persisted reviewed encounter timeline data.")
    else:
        print("- 70% Phase 2 threshold came from exact source-backed structural encounter data because local persistence was absent.")
        print("- Source fallback is audit-only and is not promoted or written into canonical persistence by this tool.")
    print("- Threshold clock time depends on supplied raid DPS.")
    print("- Healer demand priority is strategy/audit policy, not canonical encounter truth.")
    print("- Static context diagnostics irrelevant to healer output are reported but do not block this objective.")
    print("- Unknown or healing-relevant static diagnostics remain aggregate blockers and keep weakest-window output unresolved.")
    print("- No numeric healer survival threshold is inferred from prose such as 'continuous high flame damage'.")
    print("- Missing periodic/delayed runtime evidence remains unresolved instead of becoming fake ticks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
