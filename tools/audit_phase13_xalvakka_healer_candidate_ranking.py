from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.resource_costs import ResourceType
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from services.encounter_boss_guide import EncounterBossGuideService
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_candidate_generation_service import (
    GeneratedRotationCandidate,
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_runtime_uptime_service import RotationRuntimeUptimeRequirement
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_healer_priority_comparison import (
    _BASE_PRIORITIES,
    _audit_policy_set,
)
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_band_cost_diagnosis import _project_plan
from tools.audit_phase13_xalvakka_healer_threshold_rotation import (
    _DEMAND_NAME,
    _DEMAND_PRIORITIES,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _candidate_options(values: tuple[float, ...]) -> tuple[RotationRefreshLeadCandidateOption, ...]:
    result = []
    seen: set[float] = set()
    for raw in values:
        seconds = float(raw)
        if seconds <= 0:
            raise ValueError("all --anticipation-seconds values must be positive")
        if seconds in seen:
            continue
        seen.add(seconds)
        label = f"seeds-{seconds:g}s-early"
        result.append(
            RotationRefreshLeadCandidateOption(
                option_id=label,
                refresh_leads=(
                    DemandRefreshLead(
                        demand_name=_DEMAND_NAME,
                        bar="front",
                        skill_name="Budding Seeds",
                        lead_seconds=seconds,
                    ),
                ),
            )
        )
    return tuple(result)


def _plan_signature(candidate: GeneratedRotationCandidate):
    return tuple(
        (
            float(action.time_seconds),
            action.kind.value,
            str(action.bar or ""),
            str(action.name or ""),
        )
        for action in candidate.plan.actions
    )


def _dedupe_realized_candidates(
    candidates: tuple[GeneratedRotationCandidate, ...],
) -> tuple[GeneratedRotationCandidate, ...]:
    """Drop candidate policies that realize to the exact same action schedule."""

    seen: set[tuple] = set()
    result = []
    for candidate in candidates:
        signature = _plan_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(candidate)
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and rank explicit DF Healer rotation candidate families at representative "
            "Xalvakka DPS bands using hard obligations before resource consequences."
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
    parser.add_argument(
        "--raid-dps",
        type=float,
        nargs="+",
        default=(1_300_000.0, 1_500_000.0, 2_000_000.0),
    )
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument(
        "--anticipation-seconds",
        type=float,
        nargs="+",
        default=(1.0, 2.0, 3.0),
        help=(
            "explicit Budding Seeds early-refresh permissions to generate as separate candidates; "
            "these are audit inputs, not inferred gameplay strategy"
        ),
    )
    parser.add_argument(
        "--minimum-magicka-reserve",
        type=int,
        default=None,
        help=(
            "optional caller-supplied Magicka required immediately before the projected "
            "Phase 2 prep window; no reserve floor is invented when omitted"
        ),
    )
    parser.add_argument(
        "--minimum-winters-revenge-uptime",
        type=float,
        default=None,
        help=(
            "optional caller-supplied Winter's Revenge runtime uptime floor from 0 to 1; "
            "no uptime threshold is invented when omitted"
        ),
    )
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if any(float(value) <= 0 for value in args.raid_dps):
        raise ValueError("all --raid-dps values must be positive")
    if args.minimum_magicka_reserve is not None and int(args.minimum_magicka_reserve) < 0:
        raise ValueError("--minimum-magicka-reserve cannot be negative")
    if (
        args.minimum_winters_revenge_uptime is not None
        and not 0.0 <= float(args.minimum_winters_revenge_uptime) <= 1.0
    ):
        raise ValueError("--minimum-winters-revenge-uptime must be between 0 and 1")

    options = _candidate_options(tuple(float(value) for value in args.anticipation_seconds))
    if not options:
        raise ValueError("at least one --anticipation-seconds value is required")

    database_path = Path(args.database)
    build = _load_saved_build(
        Path(args.builds),
        character=args.character,
        build_name=args.build,
    )
    guide = EncounterBossGuideService(database_path).get(args.encounter)
    policy_set = _audit_policy_set(build, database_path=database_path)
    priority_projection = HealerRotationPriorityService().project(
        policy_set=policy_set,
        base_priorities=_BASE_PRIORITIES,
        demand_priorities=_DEMAND_PRIORITIES,
    )

    refinement_service = RotationDurationRefinementService(database_path=database_path)
    rotation_generator = RotationGenerationSupport(duration_refinement=refinement_service)
    request = RotationGenerationRequest(
        duration_seconds=float(args.duration),
        ability_priorities=priority_projection.entries,
    )
    definition = rotation_generator.build_definition(build=build, request=request)
    seed_plan = rotation_generator.planner.build_plan(definition, build)
    base_plan = refinement_service.refine(
        seed_plan,
        priorities=priority_projection.priority_list,
    ).plan

    sustain_service = RotationSustainService(database_path=database_path)
    base_sustain = sustain_service.evaluate(
        build=build,
        plan=base_plan,
        resource=ResourceType.MAGICKA,
    )
    candidate_generator = RotationCandidateGenerationService(
        refinement_service=refinement_service
    )
    scorecard_service = RotationCandidateScorecardService()
    ranking_service = RotationCandidateRankingService()
    duration_analysis_service = RotationDurationAnalysisService(database_path)

    print("=" * 118)
    print(" PHASE 13 XALVAKKA HEALER CANDIDATE FAMILY RANKING")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        "Generated Seeds anticipation candidates: "
        + ", ".join(f"{value:g}s" for value in args.anticipation_seconds)
    )
    print(
        "Hard obligation: at least one front-bar Budding Seeds cast inside the projected "
        "Phase 2 healing-prep demand window"
    )
    if args.minimum_magicka_reserve is None:
        print("Mechanic-entry reserve: not supplied; no Magicka floor is assumed")
    else:
        print(
            "Mechanic-entry reserve: "
            f"{int(args.minimum_magicka_reserve):,} Magicka immediately before the prep window "
            "(caller supplied)"
        )
    if args.minimum_winters_revenge_uptime is None:
        print("Winter's Revenge uptime: not supplied; no runtime floor is assumed")
    else:
        print(
            "Winter's Revenge uptime: "
            f">= {float(args.minimum_winters_revenge_uptime):.2%} (caller supplied)"
        )
    print(
        "Boundary: candidate leads are explicit audit possibilities. This tool generates and ranks "
        "their realized schedules; it does not infer that any lead value is canonical healer strategy."
    )

    for raid_dps in args.raid_dps:
        # Reuse the established threshold projection helper to obtain the exact demand window.
        # Its one returned plan is intentionally discarded; the candidate generator below owns
        # the family generation for this audit.
        seed_refresh_leads = options[0].refresh_leads
        phase_2, demand, _ = _project_plan(
            raid_dps=float(raid_dps),
            guide=guide,
            difficulty=args.difficulty,
            seed_plan=seed_plan,
            refinement_service=refinement_service,
            priorities=priority_projection.priority_list,
            refresh_leads=seed_refresh_leads,
            lead_seconds=float(args.lead_seconds),
            window_seconds=float(args.window_seconds),
        )

        generated = candidate_generator.generate(
            seed_plan=seed_plan,
            priorities=priority_projection.priority_list,
            demands=(demand,),
            options=options,
            baseline_id="demand-aware-0s",
        )
        all_candidates = _dedupe_realized_candidates(
            (
                GeneratedRotationCandidate(
                    candidate_id="baseline",
                    plan=base_plan,
                    refresh_leads=(),
                ),
                *generated,
            )
        )

        requirement = RotationDemandActionRequirement(
            demand_name=demand.name,
            skill_name="Budding Seeds",
            bar="front",
            minimum_casts=1,
        )
        reserve_requirements = ()
        if args.minimum_magicka_reserve is not None:
            reserve_requirements = (
                RotationResourceReserveRequirement(
                    demand_name=demand.name,
                    resource=ResourceType.MAGICKA,
                    minimum_amount=int(args.minimum_magicka_reserve),
                ),
            )
        uptime_requirements = ()
        if args.minimum_winters_revenge_uptime is not None:
            uptime_requirements = (
                RotationRuntimeUptimeRequirement(
                    skill_name="Winter's Revenge",
                    bar="back",
                    minimum_uptime=float(args.minimum_winters_revenge_uptime),
                ),
            )

        ranking_inputs = []
        for candidate in all_candidates:
            candidate_sustain = (
                base_sustain
                if candidate.candidate_id == "baseline"
                else sustain_service.evaluate(
                    build=build,
                    plan=candidate.plan,
                    resource=ResourceType.MAGICKA,
                )
            )
            candidate_duration = (
                duration_analysis_service.analyze(candidate.plan)
                if uptime_requirements
                else None
            )
            card = scorecard_service.compare(
                baseline_plan=base_plan,
                candidate_plan=candidate.plan,
                baseline_sustain=base_sustain,
                candidate_sustain=candidate_sustain,
                demands=(demand,),
                demand_requirements=(requirement,),
                reserve_requirements=reserve_requirements,
                candidate_duration=candidate_duration,
                runtime_uptime_requirements=uptime_requirements,
            )
            ranking_inputs.append(
                RotationCandidateRankingInput(candidate.candidate_id, card)
            )

        ranked = ranking_service.rank(tuple(ranking_inputs))

        print()
        print("-" * 118)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s | "
            f"{len(all_candidates)} unique realized schedules"
        )
        for item in ranked:
            card = item.scorecard
            coverage = card.demand_coverage[0]
            consequence = card.consequence
            cast_text = ", ".join(f"{value:g}s" for value in coverage.cast_times) or "none"
            reserve_text = ""
            if card.reserve_assessments:
                reserve = card.reserve_assessments[0]
                reserve_text = (
                    f" | entry Mag {reserve.available_before_start:,}/"
                    f"{reserve.requirement.minimum_amount:,}"
                )
            uptime_text = ""
            if card.runtime_uptime_assessments:
                uptime = card.runtime_uptime_assessments[0]
                observed = (
                    "unknown"
                    if uptime.observed_uptime is None
                    else f"{uptime.observed_uptime:.2%}"
                )
                uptime_text = (
                    f" | WR uptime {observed}/"
                    f"{uptime.requirement.minimum_uptime:.2%}"
                )
            print(
                f"#{item.rank} {item.candidate_id:19s} | {item.tier.value:10s} | "
                f"prep casts {cast_text:12s} | resource {consequence.resource_kind.value:8s} | "
                f"min {consequence.minimum_resource_delta:+d} | end {consequence.ending_resource_delta:+d}"
                f"{reserve_text}{uptime_text}"
            )
            for reason in item.reasons:
                print(f"    - {reason}")
            if card.candidate_specific_unresolved:
                print("    candidate-specific unresolved:")
                for message in card.candidate_specific_unresolved:
                    print(f"      * {message}")
            if card.candidate_specific_schedule_notes:
                print("    candidate-specific schedule notes:")
                for message in card.candidate_specific_schedule_notes:
                    print(f"      * {message}")

    print()
    print(
        "Interpretation: the generator supplies multiple explicit schedule possibilities, then hard "
        "encounter obligations decide eligibility before softer resource consequences. Exact duplicate "
        "realized schedules are collapsed so differently named policies do not masquerade as extra "
        "choices. Optional reserve and runtime uptime floors remain caller supplied; omitted floors are "
        "not silently invented."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
