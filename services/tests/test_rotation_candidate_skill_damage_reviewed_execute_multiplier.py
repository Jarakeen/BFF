from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.combat_state_snapshot import CombatantSnapshot, CombatStateSnapshot
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from minmax.skill_component_condition import SkillComponentCondition, SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)


def _trace(value: float):
    return SimpleNamespace(final_value=value)


def _context():
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.WEAPON_DAMAGE: _trace(3000.0),
                StatId.SPELL_DAMAGE: _trace(3000.0),
                StatId.PHYSICAL_PENETRATION: _trace(0.0),
                StatId.SPELL_PENETRATION: _trace(0.0),
                StatId.CRITICAL_CHANCE: _trace(0.0),
                StatId.CRITICAL_DAMAGE: _trace(0.0),
            }
        ),
        fight_duration=10.0,
        target_resistance=None,
        combat_state=CombatState(),
        dd_exploiter_bonus=0.0,
    )


class _Calculator:
    def evaluate_entity_id(self, entity_id, context):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=202),
            components=(
                SimpleNamespace(coefficient_number=1, final_value=1000.0),
                SimpleNamespace(coefficient_number=2, final_value=500.0),
            ),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        return tuple(
            SkillComponentClassification(
                skill_rank_id=202,
                coefficient_number=number,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=False,
                is_aoe=False,
                can_crit=False,
                source="test",
            )
            for number in (1, 2)
        )


class _Consequences:
    def __init__(self, rows_by_coefficient):
        self.rows_by_coefficient = dict(rows_by_coefficient)

    def resolve(self, skill_rank_id, coefficient_number):
        return tuple(self.rows_by_coefficient.get(coefficient_number, ()))


def _amplification():
    condition = SkillComponentCondition(
        skill_rank_id=202,
        coefficient_number=1,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=0.50,
        evidence="below 50% target Health",
    )
    return SkillComponentConditionalConsequence(
        skill_rank_id=202,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
        condition=condition,
        maximum_bonus_fraction=4.0,
        evidence="up to 400% more damage",
    )


def _snapshot(health_fraction: float):
    return CombatStateSnapshot(
        time_seconds=2.0,
        player=CombatantSnapshot("player", current_health=100.0, maximum_health=100.0),
        targets=(
            CombatantSnapshot(
                "boss",
                current_health=health_fraction * 100.0,
                maximum_health=100.0,
            ),
        ),
    )


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Tester",
            build_name="DD",
            duration_seconds=10.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _evaluate(skill_name: str, health_fraction: float):
    snapshot = _snapshot(health_fraction)
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(),
        component_repository=_Components(),
        conditional_consequence_repository=_Consequences({1: (_amplification(),)}),
        runtime_target_snapshot_resolver=lambda time_seconds, sequence: snapshot,
        execute_target_identity="boss",
    )
    action = RotationAction(
        2.0,
        0,
        RotationActionKind.SKILL,
        name=skill_name,
        bar="front",
    )
    return service.evaluate_action(candidate=_candidate(), action=action)


def test_reviewed_execute_multiplier_applies_only_to_owning_component() -> None:
    evidence = _evaluate("Killer's Blade", 0.25)

    # At 25% Health, reviewed Killer's Blade scaling is x3 on coefficient 1.
    # Coefficient 2 is unconditional and must remain x1.
    assert evidence.damage_value == 3500.0
    assert evidence.unresolved == ()


def test_reviewed_execute_above_threshold_keeps_both_components_at_base_damage() -> None:
    evidence = _evaluate("Killer's Blade", 0.75)

    assert evidence.damage_value == 1500.0
    assert evidence.unresolved == ()


def test_unreviewed_execute_does_not_inherit_killers_blade_multiplier() -> None:
    evidence = _evaluate("Executioner", 0.25)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "Executioner: coefficient 1: continuous execute interpolation is not source-reviewed",
    )
