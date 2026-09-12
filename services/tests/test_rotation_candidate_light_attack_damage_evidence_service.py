from __future__ import annotations

import pytest

from minmax.build_evaluation import BuildEvaluation
from minmax.calculation import CalculationResult, StatBreakdown
from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.combat_contribution import CombatContribution
from minmax.combat_state import CombatState
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.stat_ids import StatId
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_light_attack_damage_evidence_service import (
    RotationCandidateLightAttackDamageEvidenceService,
)


def _slots() -> tuple[SlottedSkill, ...]:
    return tuple(
        SlottedSkill(
            skill_id=f"dummy_{index}",
            skill_line_id="fighters_guild",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )


def _bar(bar_id: BarId, weapon_type: WeaponType) -> Bar:
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon_type),
        off_hand=None,
        slots=_slots(),
    )


def _build(
    *,
    front: WeaponType = WeaponType.FLAME_STAFF,
    back: WeaponType = WeaponType.FROST_STAFF,
) -> CharacterBuild:
    return CharacterBuild(
        name="LA Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, front),
        back_bar=_bar(BarId.BACK, back),
    )


def _evaluation(*contributions: CombatContribution) -> BuildEvaluation:
    return BuildEvaluation(
        stats=CalculationResult(
            stats={
                StatId.MAX_MAGICKA: StatBreakdown(base=30000.0),
                StatId.MAX_STAMINA: StatBreakdown(base=15000.0),
                StatId.SPELL_DAMAGE: StatBreakdown(base=5000.0),
                StatId.WEAPON_DAMAGE: StatBreakdown(base=4000.0),
            }
        ),
        combat_effects=(),
        combat_contributions=tuple(contributions),
    )


def _exploiter(value: float = 0.04) -> CombatContribution:
    return CombatContribution(
        source="test Exploiter",
        effect_type="conditional_exploiter_damage_done",
        raw_value=value,
        uptime=1.0,
        effective_value=value,
    )


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="LA Build",
            duration_seconds=10.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_flame_staff_light_attack_uses_canonical_weapon_identity_and_formula() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(3465.0)


def test_runtime_major_berserk_applies_once_to_light_attack_formula() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        attacker_combat_state=CombatState(
            in_combat=True,
            active_buffs=("Major Berserk",),
        ),
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(3811.5)


def test_exploiter_applies_to_light_attack_only_when_target_is_off_balance() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    inactive = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(_exploiter()),
        initial_bar="front",
        target_combat_state=CombatState(),
    ).evaluate_action(candidate=candidate, action=light)
    active = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(_exploiter()),
        initial_bar="front",
        target_combat_state=CombatState(active_buffs=("Off Balance",)),
    ).evaluate_action(candidate=candidate, action=light)

    assert inactive.damage_value == pytest.approx(3465.0)
    assert active.damage_value == pytest.approx(3465.0 * 1.04)
    assert inactive.unresolved == ()
    assert active.unresolved == ()


def test_exploiter_light_attack_fails_closed_when_target_state_is_unknown() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    evidence = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(_exploiter()),
        initial_bar="front",
    ).evaluate_action(candidate=_candidate(light), action=light)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "Exploiter requires authoritative target CombatState at light-attack damage time",
    )


def test_bar_swap_routes_later_light_attack_through_frost_staff_formula() -> None:
    swap = RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="back")
    light = RotationAction(1.0, 1, RotationActionKind.LIGHT_ATTACK, bar="back")
    candidate = _candidate(swap, light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(3465.0)


def test_bow_light_attack_uses_preserved_uesp_formula() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(front=WeaponType.BOW),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.unresolved == ()
    assert evidence.damage_value == pytest.approx(3465.0)


def test_two_handed_light_attack_remains_explicitly_unresolved_without_source_formula() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(front=WeaponType.GREATSWORD),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "canonical light-attack damage formula unavailable for greatsword",
    )


def test_unsupported_weapon_family_remains_unresolved_not_zero() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(front=WeaponType.RESTORATION_STAFF),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.damage_value is None
    assert "canonical light-attack damage formula unavailable for restoration_staff" in evidence.unresolved


def test_lightning_staff_remains_unresolved_while_source_formula_uses_ha_dot_semantics() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(front=WeaponType.LIGHTNING_STAFF),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.damage_value is None
    assert "HA, Empower, and DoT modifier buckets" in evidence.unresolved[0]


def test_claimed_bar_mismatch_is_preserved_as_weapon_projection_failure() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="back")
    candidate = _candidate(light)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=light)

    assert evidence.damage_value is None
    assert "plan has front bar active" in evidence.unresolved[0]


def test_non_light_attack_is_not_reinterpreted_by_light_attack_service() -> None:
    skill = RotationAction(0.0, 0, RotationActionKind.SKILL, name="deep_fissure", bar="front")
    candidate = _candidate(skill)
    service = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
    )

    evidence = service.evaluate_action(candidate=candidate, action=skill)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "skill damage requires its dedicated canonical action evaluator",
    )