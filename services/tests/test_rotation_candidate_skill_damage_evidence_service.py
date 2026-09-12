from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_skill_damage_evidence_service import (
    RotationCandidateSkillDamageEvidenceService,
)
from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
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


def _context(*, target_resistance=None, combat_state=None, dd_exploiter_bonus=0.0):
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
        target_resistance=target_resistance,
        combat_state=combat_state or CombatState(),
        dd_exploiter_bonus=float(dd_exploiter_bonus),
    )


class _Calculator:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def evaluate_entity_id(self, entity_id, context):
        self.calls.append((entity_id, context))
        return self.result


class _Components:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.calls = []

    def get_for_skill_rank(self, skill_rank_id):
        self.calls.append(skill_rank_id)
        return self.rows


def _tooltip(*, components, unresolved=(), skill_rank_id=101):
    skill = None if skill_rank_id is None else SimpleNamespace(skill_rank_id=skill_rank_id)
    return SimpleNamespace(skill=skill, components=tuple(components), unresolved=tuple(unresolved))


def _component(
    *,
    number=1,
    kind=SkillEffectKind.DAMAGE,
    damage_type="magical",
    is_dot=False,
    is_aoe=False,
    can_crit=False,
):
    return SkillComponentClassification(
        skill_rank_id=101,
        coefficient_number=number,
        effect_kind=kind,
        damage_type=damage_type if kind is SkillEffectKind.DAMAGE else None,
        is_dot=is_dot if kind is SkillEffectKind.DAMAGE else None,
        is_aoe=is_aoe if kind is SkillEffectKind.DAMAGE else None,
        can_crit=can_crit if kind is SkillEffectKind.DAMAGE else None,
        source="test",
    )


def test_default_component_repository_uses_reviewed_dd_overlay() -> None:
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(_tooltip(components=())),
    )

    assert isinstance(service.components, RotationDDReviewedSkillComponentRepository)


def test_direct_skill_action_uses_canonical_entity_and_combat_damage_path() -> None:
    context = _context()
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
    )
    components = _Components((_component(),))
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=context,
        calculator=calculator,
        component_repository=components,
    )
    action = RotationAction(
        2.0,
        3,
        RotationActionKind.SKILL,
        name="deep_fissure",
        bar="front",
    )

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert calculator.calls == [("deep_fissure", context)]
    assert components.calls == [101]
    assert evidence.time_seconds == 2.0
    assert evidence.sequence == 3
    assert evidence.damage_value == 1000.0
    assert evidence.unresolved == ()


def test_direct_skill_exploiter_applies_only_to_explicit_off_balance_state() -> None:
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
    )
    action = RotationAction(2.0, 3, RotationActionKind.SKILL, name="skill_x", bar="front")

    inactive = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(dd_exploiter_bonus=0.04),
        calculator=calculator,
        component_repository=_Components((_component(),)),
        target_combat_state=CombatState(),
    ).evaluate_action(candidate=_candidate(), action=action)
    active = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(dd_exploiter_bonus=0.04),
        calculator=calculator,
        component_repository=_Components((_component(),)),
        target_combat_state=CombatState(active_buffs=("Off Balance",)),
    ).evaluate_action(candidate=_candidate(), action=action)

    assert inactive.damage_value == 1000.0
    assert active.damage_value == 1040.0
    assert inactive.unresolved == ()
    assert active.unresolved == ()


def test_direct_skill_exploiter_fails_closed_when_target_state_is_unknown() -> None:
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(dd_exploiter_bonus=0.04),
        calculator=_Calculator(
            _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
        ),
        component_repository=_Components((_component(),)),
    )
    action = RotationAction(2.0, 3, RotationActionKind.SKILL, name="skill_x", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "Exploiter requires authoritative target CombatState at skill damage time",
    )


def test_direct_skill_action_applies_existing_target_mitigation() -> None:
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(target_resistance=18200.0),
        calculator=calculator,
        component_repository=_Components((_component(),)),
    )
    action = RotationAction(0.0, 0, RotationActionKind.SKILL, name="skill_x", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is not None
    assert 0.0 < evidence.damage_value < 1000.0
    assert evidence.unresolved == ()


def test_periodic_component_fails_closed_until_runtime_tick_projection_exists() -> None:
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=6000.0),))
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=calculator,
        component_repository=_Components((_component(is_dot=True),)),
    )
    action = RotationAction(0.0, 0, RotationActionKind.SKILL, name="damage_over_time", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is None
    assert "periodic damage requires horizon-aware runtime tick projection" in evidence.unresolved[0]


def test_unknown_component_identity_is_not_treated_as_zero_damage() -> None:
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=calculator,
        component_repository=_Components(
            (
                SkillComponentClassification(
                    skill_rank_id=101,
                    coefficient_number=1,
                    effect_kind=SkillEffectKind.UNKNOWN,
                    source="test",
                ),
            )
        ),
    )
    action = RotationAction(0.0, 0, RotationActionKind.SKILL, name="skill_x", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is None
    assert "effect kind unresolved" in evidence.unresolved[0]


def test_verified_non_damage_skill_contributes_zero_direct_damage() -> None:
    calculator = _Calculator(
        _tooltip(components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),))
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=calculator,
        component_repository=_Components((_component(kind=SkillEffectKind.HEAL),)),
    )
    action = RotationAction(0.0, 0, RotationActionKind.SKILL, name="healing_skill", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value == 0.0
    assert evidence.unresolved == ()


def test_unresolved_canonical_skill_identity_propagates() -> None:
    calculator = _Calculator(
        _tooltip(
            components=(),
            unresolved=("Ability entity ID not found: missing_skill",),
            skill_rank_id=None,
        )
    )
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=calculator,
        component_repository=_Components(()),
    )
    action = RotationAction(0.0, 0, RotationActionKind.SKILL, name="missing_skill", bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is None
    assert evidence.unresolved == ("Ability entity ID not found: missing_skill",)


def test_skill_provider_refuses_to_guess_weapon_attack_damage() -> None:
    service = RotationCandidateSkillDamageEvidenceService(
        database_path="unused-test.db",
        context=_context(),
        calculator=_Calculator(_tooltip(components=())),
        component_repository=_Components(()),
    )
    action = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")

    evidence = service.evaluate_action(candidate=_candidate(), action=action)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "light_attack damage requires its dedicated canonical action evaluator",
    )
