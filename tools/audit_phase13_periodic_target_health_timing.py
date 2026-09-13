from __future__ import annotations

"""Audit reviewed periodic target-Health timing policies without scheduling guesses."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_condition import SkillComponentCondition, SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from services.rotation_periodic_target_health_eligibility_service import (
    RotationPeriodicTargetHealthEligibilityService,
)
from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemantics,
    RotationPeriodicTargetHealthSemanticsService,
)


def _consequence():
    condition = SkillComponentCondition(
        skill_rank_id=1,
        coefficient_number=1,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=0.25,
        evidence="synthetic reviewed below 25% Health",
    )
    return SkillComponentConditionalConsequence(
        skill_rank_id=1,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
        condition=condition,
        maximum_bonus_fraction=None,
        evidence="synthetic periodic execute activation",
    )


def _snapshot(time_seconds: float, health_fraction: float):
    return CombatStateSnapshot(
        time_seconds=time_seconds,
        player=CombatantSnapshot("player"),
        targets=(
            CombatantSnapshot(
                "boss",
                current_health=health_fraction * 100.0,
                maximum_health=100.0,
            ),
        ),
    )


def _events():
    return tuple(
        RuntimeEvent(time_seconds=value, trigger="damage_dealt", source="Execute Dot")
        for value in (1.0, 2.0, 3.0)
    )


def _evaluate(policy, resolver):
    semantics = RotationPeriodicTargetHealthSemantics(
        skill_entity_id="execute_dot",
        coefficient_number=1,
        policy=policy,
        source="synthetic reviewed timing evidence",
    )
    service = RotationPeriodicTargetHealthEligibilityService(
        semantics_service=RotationPeriodicTargetHealthSemanticsService((semantics,)),
    )
    return service.evaluate(
        skill_name="Execute Dot",
        coefficient_number=1,
        consequences=(_consequence(),),
        runtime_events=_events(),
        cast_time_seconds=0.0,
        cast_sequence=0,
        snapshot_resolver=resolver,
        target_identity="boss",
    )


def main() -> int:
    cast_snapshot = _evaluate(
        PeriodicTargetHealthTimingPolicy.SNAPSHOT_AT_CAST,
        lambda time, sequence: _snapshot(time, 0.20),
    )
    dynamic_health = {1.0: 0.50, 2.0: 0.20, 3.0: 0.10}
    dynamic = _evaluate(
        PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK,
        lambda time, sequence: _snapshot(time, dynamic_health[time]),
    )

    cast_flags = tuple(row.include for row in cast_snapshot.occurrences)
    dynamic_flags = tuple(row.include for row in dynamic.occurrences)
    passed = (
        cast_snapshot.resolved
        and dynamic.resolved
        and cast_flags == (True, True, True)
        and dynamic_flags == (False, True, True)
    )

    print("=" * 72)
    print(" PHASE 13 PERIODIC TARGET-HEALTH TIMING AUDIT")
    print("=" * 72)
    print(f"snapshot_at_cast includes={cast_flags} expected=(True, True, True)")
    print(f"dynamic_at_tick includes={dynamic_flags} expected=(False, True, True)")
    print()
    print(f"RESULT={'PASS' if passed else 'FAIL'}")
    print(
        "Interpretation: periodic target-Health conditions use only an explicitly reviewed "
        "cast-snapshot or exact-tick timing policy; no policy is inferred from DoT cadence."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
