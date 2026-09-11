from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.character_progression import CharacterProgression
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
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


def _character_build() -> CharacterBuild:
    return CharacterBuild(
        name="Magrat",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF),
        back_bar=_bar(BarId.BACK, WeaponType.FROST_STAFF),
    )


def _saved_build() -> PlayerBuild:
    return PlayerBuild(Name="Magrat", BuildName="DF Healer")


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar="front",
            ),
        ),
    )


def _evidence() -> tuple[RotationHeavyAttackCompletionEvidence, ...]:
    return (
        RotationHeavyAttackCompletionEvidence(
            action_time_seconds=2.0,
            action_sequence=0,
            completion_time_seconds=3.6,
            fully_charged=True,
            verified_base_restore=None,
            source="reviewed test heavy",
        ),
    )


class _ProgressionAdapter:
    def __init__(self, progression: CharacterProgression) -> None:
        self.progression = progression

    def resolve(self, _build):
        return SimpleNamespace(
            character_id="magrat",
            progression=self.progression,
            unresolved=(),
            resolved=True,
        )


def test_plan_resolver_uses_verified_resto_base_and_saved_cycle_of_life() -> None:
    service = RotationHeavySustainProjectionService(
        progression_adapter=_ProgressionAdapter(
            CharacterProgression(passive_ranks={"Cycle of Life": 2})
        )
    )
    plan = _plan()
    resolver = service.restoration_resolver_for_plan(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        plan=plan,
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=_evidence(),
    )

    event = resolver(plan.actions[0])
    assert event is not None
    assert event.amount == pytest.approx(3267.0 * 1.30)
    assert event.time_seconds == pytest.approx(3.6)
    assert event.resource is ResourceType.MAGICKA


def test_plan_resolver_fails_closed_when_saved_cycle_of_life_is_unknown() -> None:
    service = RotationHeavySustainProjectionService(
        progression_adapter=_ProgressionAdapter(CharacterProgression(passive_ranks={}))
    )

    with pytest.raises(ValueError, match="Cycle of Life rank is unknown"):
        service.restoration_resolver_for_plan(
            character_build=_character_build(),
            sustain_build=_saved_build(),
            plan=_plan(),
            resource=ResourceType.MAGICKA,
            initial_bar="front",
            completion_evidence=_evidence(),
        )
