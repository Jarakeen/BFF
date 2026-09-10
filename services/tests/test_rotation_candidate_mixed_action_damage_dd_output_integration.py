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
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.stat_ids import StatId
from services.rotation_candidate_action_damage_evidence_service import (
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidence,
    RotationCandidateDDRoleOutputService,
)
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


def _build() -> CharacterBuild:
    return CharacterBuild(
        name="Mixed Damage Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FLAME_STAFF),
            off_hand=None,
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
            }
        ),
        combat_effects=(),
        combat_contributions=(),
    )


class _SkillProvider:
    def __init__(self, damage: float = 1000.0) -> None:
        self.damage = damage
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=self.damage,
        )


def test_same_cycle_light_attack_and_skill_both_contribute_to_whole_plan_dd_output() -> None:
    light = RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front")
    skill = RotationAction(
        0.0,
        1,
        RotationActionKind.SKILL,
        name="deep_fissure",
        bar="front",
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="woven",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Mixed Damage Build",
            duration_seconds=10.0,
            actions=(light, skill),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    skill_provider = _SkillProvider(1000.0)
    light_provider = RotationCandidateLightAttackDamageEvidenceService(
        build=_build(),
        evaluation=_evaluation(),
        initial_bar="front",
    )
    router = RotationCandidateActionDamageEvidenceService(
        skill_provider=skill_provider,
        light_attack_provider=light_provider,
    )
    output = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=router,
    ).evaluate_plan(candidate)

    assert output.unresolved == ()
    assert output.value == pytest.approx((3465.0 + 1000.0) / 10.0)
    assert [call[1] for call in skill_provider.calls] == [skill]


def test_missing_action_kind_provider_fails_closed_in_dispatcher() -> None:
    heavy = RotationAction(2.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front")
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Mixed Damage Build",
            duration_seconds=10.0,
            actions=(heavy,),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    router = RotationCandidateActionDamageEvidenceService()

    evidence = router.evaluate_action(candidate=candidate, action=heavy)

    assert evidence.damage_value is None
    assert evidence.unresolved == (
        "heavy_attack damage consequence has no canonical evaluator configured",
    )
