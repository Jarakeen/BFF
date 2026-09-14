from __future__ import annotations

"""Audit whether reviewed Xalvakka add-taunt behavior is ready for hard policy promotion."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_tank_encounter_add_taunt_behavior_service import (
    RotationTankEncounterAddTauntBehaviorService,
)


def audit() -> tuple[str, ...]:
    plan = RotationTankEncounterAddTauntBehaviorService().reviewed_for("xalvakka")
    if plan is None:
        return ("UNRESOLVED: no reviewed Xalvakka empirical add taunt behavior",)

    lines = [
        "PHASE 13 XALVAKKA ADD TAUNT BEHAVIOR READINESS AUDIT",
        f"EVIDENCE_SCOPE={plan.evidence_scope}",
        f"SOURCE_REPORT={plan.source_report}",
        "OBSERVED_TAUNT_SOURCES=" + ",".join(plan.observed_taunt_sources),
    ]
    for actor in plan.actors:
        lines.append(
            f"ACTOR: {actor.actor_name} taunt_coverage={actor.taunted_instances}/{actor.observed_instances} "
            f"({actor.taunt_coverage_fraction * 100:.1f}%) "
            f"acquisition_median={actor.acquisition_lag.median_seconds:.3f}s "
            f"acquisition_range={actor.acquisition_lag.minimum_seconds:.3f}-{actor.acquisition_lag.maximum_seconds:.3f}s "
            f"repeat_median={actor.repeat_taunt_interval.median_seconds:.3f}s "
            f"repeat_range={actor.repeat_taunt_interval.minimum_seconds:.3f}-{actor.repeat_taunt_interval.maximum_seconds:.3f}s"
        )
        lines.append(
            f"  candidate_ranking_context={actor.candidate_ranking_context} "
            f"hard_timing_policy={actor.hard_timing_policy} "
            f"continuous_ownership_proven={actor.continuous_ownership_proven}"
        )

    lines.extend(
        (
            "STATUS=EMPIRICAL_STRATEGY_ONLY",
            "HARD_POLICY_PROMOTION=BLOCKED",
            "BLOCKERS=single report; single observed taunt source; acquisition variance; refresh variance; continuous aggro ownership not proven",
            "NEXT_STEP=add independent report/player evidence and/or lifecycle/threat evidence before promoting exact acquisition or maintenance timing",
        )
    )
    return tuple(lines)


def main() -> int:
    for line in audit():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
