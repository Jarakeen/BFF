from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_component_damage_eligibility_service import (
    RotationExecuteComponentDamageEligibilityService,
    RotationExecuteComponentDamageStatus,
)


def _condition(threshold=0.25):
    return SkillComponentCondition(
        skill_rank_id=10,
        coefficient_number=2,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=threshold,
        evidence="below 25% target Health",
    )


def _consequence(kind, *, threshold=0.25, maximum_bonus_fraction=None):
    return SkillComponentConditionalConsequence(
        skill_rank_id=10,
        coefficient_number=2,
        consequence_type=kind,
        condition=_condition(threshold),
        maximum_bonus_fraction=maximum_bonus_fraction,
        evidence="reviewed execute evidence",
    )


def _snapshot(current_health):
    return CombatStateSnapshot(
        time_seconds=8.0,
        player=CombatantSnapshot(
            "player",
            current_health=100.0,
            maximum_health=100.0,
        ),
        targets=(
            CombatantSnapshot(
                "boss",
                current_health=current_health,
                maximum_health=100.0,
            ),
        ),
    )


def test_unconditional_component_is_included_without_runtime_health() -> None:
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Ordinary Skill",
        coefficient_number=1,
        consequences=(),
        snapshot=None,
        target_identity="",
    )

    assert result.status is RotationExecuteComponentDamageStatus.INCLUDE
    assert result.unresolved == ()


def test_threshold_activation_suppresses_component_above_threshold() -> None:
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Execute Skill",
        coefficient_number=2,
        consequences=(
            _consequence(SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT),
        ),
        snapshot=_snapshot(30.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteComponentDamageStatus.SUPPRESS
    assert result.unresolved == ()


def test_threshold_activation_includes_component_below_threshold() -> None:
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Execute Skill",
        coefficient_number=2,
        consequences=(
            _consequence(SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT),
        ),
        snapshot=_snapshot(20.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteComponentDamageStatus.INCLUDE
    assert result.unresolved == ()


def test_active_damage_amplification_fails_closed_without_interpolation() -> None:
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Scaling Execute",
        coefficient_number=2,
        consequences=(
            _consequence(
                SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                maximum_bonus_fraction=4.0,
            ),
        ),
        snapshot=_snapshot(20.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteComponentDamageStatus.UNKNOWN
    assert result.unresolved == (
        "Scaling Execute: coefficient 2: target-health damage amplification is active but exact interpolation is unresolved",
    )


def test_inactive_damage_amplification_keeps_base_component() -> None:
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Scaling Execute",
        coefficient_number=2,
        consequences=(
            _consequence(
                SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                maximum_bonus_fraction=4.0,
            ),
        ),
        snapshot=_snapshot(80.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteComponentDamageStatus.INCLUDE
    assert result.unresolved == ()


def test_conditional_component_fails_closed_when_target_health_is_unknown() -> None:
    snapshot = CombatStateSnapshot(
        time_seconds=8.0,
        player=CombatantSnapshot("player", current_health=100.0, maximum_health=100.0),
        targets=(CombatantSnapshot("boss"),),
    )
    result = RotationExecuteComponentDamageEligibilityService().resolve(
        skill_name="Execute Skill",
        coefficient_number=2,
        consequences=(
            _consequence(SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT),
        ),
        snapshot=snapshot,
        target_identity="boss",
    )

    assert result.status is RotationExecuteComponentDamageStatus.UNKNOWN
    assert "Health is unknown" in result.unresolved[0]
