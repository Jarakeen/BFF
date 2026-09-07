from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.resource_costs import ResourceType
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from services.encounter_boss_guide import EncounterBossGuideService
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_healer_priority_comparison import _BASE_PRIORITIES, _audit_policy_set
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_band_cost_diagnosis import _project_plan
from tools.audit_phase13_xalvakka_healer_threshold_rotation import (
    _DEMAND_NAME,
    _DEMAND_PRIORITIES,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the baseline DF Healer rotation with one explicit mechanic-driven Budding Seeds "
            "action claim inside the projected Xalvakka Phase 2 prep window."
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
    parser.add_argument("--raid-dps", type=float, nargs="+", default=(2_000_000.0,))
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--lead-seconds", type=float, default=3.0)
    parser.add_argument("--window-seconds", type=float, default=2.0)
    parser.add_argument(
        "--minimum-magicka-reserve",
        type=int,
        default=None,
        help=(
            "optional caller-supplied Magicka required immediately before the projected prep window; "
            "no reserve floor is invented when omitted"
        ),
    )
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if any(float(value) <= 0 for value in args.raid_dps):
        raise ValueError("all --raid-dps values must be positive")
    if args.minimum_magicka_reserve is not None and int(args.minimum_magicka_reserve) < 0:
        raise ValueError("--minimum-magicka-reserve cannot be negative")

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
    scorecard_service = RotationCandidateScorecardService()
    ranking_service = RotationCandidateRankingService()

    print("=" * 118)
    print(" PHASE 13 XALVAKKA HEALER MECHANIC ACTION CLAIM")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        "Claim: Budding Seeds may take one front-bar skill slot inside the named Phase 2 prep demand "
        "only when its ordinary refresh would otherwise occur after that demand ends."
    )
    print(
        "Boundary: this is an explicit diagnostic mechanic policy, not canonical healer strategy. "
        "The claim does not shorten Budding Seeds' verified duration rule globally."
    )

    for raid_dps in args.raid_dps:
        # Reuse the established threshold projection path only to obtain the exact
        # health-derived demand window. The returned lead-based plan is discarded.
        phase_2, demand, _ = _project_plan(
            raid_dps=float(raid_dps),
            guide=guide,
            difficulty=args.difficulty,
            seed_plan=seed_plan,
            refinement_service=refinement_service,
            priorities=priority_projection.priority_list,
            refresh_leads=(
                DemandRefreshLead(
                    demand_name=_DEMAND_NAME,
                    bar="front",
                    skill_name="Budding Seeds",
                    lead_seconds=1.0,
                ),
            ),
            lead_seconds=float(args.lead_seconds),
            window_seconds=float(args.window_seconds),
        )

        claim_plan = refinement_service.refine(
            seed_plan,
            priorities=priority_projection.priority_list,
            demands=(demand,),
            demand_action_claims=(
                DemandActionClaim(
                    demand_name=demand.name,
                    bar="front",
                    skill_name="Budding Seeds",
                ),
            ),
        ).plan
        claim_sustain = sustain_service.evaluate(
            build=build,
            plan=claim_plan,
            resource=ResourceType.MAGICKA,
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

        baseline_card = scorecard_service.compare(
            baseline_plan=base_plan,
            candidate_plan=base_plan,
            baseline_sustain=base_sustain,
            candidate_sustain=base_sustain,
            demands=(demand,),
            demand_requirements=(requirement,),
            reserve_requirements=reserve_requirements,
        )
        claim_card = scorecard_service.compare(
            baseline_plan=base_plan,
            candidate_plan=claim_plan,
            baseline_sustain=base_sustain,
            candidate_sustain=claim_sustain,
            demands=(demand,),
            demand_requirements=(requirement,),
            reserve_requirements=reserve_requirements,
        )
        ranked = ranking_service.rank(
            (
                RotationCandidateRankingInput("baseline", baseline_card),
                RotationCandidateRankingInput("mechanic-claim", claim_card),
            )
        )

        print()
        print("-" * 118)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s"
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
            print(
                f"#{item.rank} {item.candidate_id:15s} | {item.tier.value:10s} | "
                f"prep casts {cast_text:12s} | resource {consequence.resource_kind.value:8s} | "
                f"min {consequence.minimum_resource_delta:+d} | end {consequence.ending_resource_delta:+d}"
                f"{reserve_text}"
            )
            for reason in item.reasons:
                print(f"    - {reason}")
            if card.candidate_specific_schedule_notes:
                print("    candidate-specific schedule notes:")
                for message in card.candidate_specific_schedule_notes:
                    print(f"      * {message}")
            if card.candidate_specific_unresolved:
                print("    candidate-specific unresolved:")
                for message in card.candidate_specific_unresolved:
                    print(f"      * {message}")

    print()
    print(
        "Interpretation: if the mechanic-claim plan becomes eligible, the 2.0m failure was not a lack "
        "of available action time; it was a policy limitation of due-only refresh scheduling. The "
        "resource/cascade evidence then shows the concrete price of deliberately moving Seeds into the mechanic."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
