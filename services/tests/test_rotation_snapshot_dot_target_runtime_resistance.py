from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
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


def _trace(value: float):
    return SimpleNamespace(final_value=value)


@dataclass(frozen=True)
class _Context:
    core_state: object
    fight_duration: float
    target_resistance: float | None
    combat_state: CombatState


def _context():
    return _Context(
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
        target_resistance=18200.0,
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
                    events=(
                        RuntimeEvent(
                            time_seconds=1.0,
                            trigger="damage_dealt",
                            source="snapshot tick",
                            sequence=0,
                        ),
                        RuntimeEvent(
                            time_seconds=2.0,
                            trigger="damage_dealt",
                            source="snapshot tick",
                            sequence=1,
                        ),
                    ),
                    active_end_time_seconds=10.0,
                    unresolved=(),
                ),
            )
        )


def test_snapshot_dot_re_resolves_target_resistance_per_tick() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="snapshot_periodic_skill",
        bar="front",
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="snapshot-target-resistance",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Snapshot Target Resistance",
            duration_seconds=10.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    resistance_calls = []

    def target_resistance(time_seconds, sequence=None):
        resistance_calls.append((float(time_seconds), sequence))
        return 0.0 if float(time_seconds) == 1.0 else 18200.0

    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(),
        component_repository=_Components(),
        periodic_runtime_projection_service=_Projection(action),
        periodic_runtime_semantics=(
            RotationPeriodicDamageRuntimeSemantics(
                skill_entity_id="snapshot_periodic_skill",
                coefficient_number=1,
                first_tick_offset_seconds=1.0,
                refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
                source="reviewed runtime evidence",
                magnitude_policy=PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
            ),
        ),
        runtime_target_resistance_resolver=target_resistance,
    )

    evidence = service.evaluate_action(candidate=candidate, action=action)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(163.6)
    assert resistance_calls == [(1.0, None), (2.0, None)]
