from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.damage_done import DamageDoneModifiers
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from minmax.skill_component_condition import (
    SkillComponentCondition,
    SkillComponentConditionType,
)
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequence,
    SkillComponentConditionalConsequenceType,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageMagnitudePolicy,
)
from services.rotation_candidate_periodic_target_health_damage_bridge_service import (
    RotationCandidatePeriodicTargetHealthDamageBridgeService,
)
from services.rotation_periodic_target_health_eligibility_service import (
    RotationPeriodicTargetHealthEligibilityService,
)
from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemantics,
    RotationPeriodicTargetHealthSemanticsService,
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
        fight_duration=5.0,
        target_resistance=None,
    )


def _action():
    return RotationAction(0.0, 0, RotationActionKind.SKILL, name="Periodic Execute", bar="front")


def _candidate(action):
    return GeneratedRotationCandidate(
        candidate_id="periodic-target-health",
        plan=RotationPlan(
            character_name="Tester",
            build_name="DD",
            duration_seconds=5.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _condition():
    return SkillComponentCondition(
        skill_rank_id=1,
        coefficient_number=1,
        condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
        threshold=0.5,
        evidence="below 50% target Health",
    )


def _consequence():
    return SkillComponentConditionalConsequence(
        skill_rank_id=1,
        coefficient_number=1,
        consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
        condition=_condition(),
        maximum_bonus_fraction=None,
        evidence="periodic execute active below 50% Health",
    )


def _snapshot(time_seconds: float, health_fraction: float):
    return CombatStateSnapshot(
        time_seconds=time_seconds,
        player=CombatantSnapshot(identity="player"),
        targets=(
            CombatantSnapshot(
                identity="boss",
                current_health=health_fraction * 100.0,
                maximum_health=100.0,
            ),
        ),
    )


class _Calculator:
    def evaluate_entity_id(self, entity_id, context):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=1),
            components=(SimpleNamespace(coefficient_number=1, final_value=100.0),),
            unresolved=(),
        )


class _MixedCalculator:
    def evaluate_entity_id(self, entity_id, context):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=1),
            components=(
                SimpleNamespace(coefficient_number=1, final_value=100.0),
                SimpleNamespace(coefficient_number=2, final_value=250.0),
            ),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        return (
            SkillComponentClassification(
                skill_rank_id=1,
                coefficient_number=1,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=True,
                is_aoe=False,
                can_crit=False,
                source="test",
            ),
        )


class _MixedComponents:
    def get_for_skill_rank(self, skill_rank_id):
        return (
            SkillComponentClassification(
                skill_rank_id=1,
                coefficient_number=1,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=True,
                is_aoe=False,
                can_crit=False,
                source="test",
            ),
            SkillComponentClassification(
                skill_rank_id=1,
                coefficient_number=2,
                effect_kind=SkillEffectKind.DAMAGE,
                damage_type="magical",
                is_dot=False,
                is_aoe=False,
                can_crit=False,
                source="test",
            ),
        )


class _Consequences:
    def resolve(self, skill_rank_id, coefficient_number):
        return (_consequence(),) if int(coefficient_number) == 1 else ()


class _Projection:
    def __init__(self, action):
        self.action = action

    def project(self, *, plan, semantics):
        return SimpleNamespace(
            entries=(
                SimpleNamespace(
                    action=self.action,
                    coefficient_number=1,
                    events=(
                        RuntimeEvent(1.0, "damage_dealt", "periodic"),
                        RuntimeEvent(2.0, "damage_dealt", "periodic", sequence=1),
                        RuntimeEvent(3.0, "damage_dealt", "periodic", sequence=2),
                    ),
                    unresolved=(),
                ),
            )
        )


class _Base:
    def __init__(self, action, *, magnitude_policy=PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST):
        self.context = _context()
        self.calculator = _Calculator()
        self.components = _Components()
        self.conditional_consequences = _Consequences()
        self.periodic_runtime_projection_service = _Projection(action)
        self.periodic_runtime_semantics = (SimpleNamespace(),)
        self.semantic = SimpleNamespace(
            magnitude_policy=magnitude_policy,
            successive_hit_multiplier=None,
        )
        self.dynamic_event_times = []

    def evaluate_action(self, *, candidate, action):
        tooltip = self.calculator.evaluate_entity_id(action.name, self.context)
        classifications = {
            row.coefficient_number: row
            for row in self.components.get_for_skill_rank(tooltip.skill.skill_rank_id)
        }
        total = sum(
            float(component.final_value)
            for component in tooltip.components
            if classifications.get(component.coefficient_number) is not None
            and classifications[component.coefficient_number].effect_kind is SkillEffectKind.DAMAGE
        )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=total,
        )

    def _periodic_semantics_for(self, *, action_name, coefficient_number):
        return self.semantic

    def _target_state_for_runtime_event(self, event):
        return None

    @staticmethod
    def _requires_exploiter_target_state(context):
        return False

    @staticmethod
    def _context_for_runtime_event(context, event):
        return context

    @staticmethod
    def _damage_done_for_context(context, target_state):
        return DamageDoneModifiers()

    @staticmethod
    def _resolve_component_damage(**kwargs):
        return 100.0

    @staticmethod
    def _occurrence_multiplier(semantic, occurrence_index):
        return 1.0

    def _resolve_dynamic_periodic_damage(
        self,
        *,
        action,
        coefficient_number,
        classification,
        runtime_events,
        semantic,
    ):
        self.dynamic_event_times.extend(float(event.time_seconds) for event in runtime_events)
        return 150.0 * len(tuple(runtime_events)), ()


