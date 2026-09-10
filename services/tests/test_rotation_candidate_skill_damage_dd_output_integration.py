from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_dd_role_output_service import (
    RotationCandidateDDRoleOutputService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)


def _trace(value: float):
    return SimpleNamespace(final_value=value)


def test_direct_skill_damage_flows_into_whole_plan_dd_output() -> None:
    context = SimpleNamespace(
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
    )
    tooltip = SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=101),
        components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
        unresolved=(),
    )

    class Calculator:
        def evaluate_entity_id(self, entity_id, supplied_context):
            assert entity_id == "direct_skill"
            assert supplied_context is context
            return tooltip

    class Components:
        def get_for_skill_rank(self, skill_rank_id):
            assert skill_rank_id == 101
            return (
                SkillComponentClassification(
                    skill_rank_id=101,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.DAMAGE,
                    damage_type="magical",
                    is_dot=False,
                    is_aoe=False,
                    can_crit=False,
                    source="test",
                ),
            )

    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="DD Build",
            duration_seconds=10.0,
            actions=(
                RotationAction(
                    0.0,
                    0,
                    RotationActionKind.SKILL,
                    name="direct_skill",
                    bar="front",
                ),
                RotationAction(
                    5.0,
                    0,
                    RotationActionKind.SKILL,
                    name="direct_skill",
                    bar="front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=context,
        calculator=Calculator(),
        component_repository=Components(),
    )
    output = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=skill_damage,
    )

    evidence = output.evaluate_plan(candidate)

    assert evidence.value == 200.0
    assert evidence.unresolved == ()
