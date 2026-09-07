from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.resource_costs import ResourceType
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from services.encounter_boss_guide import EncounterBossGuideService
from services.healer_rotation_priority_service import HealerRotationPriorityService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate, RotationCandidateGenerationService
from services.rotation_candidate_ranking_service import RotationCandidateRankingInput, RotationCandidateRankingService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService, RotationDemandActionRequirement
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_sustain_service import RotationSustainService
from tools.audit_phase13_healer_priority_comparison import _BASE_PRIORITIES, _audit_policy_set
from tools.audit_phase13_saved_build_recovery_heavy_rotation import _load_saved_build
from tools.audit_phase13_xalvakka_healer_band_cost_diagnosis import _project_plan
from tools.audit_phase13_xalvakka_healer_candidate_ranking import (
    _candidate_options,
    _dedupe_realized_candidates,
    _plan_signature,
)
from tools.audit_phase13_xalvakka_healer_threshold_rotation import _DEMAND_PRIORITIES
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _lead_grid(start: float, stop: float, step: float) -> tuple[float, ...]:
    start_value = float(start)
    stop_value = float(stop)
    step_value = float(step)
    if start_value <= 0:
        raise ValueError("--start-seconds must be positive")
    if stop_value < start_value:
        raise ValueError("--stop-seconds must be greater than or equal to --start-seconds")
    if step_value <= 0:
        raise ValueError("--step-seconds must be positive")

    values = []
    value = start_value
    tolerance = step_value * 1e-9
    while value <= stop_value + tolerance:
        values.append(round(value, 9))
        value += step_value
    return tuple(values)


def _lead_from_candidate_id(candidate_id: str) -> float | None:
    text = str(candidate_id)
    if not text.startswith("seeds-") or not text.endswith("s-early"):
        return None
    raw = text[len("seeds-") : -len("s-early")]
    try:
        return float(raw)
    except ValueError:
        return None


