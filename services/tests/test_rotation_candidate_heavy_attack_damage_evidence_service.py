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
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.stat_ids import StatId
from services.rotation_candidate_action_damage_evidence_service import (
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import RotationCandidateDDRoleOutputService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_heavy_attack_damage_evidence_service import (
    RotationCandidateHeavyAttackDamageEvidenceService,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
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


def _build(
    weapon_type: WeaponType = WeaponType.FLAME_STAFF,
    *,
    off_hand_type: WeaponType | None = None,
) -> CharacterBuild:
    return CharacterBuild(
        name="Heavy Damage Build",
        character_class=CharacterClass.WARDEN,
        role=Role.DD,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(weapon_type),
            off_hand=None if off_hand_type is None else Weapon(off_hand_type),
            slots=_slots(),
        ),
        back_bar=None,
    )


def _evaluation() -> BuildEvaluation:
    return BuildEvaluation(
        stats=CalculationResult(
            stats={
                StatId.MAX_MAGICKA: StatBreakdown(base=30000.0),
                StatId.MAX_STAMINA: StatBreakdown(base=15000.0),
                StatId.SPELL_DAMAGE: StatBreakdown(base=5000.0),
                StatId.WEAPON_DAMAGE: StatBreakdown(base=4000.0),
                StatId.PHYSICAL_PENETRATION: StatBreakdown(base=0.0),
                StatId.SPELL_PENETRATION: StatBreakdown(base=0.0),
                StatId.CRITICAL_CHANCE: StatBreakdown(base=0.0),
                StatId.CRITICAL_DAMAGE: StatBreakdown(base=0.0),
            }
        ),
        combat_effects=(),
        combat_contributions=(),
    )


def _candidate(action: RotationAction, duration: float = 10.0) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="heavy",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Heavy Damage Build",
            duration_seconds=duration,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _completion(action: RotationAction, *, fully_charged: bool = True, completion=2.0):
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=action.time_seconds,
        action_sequence=action.sequence,
        completion_time_seconds=completion,
        fully_charged=fully_charged,
        verified_base_restore=None,
        source="test completion evidence",
    )


def _evaluate_heavy(build: CharacterBuild) -> float | None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=build,
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action),),
    )
    return service.evaluate_action(candidate=_candidate(action), action=action).damage_value


def test_fully_charged_flame_staff_heavy_uses_existing_uesp_formula() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action),),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.unresolved == ()
    assert result.damage_value == pytest.approx(5892.0)


def test_heavy_damage_does_not_require_restore_amount_when_completion_is_proven() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    evidence = _completion(action)
    assert evidence.verified_base_restore is None
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(evidence,),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.damage_value == pytest.approx(5892.0)
    assert result.unresolved == ()


def test_missing_completion_evidence_fails_closed() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.damage_value is None
    assert "lacks completion/full-charge evidence" in result.unresolved[0]


def test_partial_heavy_does_not_reuse_full_charge_damage_formula() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action, fully_charged=False),),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.damage_value is None
    assert "partial/interrupted" in result.unresolved[0]


def test_heavy_completion_after_plan_horizon_fails_closed() -> None:
    action = RotationAction(9.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action, completion=11.0),),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.damage_value is None
    assert "completes after the rotation plan horizon" in result.unresolved[0]


def test_two_handed_heavy_uses_existing_physical_formula() -> None:
    assert _evaluate_heavy(_build(WeaponType.GREATSWORD)) == pytest.approx(5892.0)


def test_dual_wield_heavy_uses_existing_physical_formula() -> None:
    assert _evaluate_heavy(
        _build(WeaponType.DAGGER, off_hand_type=WeaponType.DAGGER)
    ) == pytest.approx(3928.0)


def test_one_hand_and_shield_heavy_uses_existing_physical_formula() -> None:
    assert _evaluate_heavy(
        _build(WeaponType.SWORD, off_hand_type=WeaponType.SHIELD)
    ) == pytest.approx(5500.0)


def test_bow_remains_explicitly_unresolved_without_canonical_damage_formula() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    service = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(WeaponType.BOW),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action),),
    )

    result = service.evaluate_action(candidate=_candidate(action), action=action)

    assert result.damage_value is None
    assert "canonical heavy-attack damage routing unavailable for bow" in result.unresolved


def test_heavy_attack_dispatches_into_whole_plan_dd_output() -> None:
    action = RotationAction(0.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    candidate = _candidate(action)
    heavy = RotationCandidateHeavyAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(_completion(action),),
    )
    router = RotationCandidateActionDamageEvidenceService(heavy_attack_provider=heavy)

    output = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=router,
    ).evaluate_plan(candidate)

    assert output.unresolved == ()
    assert output.value == pytest.approx(589.2)
