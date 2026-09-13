from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
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
        evidence="below 25% Health",
    )
    return SkillComponentConditionalConsequence(
        skill_rank_id=1,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
        condition=condition,
        maximum_bonus_fraction=None,
        evidence="periodic component activates below 25% Health",
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


def _service(policy):
    semantics = RotationPeriodicTargetHealthSemantics(
        skill_entity_id="execute_dot",
        coefficient_number=1,
        policy=policy,
        source="reviewed timing evidence",
    )
    return RotationPeriodicTargetHealthEligibilityService(
        semantics_service=RotationPeriodicTargetHealthSemanticsService((semantics,)),
    )


def test_snapshot_at_cast_applies_one_reviewed_health_state_to_all_ticks() -> None:
    service = _service(PeriodicTargetHealthTimingPolicy.SNAPSHOT_AT_CAST)

    result = service.evaluate(
        skill_name="Execute Dot",
        coefficient_number=1,
        consequences=(_consequence(),),
        runtime_events=_events(),
        cast_time_seconds=0.0,
        cast_sequence=4,
        snapshot_resolver=lambda time, sequence: _snapshot(time, 0.20),
        target_identity="boss",
    )

    assert result.resolved is True
    assert [row.include for row in result.occurrences] == [True, True, True]


def test_dynamic_at_tick_reads_exact_health_for_each_occurrence() -> None:
    service = _service(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK)
    health = {1.0: 0.50, 2.0: 0.20, 3.0: 0.10}

    result = service.evaluate(
        skill_name="Execute Dot",
        coefficient_number=1,
        consequences=(_consequence(),),
        runtime_events=_events(),
        cast_time_seconds=0.0,
        cast_sequence=0,
        snapshot_resolver=lambda time, sequence: _snapshot(time, health[time]),
        target_identity="boss",
    )

    assert result.resolved is True
    assert [row.include for row in result.occurrences] == [False, True, True]


def test_dynamic_at_tick_fails_closed_when_one_tick_snapshot_is_missing() -> None:
    service = _service(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK)

    def resolve(time, sequence):
        if time == 2.0:
            return None
        return _snapshot(time, 0.20)

    result = service.evaluate(
        skill_name="Execute Dot",
        coefficient_number=1,
        consequences=(_consequence(),),
        runtime_events=_events(),
        cast_time_seconds=0.0,
        cast_sequence=0,
        snapshot_resolver=resolve,
        target_identity="boss",
    )

    assert result.resolved is False
    assert any("tick at 2s" in item for item in result.unresolved)


def test_missing_reviewed_timing_semantics_fail_closed() -> None:
    service = RotationPeriodicTargetHealthEligibilityService(
        semantics_service=RotationPeriodicTargetHealthSemanticsService(),
    )

    result = service.evaluate(
        skill_name="Execute Dot",
        coefficient_number=1,
        consequences=(_consequence(),),
        runtime_events=_events(),
        cast_time_seconds=0.0,
        cast_sequence=0,
        snapshot_resolver=lambda time, sequence: _snapshot(time, 0.20),
        target_identity="boss",
    )

    assert result.resolved is False
    assert result.unresolved == (
        "Execute Dot: coefficient 1 periodic target-Health timing is not source-reviewed",
    )