def _eligibility(policy):
    return RotationPeriodicTargetHealthEligibilityService(
        semantics_service=RotationPeriodicTargetHealthSemanticsService(
            (
                RotationPeriodicTargetHealthSemantics(
                    skill_entity_id="Periodic Execute",
                    coefficient_number=1,
                    policy=policy,
                    source="reviewed test evidence",
                ),
            )
        )
    )


def test_dynamic_tick_health_counts_only_ticks_where_execute_is_active() -> None:
    action = _action()
    snapshots = {
        1.0: _snapshot(1.0, 0.75),
        2.0: _snapshot(2.0, 0.25),
        3.0: _snapshot(3.0, 0.25),
    }
    bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
        base=_Base(action),
        target_health_eligibility=_eligibility(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK),
        snapshot_resolver=lambda time_seconds, sequence: snapshots.get(float(time_seconds)),
        target_identity="boss",
    )

    evidence = bridge.evaluate_if_supported(candidate=_candidate(action), action=action)

    assert evidence is not None
    assert evidence.damage_value == 200.0
    assert evidence.unresolved == ()


def test_cast_snapshot_health_applies_same_eligibility_to_all_ticks() -> None:
    action = _action()
    bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
        base=_Base(action),
        target_health_eligibility=_eligibility(PeriodicTargetHealthTimingPolicy.SNAPSHOT_AT_CAST),
        snapshot_resolver=lambda time_seconds, sequence: _snapshot(float(time_seconds), 0.25),
        target_identity="boss",
    )

    evidence = bridge.evaluate_if_supported(candidate=_candidate(action), action=action)

    assert evidence is not None
    assert evidence.damage_value == 300.0
    assert evidence.unresolved == ()


def test_missing_dynamic_tick_health_fails_closed() -> None:
    action = _action()
    bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
        base=_Base(action),
        target_health_eligibility=_eligibility(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK),
        snapshot_resolver=lambda time_seconds, sequence: (
            _snapshot(float(time_seconds), 0.25) if float(time_seconds) != 2.0 else None
        ),
        target_identity="boss",
    )

    evidence = bridge.evaluate_if_supported(candidate=_candidate(action), action=action)

    assert evidence is not None
    assert evidence.damage_value is None
    assert any("tick at 2s" in item for item in evidence.unresolved)


def test_dynamic_source_magnitude_uses_canonical_tick_resolver_for_included_ticks_only() -> None:
    action = _action()
    base = _Base(action, magnitude_policy=PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK)
    snapshots = {
        1.0: _snapshot(1.0, 0.75),
        2.0: _snapshot(2.0, 0.25),
        3.0: _snapshot(3.0, 0.25),
    }
    bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
        base=base,
        target_health_eligibility=_eligibility(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK),
        snapshot_resolver=lambda time_seconds, sequence: snapshots.get(float(time_seconds)),
        target_identity="boss",
    )

    evidence = bridge.evaluate_if_supported(candidate=_candidate(action), action=action)

    assert evidence is not None
    assert evidence.damage_value == 300.0
    assert evidence.unresolved == ()
    assert base.dynamic_event_times == [2.0, 3.0]


def test_mixed_damage_skill_composes_other_components_through_canonical_delegate() -> None:
    action = _action()
    base = _Base(action)
    base.calculator = _MixedCalculator()
    base.components = _MixedComponents()
    bridge = RotationCandidatePeriodicTargetHealthDamageBridgeService(
        base=base,
        target_health_eligibility=_eligibility(PeriodicTargetHealthTimingPolicy.DYNAMIC_AT_TICK),
        snapshot_resolver=lambda time_seconds, sequence: _snapshot(float(time_seconds), 0.25),
        target_identity="boss",
    )

    evidence = bridge.evaluate_if_supported(candidate=_candidate(action), action=action)

    assert evidence is not None
    assert evidence.damage_value == 550.0
    assert evidence.unresolved == ()
    assert base.components.get_for_skill_rank(1)[0].effect_kind is SkillEffectKind.DAMAGE
