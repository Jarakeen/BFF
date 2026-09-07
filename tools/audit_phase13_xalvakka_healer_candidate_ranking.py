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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rank baseline and encounter-aware DF Healer rotations at representative "
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
    parser.add_argument("--anticipation-seconds", type=float, default=3.0)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if any(float(value) <= 0 for value in args.raid_dps):
        raise ValueError("all --raid-dps values must be positive")

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
    refresh_leads = (
        DemandRefreshLead(
            demand_name=_DEMAND_NAME,
            bar="front",
            skill_name="Budding Seeds",
            lead_seconds=float(args.anticipation_seconds),
        ),
    )

    refinement_service = RotationDurationRefinementService(database_path=database_path)
    generator = RotationGenerationSupport(duration_refinement=refinement_service)
    request = RotationGenerationRequest(
        duration_seconds=float(args.duration),
        ability_priorities=priority_projection.entries,
    )
    definition = generator.build_definition(build=build, request=request)
    seed_plan = generator.planner.build_plan(definition, build)
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

    print("=" * 112)
    print(" PHASE 13 XALVAKKA HEALER CANDIDATE RANKING")
    print("=" * 112)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        "Hard obligation: at least one front-bar Budding Seeds cast inside the projected "
        "Phase 2 healing-prep demand window"
    )
    print(
        "Boundary: this audit ranks only supplied obligations plus canonical Magicka consequences; "
        "it does not certify the audit-only healer policy as universal gameplay truth"
    )

    for raid_dps in args.raid_dps:
        phase_2, demand, aware_plan = _project_plan(
            raid_dps=float(raid_dps),
            guide=guide,
            difficulty=args.difficulty,
            seed_plan=seed_plan,
            refinement_service=refinement_service,
            priorities=priority_projection.priority_list,
            refresh_leads=refresh_leads,
            lead_seconds=float(args.lead_seconds),
            window_seconds=float(args.window_seconds),
        )
        aware_sustain = sustain_service.evaluate(
            build=build,
            plan=aware_plan,
            resource=ResourceType.MAGICKA,
        )
        requirement = RotationDemandActionRequirement(
            demand_name=demand.name,
            skill_name="Budding Seeds",
            bar="front",
            minimum_casts=1,
        )

        baseline_card = scorecard_service.compare(
            baseline_plan=base_plan,
            candidate_plan=base_plan,
            baseline_sustain=base_sustain,
            candidate_sustain=base_sustain,
            demands=(demand,),
            demand_requirements=(requirement,),
        )
        aware_card = scorecard_service.compare(
            baseline_plan=base_plan,
            candidate_plan=aware_plan,
            baseline_sustain=base_sustain,
            candidate_sustain=aware_sustain,
            demands=(demand,),
            demand_requirements=(requirement,),
        )
        ranked = ranking_service.rank(
            (
                RotationCandidateRankingInput("baseline", baseline_card),
                RotationCandidateRankingInput("encounter-aware", aware_card),
            )
        )

        print()
        print("-" * 112)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s"
        )
        for item in ranked:
            card = item.scorecard
            coverage = card.demand_coverage[0]
            consequence = card.consequence
            cast_text = ", ".join(f"{value:g}s" for value in coverage.cast_times) or "none"
            print(
                f"#{item.rank} {item.candidate_id:15s} | {item.tier.value:10s} | "
                f"prep casts {cast_text:12s} | resource {consequence.resource_kind.value:8s} | "
                f"min {consequence.minimum_resource_delta:+d} | end {consequence.ending_resource_delta:+d}"
            )
            for reason in item.reasons:
                print(f"    - {reason}")

    print()
    print(
        "Interpretation: hard encounter obligations decide eligibility before softer resource "
        "consequences. If neither candidate satisfies the supplied obligation, neither is promoted "
        "to an eligible plan merely because its resource numbers are better."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
