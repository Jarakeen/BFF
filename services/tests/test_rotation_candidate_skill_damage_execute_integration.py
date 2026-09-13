from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.combat_state_snapshot import CombatantSnapshot, CombatStateSnapshot
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="DD Build",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _trace(value: float):
    return SimpleNamespace(final_value=value)


def _context():
    derived = {
        StatId.WEAPON_DAMAGE: _trace(3000.0),
        StatId.SPELL_DAMAGE: _trace(3000.0),
        StatId.PHYSICAL_PENETRATION: _trace(0.0),
        StatId.SPELL_PENETRATION: _trace(0.0),
        StatId.CRITICAL_CHANCE: _trace(0.0),
        StatId.CRITICAL_DAMAGE: _trace(0.0),
    }
    return SimpleNamespace(
        core_state=SimpleNamespace(derived=derived),
        fight_duration=10.0,
        target_resistance=None,
        combat_state=CombatState(),
        dd_exploiter_bonus=0.0,
    )


class _Calculator:
    def evaluate_entity_id(self, entity_id, context):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=101),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            unresolved=(),
        )


class _Components:
    def __init__(self, *, is_dot: bool = False):
        self.row = SkillComponentClassification(
            skill_rank_id=101,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="magical",
            is_dot=is_dot,
            is_aoe=False,
            can_crit=False,
            source="test",
        )

    def get_for_skill_rank(self, skill_rank_id):
        return (self.row,)


class _Consequences:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def resolve(self, skill_rank_id, coefficient_number):
        return self.rows


def _condition(threshold: float = 0.25) -> SkillComponentCondition:
    return SkillComponentCondition(
        skill_rank_id=101,
        coefficient_number=1,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=threshold,
        evidence="below target Health threshold",
    )


def _activation(threshold: float = 0.25) -> SkillComponentConditionalConsequence:
    condition = _condition(threshold)
    return SkillComponentConditionalConsequence(
        skill_rank_id=101,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
        condition=condition,
        maximum_bonus_fraction=None,
        evidence=condition.evidence,
    )


def _amplification(threshold: float = 0.25) -> SkillComponentConditionalConsequence:
    condition = _condition(threshold)
    return SkillComponentConditionalConsequence(
        skill_rank_id=101,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
        condition=condition,
        maximum_bonus_fraction=3.0,
        evidence="up to 300% more damage",
    )


def _snapshot(health_fraction: float) -> CombatStateSnapshot:
    return CombatStateSnapshot(
        time_seconds=2.0,
        player=CombatantSnapshot(
            identity="player",
            current_health=100.0,
            maximum_health=100.0,
        ),
        targets=(
            CombatantSnapshot(
                identity="boss",
                current_health=health_fraction * 100.0,
                maximum_health=100.0,
            ),
        ),
    )


def _action() -> RotationAction:
    return RotationAction(
        2.0,
        3,
        RotationActionKind.SKILL,
        name="execute_skill",
        bar="front",
    )


def _service(*, consequences, snapshot=None, is_dot=False):
    return RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(),
        component_repository=_Components(is_dot=is_dot),
        conditional_consequence_repository=_Consequences(consequences),
        runtime_target_snapshot_resolver=(
            (lambda time_seconds, sequence: snapshot)
            if snapshot is not None
            else None
        ),
        execute_target_identity="boss",
    )


def test_threshold_activation_is_suppressed_above_threshold() -> None:
    evidence = _service(
        consequences=(_activation(),),
        snapshot=_snapshot(0.50),
    ).evaluate_action(candidate=_candidate(), action=_action())

    assert evidence.damage_value == 0.0
    assert evidence.unresolved == ()


def test_threshold_activation_contributes_damage_below_threshold() -> None:
    evidence = _service(
        consequences=(_activation(),),
        snapshot=_snapshot(0.20),
    ).evaluate_action(candidate=_candidate(), action=_action())

    assert evidence.damage_value == 1000.0
    assert evidence.unresolved == ()


def test_threshold_activation_requires_runtime_snapshot() -> None:
    evidence = _service(
        consequences=(_activation(),),
    ).evaluate_action(candidate=_candidate(), action=_action())

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "execute_skill: coefficient 1: target-health conditional damage requires an exact runtime snapshot",
    )


def test_active_continuous_execute_amplification_fails_closed() -> None:
    evidence = _service(
        consequences=(_amplification(),),
        snapshot=_snapshot(0.20),
    ).evaluate_action(candidate=_candidate(), action=_action())

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "execute_skill: coefficient 1: continuous execute interpolation is not source-reviewed",
    )


def test_periodic_target_health_condition_timing_is_not_guessed() -> None:
    evidence = _service(
        consequences=(_activation(),),
        snapshot=_snapshot(0.20),
        is_dot=True,
    ).evaluate_action(candidate=_candidate(), action=_action())

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "execute_skill: coefficient 1 periodic target-health conditional timing is unresolved",
    )
