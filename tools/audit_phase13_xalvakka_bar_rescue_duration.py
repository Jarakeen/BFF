from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from services.encounter_boss_guide import EncounterBossGuideService
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_demand_bar_access_service import (
    RotationDemandBarAccessClaim,
    RotationDemandBarAccessService,
)
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_duration_consequence_service import RotationDurationConsequenceService
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from tools.audit_phase13_healer_priority_comparison import _BASE_PRIORITIES, _audit_policy_set
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_band_cost_diagnosis import _project_plan
from tools.audit_phase13_xalvakka_healer_threshold_rotation import (
    _DEMAND_NAME,
    _DEMAND_PRIORITIES,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"
_TRACKED = (
    ("Expansive Frost Cloak", "back"),
    ("Winter's Revenge", "back"),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure canonical duration/recast consequences of the explicit Xalvakka healer "
            "bar-access rescue without inventing support-uptime acceptability thresholds."
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
    args = parser.parse_args()

    if float(args.raid_dps) <= 0:
        raise ValueError("--raid-dps must be positive")

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
    generator = RotationGenerationSupport(duration_refinement=refinement_service)
    request = RotationGenerationRequest(
        duration_seconds=float(args.duration),
        ability_priorities=priority_projection.entries,
    )
    definition = generator.build_definition(build=build, request=request)
    seed_plan = generator.planner.build_plan(definition, build)
    baseline_refinement = refinement_service.refine(
        seed_plan,
        priorities=priority_projection.priority_list,
    )
    baseline_plan = baseline_refinement.plan

    phase_2, demand, _ = _project_plan(
        raid_dps=float(args.raid_dps),
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

    rescue = RotationDemandBarAccessService().refine(
        plan=baseline_plan,
        demands=(demand,),
        claim=RotationDemandBarAccessClaim(
            demand_name=demand.name,
            bar="front",
            skill_name="Budding Seeds",
        ),
    )

    duration_analysis = RotationDurationAnalysisService(database_path)
    baseline_duration = duration_analysis.analyze(baseline_plan)
    rescue_duration = duration_analysis.analyze(rescue.plan)
    consequences = RotationDurationConsequenceService().compare(
        baseline=baseline_duration,
        candidate=rescue_duration,
        skills=_TRACKED,
    )

    print("=" * 118)
    print(" PHASE 13 XALVAKKA HEALER BAR-RESCUE DURATION CONSEQUENCES")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        f"Raid DPS: {float(args.raid_dps):,.0f} | 70% at {float(phase_2.time_seconds):.2f}s | "
        f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s"
    )
    print(f"Bar-access rescue: {'APPLIED' if rescue.applied else 'NOT APPLIED'} | {rescue.reason}")
    print(
        "Boundary: this audit reports duration/recast deltas only. It does not invent a minimum support "
        "uptime or maximum acceptable gap for Frost Cloak or Winter's Revenge."
    )

    for item in consequences:
        print()
        print(f"{item.skill_name} [{item.bar or 'any'}]")
        if item.unresolved:
            for message in item.unresolved:
                print(f"  UNRESOLVED: {message}")
            continue
        assert item.baseline is not None and item.candidate is not None
        print(
            f"  casts: {item.baseline.cast_count} -> {item.candidate.cast_count} "
            f"({item.cast_count_delta:+d})"
        )
        print(
            f"  active: {item.baseline.active_seconds:.2f}s -> {item.candidate.active_seconds:.2f}s "
            f"({item.active_seconds_delta:+.2f}s)"
        )
        print(
            f"  uptime: {item.baseline.uptime_fraction * 100:.2f}% -> "
            f"{item.candidate.uptime_fraction * 100:.2f}% "
            f"({item.uptime_fraction_delta * 100:+.2f} pp)"
        )
        print(
            f"  total gaps: {item.baseline.total_gap_seconds:.2f}s -> "
            f"{item.candidate.total_gap_seconds:.2f}s "
            f"({item.total_gap_seconds_delta:+.2f}s)"
        )
        print(
            f"  premature overlap: {item.baseline.total_premature_seconds:.2f}s -> "
            f"{item.candidate.total_premature_seconds:.2f}s "
            f"({item.total_premature_seconds_delta:+.2f}s)"
        )

    print()
    print(
        "Interpretation: preserving the displaced cast names is necessary but not sufficient. These deltas "
        "show whether the rescue changed their canonical duration coverage; a later encounter/support policy "
        "must decide whether any observed gap is acceptable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
