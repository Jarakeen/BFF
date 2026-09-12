from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_dd_role_output_service import RotationCandidateDDRoleOutputService
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


def _context(*, tick_value: float | None = None):
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
        tick_value=tick_value,
    )


class _Calculator:
    def __init__(self, components):
        self.components = tuple(components)

    def evaluate_entity_id(self, entity_id, context):
        del entity_id, context
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=101),
            components=self.components,
            unresolved=(),
        )


class _DynamicCalculator:
    def evaluate_entity_id(self, entity_id, context):
        del entity_id
        value = 50.0 if context.tick_value is None else float(context.tick_value)
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=101),
            components=(SimpleNamespace(coefficient_number=1, final_value=value),),
            unresolved=(),
        )


class _Components:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, skill_rank_id):
        assert skill_rank_id == 101
        return self.rows


class _PeriodicProjection:
    def __init__(self, entry):
        self.entry = entry
        self.calls = []

    def project(self, *, plan, semantics):
        self.calls.append((plan, semantics))
        return RotationPeriodicDamageRuntimeProjection(entries=(self.entry,))


class _RuntimeContextResolver:
    def __init__(self, contexts):
        self.contexts = dict(contexts)
        self.calls = []

    def __call__(self, time_seconds, sequence=None):
        self.calls.append((float(time_seconds), sequence))
        context = self.contexts.get(float(time_seconds))
        return SimpleNamespace(
            resolved=context is not None,
            context=context,
            unresolved=() if context is not None else ("runtime context unavailable",),
        )


def _classification(*, number: int, is_dot: bool) -> SkillComponentClassification:
    return SkillComponentClassification(
        skill_rank_id=101,
        coefficient_number=number,
        effect_kind=SkillEffectKind.DAMAGE,
        damage_type="magical",
        is_dot=is_dot,
        is_aoe=False,
        can_crit=False,
        source="test",
    )


def _candidate(action: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="periodic-candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Periodic DD",
            duration_seconds=10.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _entry(action: RotationAction, *, number: int, ticks: tuple[float, ...], unresolved=()):
    return RotationPeriodicDamageRuntimeProjectionEntry(
        action=action,
        coefficient_number=number,
        events=tuple(
            RuntimeEvent(
                time_seconds=time_seconds,
                trigger="damage_dealt",
                source=f"periodic coefficient {number}",
                sequence=index,
            )
            for index, time_seconds in enumerate(ticks)
        ),
        active_end_time_seconds=10.0,
        unresolved=tuple(unresolved),
    )


def _semantics(
    skill: str,
    number: int,
    *,
    magnitude_policy: PeriodicDamageMagnitudePolicy = PeriodicDamageMagnitudePolicy.SNAPSHOT_AT_CAST,
):
    return (
        RotationPeriodicDamageRuntimeSemantics(
            skill_entity_id=skill,
            coefficient_number=number,
            first_tick_offset_seconds=1.0,
            refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
            source="reviewed runtime evidence",
            magnitude_policy=magnitude_policy,
        ),
    )


def test_periodic_runtime_ticks_contribute_to_whole_plan_dd_output() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="periodic_skill",
        bar="front",
    )
    projection = _PeriodicProjection(
        _entry(action, number=1, ticks=(2.0, 4.0, 6.0))
    )
    semantics = _semantics("periodic_skill", 1)
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(
            (SimpleNamespace(coefficient_number=1, final_value=100.0),)
        ),
        component_repository=_Components(
            (_classification(number=1, is_dot=True),)
        ),
        periodic_runtime_projection_service=projection,
        periodic_runtime_semantics=semantics,
    )
    candidate = _candidate(action)

    result = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=skill_damage
    ).evaluate_plan(candidate)

    assert result.unresolved == ()
    assert result.value == 30.0
    assert projection.calls == [(candidate.plan, semantics)]


