from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_conditional_output_service import (
    RotationCandidatePeriodicDamageConditionalOutputService,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
    RotationPeriodicDamageRuntimeProjection,
    RotationPeriodicDamageRuntimeProjectionEntry,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
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
    )


class _Calculator:
    def evaluate_entity_id(self, entity_id, context):
        del entity_id, context
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=101),
            components=(SimpleNamespace(coefficient_number=1, final_value=100.0),),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        assert skill_rank_id == 101
        return (
            SkillComponentClassification(
                skill_rank_id=101,
                coefficient_number=1,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=True,
                is_aoe=False,
                can_crit=False,
                source="test",
            ),
        )


class _Projection:
    def __init__(self, action):
        self.action = action

    def project(self, *, plan, semantics):
        del plan, semantics
        return RotationPeriodicDamageRuntimeProjection(
            entries=(
                RotationPeriodicDamageRuntimeProjectionEntry(
                    action=self.action,
                    coefficient_number=1,
                    events=tuple(
                        RuntimeEvent(
                            time_seconds=time_seconds,
                            trigger="damage_dealt",
                            source="periodic coefficient 1",
                            sequence=index,
                        )
                        for index, time_seconds in enumerate((1.0, 2.0, 3.0))
                    ),
                    active_end_time_seconds=10.0,
                ),
            ),
        )


def _candidate(action):
    return GeneratedRotationCandidate(
        candidate_id="conditional-periodic-candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Conditional DD",
            duration_seconds=10.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _semantics():
    return (
        RotationPeriodicDamageRuntimeSemantics(
            skill_entity_id="conditional_periodic_skill",
            coefficient_number=1,
            first_tick_offset_seconds=1.0,
            refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
            source="synthetic integration fixture",
            magnitude_policy=PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
        ),
    )


def _eligibility_service():
    return RotationRuntimeOutputEligibilityService(
        rules=(
            RotationRuntimeOutputConditionRule(
                skill_entity_id="conditional_periodic_skill",
                coefficient_number=1,
                eligibility=RuntimeOutputEligibilityRule(
                    required_conditions=("target_in_test_geometry",),
                    source="synthetic integration fixture",
                ),
            ),
        )
    )


def _skill_damage(action, resolver):
    projection = RotationCandidatePeriodicDamageConditionalOutputService(
        _Projection(action),
        output_eligibility_service=_eligibility_service(),
        condition_context_resolver=resolver,
    )
    return RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(),
        component_repository=_Components(),
        periodic_runtime_projection_service=projection,
        periodic_runtime_semantics=_semantics(),
    )


def test_dd_damage_consumer_uses_only_exact_events_that_are_condition_eligible() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="conditional_periodic_skill",
        bar="front",
    )
    contexts = {
        1.0: frozenset({"target_in_test_geometry"}),
        2.0: frozenset(),
        3.0: frozenset({"target_in_test_geometry"}),
    }

    evidence = _skill_damage(
        action,
        lambda event: contexts[float(event.time_seconds)],
    ).evaluate_action(candidate=_candidate(action), action=action)

    assert evidence.unresolved == ()
    assert evidence.damage_value == 200.0


def test_dd_damage_consumer_preserves_missing_condition_context_as_unresolved() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="conditional_periodic_skill",
        bar="front",
    )

    evidence = _skill_damage(
        action,
        lambda event: (
            frozenset({"target_in_test_geometry"})
            if float(event.time_seconds) != 2.0
            else None
        ),
    ).evaluate_action(candidate=_candidate(action), action=action)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "conditional_periodic_skill coefficient 1 at 2s: runtime output eligibility requires authoritative ConditionContext for target_in_test_geometry",
    )
