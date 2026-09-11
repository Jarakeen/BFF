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
from minmax.heavy_attack_restoration import HeavyAttackRestorationModifiers
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


def _bar(bar_id: BarId, weapon: WeaponType) -> Bar:
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon),
        off_hand=None,
        slots=_slots(),
    )


def _character_build() -> CharacterBuild:
    return CharacterBuild(
        name="Magrat",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, WeaponType.FROST_STAFF),
        back_bar=_bar(BarId.BACK, WeaponType.RESTORATION_STAFF),
    )


def _saved_build(*, heavy_pieces: int = 0) -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    for index, slot in enumerate(("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")):
        build.Armor[slot]["Weight"] = "Heavy" if index < heavy_pieces else "Light"
    return build


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def _evidence(
    *,
    start: float,
    completion: float,
    sequence: int = 0,
    modifiers: HeavyAttackRestorationModifiers = HeavyAttackRestorationModifiers(),
) -> RotationHeavyAttackCompletionEvidence:
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=start,
        action_sequence=sequence,
        completion_time_seconds=completion,
        fully_charged=True,
        verified_base_restore=None,
        modifiers=modifiers,
        source="reviewed test heavy",
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


class _ReplayService:
    def __init__(self) -> None:
        self.calls = []

    def replay(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(final_projection="replayed")


def test_saved_cycle_of_life_rank_two_composes_with_verified_resto_base() -> None:
    heavy = RotationAction(6.0, 0, RotationActionKind.HEAVY_ATTACK)
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        heavy,
    )
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        replay_service=replay,
        progression_adapter=_ProgressionAdapter(
            CharacterProgression(passive_ranks={"Cycle of Life": 2})
        ),
    )

    result = service.project(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        plan=plan,
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(_evidence(start=6.0, completion=8.0),),
    )

    assert result.is_resolved is True
    assert result.unresolved == ()
    assert len(result.restoration_projection.restoration_events) == 1
    assert result.restoration_projection.restoration_events[0].amount == pytest.approx(
        3267.0 * 1.30
    )


def test_explicit_cycle_modifier_can_fill_unknown_progression_without_double_apply() -> None:
    heavy = RotationAction(6.0, 0, RotationActionKind.HEAVY_ATTACK)
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        heavy,
    )
    service = RotationHeavySustainProjectionService(
        replay_service=_ReplayService(),
        progression_adapter=_ProgressionAdapter(CharacterProgression(passive_ranks={})),
    )

    result = service.project(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        plan=plan,
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(
            _evidence(
                start=6.0,
                completion=8.0,
                modifiers=HeavyAttackRestorationModifiers(
                    restoration_staff_cycle_of_life_percent=0.30,
                ),
            ),
        ),
    )

    assert result.is_resolved is True
    assert result.restoration_projection.restoration_events[0].amount == pytest.approx(
        3267.0 * 1.30
    )


def test_conflicting_cycle_modifier_fails_closed_against_known_progression() -> None:
    heavy = RotationAction(6.0, 0, RotationActionKind.HEAVY_ATTACK)
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        heavy,
    )
    replay = _ReplayService()
    service = RotationHeavySustainProjectionService(
        replay_service=replay,
        progression_adapter=_ProgressionAdapter(
            CharacterProgression(passive_ranks={"Cycle of Life": 1})
        ),
    )

    result = service.project(
        character_build=_character_build(),
        sustain_build=_saved_build(),
        plan=plan,
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(
            _evidence(
                start=6.0,
                completion=8.0,
                modifiers=HeavyAttackRestorationModifiers(
                    restoration_staff_cycle_of_life_percent=0.30,
                ),
            ),
        ),
    )

    assert result.is_resolved is False
    assert result.replay is None
    assert any("contradicts canonical character progression" in item for item in result.unresolved)
    assert replay.calls == []


def test_saved_revitalize_rank_two_scales_frost_restore_by_heavy_pieces() -> None:
    heavy = RotationAction(4.0, 0, RotationActionKind.HEAVY_ATTACK)
    service = RotationHeavySustainProjectionService(
        replay_service=_ReplayService(),
        progression_adapter=_ProgressionAdapter(
            CharacterProgression(passive_ranks={"Revitalize": 2})
        ),
    )

    result = service.project(
        character_build=_character_build(),
        sustain_build=_saved_build(heavy_pieces=2),
        plan=_plan(heavy),
        resource=ResourceType.MAGICKA,
        initial_bar="front",
        completion_evidence=(_evidence(start=4.0, completion=5.2),),
    )

    assert result.is_resolved is True
    assert result.restoration_projection.restoration_events[0].amount == pytest.approx(
        2425.0 * 1.08
    )