def test_mixed_direct_and_periodic_components_sum_under_parent_cast() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="mixed_skill",
        bar="front",
    )
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(
            (
                SimpleNamespace(coefficient_number=1, final_value=500.0),
                SimpleNamespace(coefficient_number=2, final_value=100.0),
            )
        ),
        component_repository=_Components(
            (
                _classification(number=1, is_dot=False),
                _classification(number=2, is_dot=True),
            )
        ),
        periodic_runtime_projection_service=_PeriodicProjection(
            _entry(action, number=2, ticks=(1.0, 2.0))
        ),
        periodic_runtime_semantics=_semantics("mixed_skill", 2),
    )

    evidence = skill_damage.evaluate_action(
        candidate=_candidate(action),
        action=action,
    )

    assert evidence.unresolved == ()
    assert evidence.damage_value == 700.0


def test_unresolved_periodic_runtime_entry_keeps_whole_skill_damage_unknown() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="periodic_skill",
        bar="front",
    )
    reason = "periodic refresh semantics unresolved"
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(
            (SimpleNamespace(coefficient_number=1, final_value=100.0),)
        ),
        component_repository=_Components(
            (_classification(number=1, is_dot=True),)
        ),
        periodic_runtime_projection_service=_PeriodicProjection(
            _entry(action, number=1, ticks=(), unresolved=(reason,))
        ),
        periodic_runtime_semantics=_semantics("periodic_skill", 1),
    )

    evidence = skill_damage.evaluate_action(
        candidate=_candidate(action),
        action=action,
    )

    assert evidence.damage_value is None
    assert evidence.unresolved == (reason,)


def test_missing_periodic_magnitude_policy_fails_closed() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="periodic_skill",
        bar="front",
    )
    semantics = (
        RotationPeriodicDamageRuntimeSemantics(
            skill_entity_id="periodic_skill",
            coefficient_number=1,
            first_tick_offset_seconds=1.0,
            refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
            source="reviewed runtime evidence",
        ),
    )
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(
            (SimpleNamespace(coefficient_number=1, final_value=100.0),)
        ),
        component_repository=_Components(
            (_classification(number=1, is_dot=True),)
        ),
        periodic_runtime_projection_service=_PeriodicProjection(
            _entry(action, number=1, ticks=(1.0, 2.0))
        ),
        periodic_runtime_semantics=semantics,
    )

    evidence = skill_damage.evaluate_action(
        candidate=_candidate(action),
        action=action,
    )

    assert evidence.damage_value is None
    assert "periodic magnitude timing policy is unavailable" in evidence.unresolved[0]


def test_dynamic_periodic_magnitude_waits_for_exact_tick_context() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="periodic_skill",
        bar="front",
    )
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(
            (SimpleNamespace(coefficient_number=1, final_value=100.0),)
        ),
        component_repository=_Components(
            (_classification(number=1, is_dot=True),)
        ),
        periodic_runtime_projection_service=_PeriodicProjection(
            _entry(action, number=1, ticks=(1.0, 2.0))
        ),
        periodic_runtime_semantics=_semantics(
            "periodic_skill",
            1,
            magnitude_policy=PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK,
        ),
    )

    evidence = skill_damage.evaluate_action(
        candidate=_candidate(action),
        action=action,
    )

    assert evidence.damage_value is None
    assert "dynamic per-tick magnitude requires exact-time runtime build context projection" in evidence.unresolved[0]


def test_dynamic_periodic_magnitude_recomputes_each_exact_runtime_tick() -> None:
    action = RotationAction(
        0.0,
        0,
        RotationActionKind.SKILL,
        name="periodic_skill",
        bar="front",
    )
    runtime = _RuntimeContextResolver(
        {
            1.0: _context(tick_value=100.0),
            2.0: _context(tick_value=200.0),
        }
    )
    skill_damage = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_DynamicCalculator(),
        component_repository=_Components(
            (_classification(number=1, is_dot=True),)
        ),
        periodic_runtime_projection_service=_PeriodicProjection(
            _entry(action, number=1, ticks=(1.0, 2.0))
        ),
        periodic_runtime_semantics=_semantics(
            "periodic_skill",
            1,
            magnitude_policy=PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK,
        ),
        runtime_build_context_resolver=runtime,
    )

    evidence = skill_damage.evaluate_action(
        candidate=_candidate(action),
        action=action,
    )

    assert evidence.unresolved == ()
    assert evidence.damage_value == 300.0
    assert runtime.calls == [(1.0, None), (2.0, None)]