def _generate_legal_candidates(
    candidate_generator,
    *,
    seed_plan,
    priorities,
    demand,
    options,
):
    """Generate each explicit lead independently so one invalid lead does not abort the sweep."""

    baseline = candidate_generator.generate(
        seed_plan=seed_plan,
        priorities=priorities,
        demands=(demand,),
        options=(),
        baseline_id="demand-aware-0s",
    )
    generated = list(baseline)
    rejected: list[tuple[str, str]] = []

    for option in options:
        try:
            result = candidate_generator.generate(
                seed_plan=seed_plan,
                priorities=priorities,
                demands=(demand,),
                options=(option,),
                baseline_id="demand-aware-0s",
            )
        except ValueError as exc:
            rejected.append((option.option_id, str(exc)))
            continue

        generated.extend(
            candidate for candidate in result if candidate.candidate_id != "demand-aware-0s"
        )

    return tuple(generated), tuple(rejected)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep explicit Budding Seeds early-refresh permissions and report the first realized "
            "schedule/obligation boundary for Xalvakka healer prep."
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
    parser.add_argument("--start-seconds", type=float, default=1.0)
    parser.add_argument("--stop-seconds", type=float, default=8.0)
    parser.add_argument("--step-seconds", type=float, default=0.5)
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

    lead_values = _lead_grid(args.start_seconds, args.stop_seconds, args.step_seconds)
    options = _candidate_options(lead_values)

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
    base_signature = _plan_signature(
        GeneratedRotationCandidate("baseline", base_plan, ())
    )

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

    print("=" * 118)
    print(" PHASE 13 XALVAKKA HEALER ANTICIPATION BOUNDARY DISCOVERY")
    print("=" * 118)
    print(f"Character: {args.character} | Build: {args.build}")
    print(f"Encounter: {guide.name} ({guide.encounter_id}) | Difficulty: {args.difficulty}")
    print(
        f"Explicit Seeds lead sweep: {lead_values[0]:g}s to {lead_values[-1]:g}s "
        f"by {float(args.step_seconds):g}s"
    )
    print(
        "Boundary: this is diagnostic exploration over caller-defined lead values. A discovered "
        "boundary is not automatically promoted into canonical healer strategy."
    )

    for raid_dps in args.raid_dps:
        phase_2, demand, _ = _project_plan(
            raid_dps=float(raid_dps),
            guide=guide,
            difficulty=args.difficulty,
            seed_plan=seed_plan,
            refinement_service=refinement_service,
            priorities=priority_projection.priority_list,
            refresh_leads=options[0].refresh_leads,
            lead_seconds=float(args.lead_seconds),
            window_seconds=float(args.window_seconds),
        )

        generated, rejected = _generate_legal_candidates(
            candidate_generator,
            seed_plan=seed_plan,
            priorities=priority_projection.priority_list,
            demand=demand,
            options=options,
        )

        unique = _dedupe_realized_candidates(
            (
                GeneratedRotationCandidate("baseline", base_plan, ()),
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

        ranking_inputs = []
        lead_by_id: dict[str, float | None] = {}
        first_schedule_change: tuple[float, str] | None = None
        first_eligible_lead: tuple[float, str] | None = None

        for candidate in unique:
            lead = _lead_from_candidate_id(candidate.candidate_id)
            lead_by_id[candidate.candidate_id] = lead
            if lead is not None and _plan_signature(candidate) != base_signature and first_schedule_change is None:
                first_schedule_change = (lead, candidate.candidate_id)

            sustain = (
                base_sustain
                if candidate.candidate_id == "baseline"
                else sustain_service.evaluate(
                    build=build,
                    plan=candidate.plan,
                    resource=ResourceType.MAGICKA,
                )
            )
            card = scorecard_service.compare(
                baseline_plan=base_plan,
                candidate_plan=candidate.plan,
                baseline_sustain=base_sustain,
                candidate_sustain=sustain,
                demands=(demand,),
                demand_requirements=(requirement,),
                reserve_requirements=reserve_requirements,
            )
            if (
                lead is not None
                and card.supplied_obligations_satisfied
                and first_eligible_lead is None
            ):
                first_eligible_lead = (lead, candidate.candidate_id)
            ranking_inputs.append(
                RotationCandidateRankingInput(candidate.candidate_id, card)
            )

        ranked = ranking_service.rank(tuple(ranking_inputs))
        best_eligible = next(
            (
                item
                for item in ranked
                if item.scorecard.supplied_obligations_satisfied
            ),
            None,
        )

        print()
        print("-" * 118)
        print(
            f"{float(raid_dps):,.0f} RAID DPS | 70% at {float(phase_2.time_seconds):.2f}s | "
            f"prep {demand.start_seconds:.2f}-{demand.end_seconds:.2f}s | "
            f"{len(unique)} unique realized schedules"
        )
        if rejected:
            rejected_ids = ", ".join(candidate_id for candidate_id, _ in rejected)
            first_reason = rejected[0][1]
            print(
                f"Rejected by verified recast rule: {rejected_ids}"
            )
            print(f"  rule boundary: {first_reason}")
        if first_schedule_change is None:
            print("First realized schedule change: none in legal supplied sweep")
        else:
            print(
                f"First realized schedule change: {first_schedule_change[0]:g}s early "
                f"({first_schedule_change[1]})"
            )
        if first_eligible_lead is None:
            print("First eligible Seeds lead: none in legal supplied sweep")
        else:
            print(
                f"First eligible Seeds lead: {first_eligible_lead[0]:g}s early "
                f"({first_eligible_lead[1]})"
            )

        print("Unique realized candidates:")
        for item in ranked:
            card = item.scorecard
            coverage = card.demand_coverage[0]
            cast_text = ", ".join(f"{value:g}s" for value in coverage.cast_times) or "none"
            lead = lead_by_id.get(item.candidate_id)
            lead_text = "baseline" if lead is None else f"{lead:g}s"
            reserve_text = ""
            if card.reserve_assessments:
                reserve = card.reserve_assessments[0]
                reserve_text = (
                    f" | entry Mag {reserve.available_before_start:,}/"
                    f"{reserve.requirement.minimum_amount:,}"
                )
            print(
                f"  #{item.rank} {item.candidate_id:19s} | lead {lead_text:8s} | "
                f"{item.tier.value:10s} | prep casts {cast_text:12s} | "
                f"min {card.consequence.minimum_resource_delta:+d} | "
                f"end {card.consequence.ending_resource_delta:+d}{reserve_text}"
            )

        if best_eligible is None:
            print("Best eligible candidate: none in legal supplied sweep")
        else:
            lead = lead_by_id.get(best_eligible.candidate_id)
            lead_text = "baseline" if lead is None else f"{lead:g}s early"
            print(
                f"Best eligible candidate: {best_eligible.candidate_id} ({lead_text})"
            )

    print()
    print(
        "Interpretation: the first schedule-change boundary answers when the lead permission actually "
        "changes the realized rotation. The first eligible boundary answers when that changed rotation "
        "first satisfies the explicit mechanic action obligation. Leads beyond the verified ordinary "
        "refresh span are reported as illegal candidates rather than aborting the entire sweep."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
