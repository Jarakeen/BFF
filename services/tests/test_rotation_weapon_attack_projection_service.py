from __future__ import annotations

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponSkillLine, WeaponType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_weapon_attack_projection_service import (
    RotationWeaponAttackProjectionService,
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


def _bar(bar_id: BarId, main: WeaponType, off: WeaponType | None = None) -> Bar:
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(main),
        off_hand=None if off is None else Weapon(off),
        slots=_slots(),
    )


def _build(
    *,
    front_main: WeaponType = WeaponType.FROST_STAFF,
    front_off: WeaponType | None = None,
    back_main: WeaponType = WeaponType.DAGGER,
    back_off: WeaponType | None = WeaponType.AXE,
) -> CharacterBuild:
    return CharacterBuild(
        name="Weapon Attack Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, front_main, front_off),
        back_bar=_bar(BarId.BACK, back_main, back_off),
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Weapon Attack Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_resolves_light_and_heavy_attacks_from_actual_active_weapon_bar() -> None:
    projection = RotationWeaponAttackProjectionService().project(
        build=_build(),
        plan=_plan(
            RotationAction(5.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(10.0, 1, RotationActionKind.HEAVY_ATTACK, bar="back"),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is True
    assert projection.violations == ()
    assert projection.unresolved == ()
    assert len(projection.resolutions) == 2

    light, heavy = projection.resolutions
    assert light.active_bar == "front"
    assert light.weapon_skill_line is WeaponSkillLine.DESTRUCTION_STAFF
    assert light.main_hand is WeaponType.FROST_STAFF
    assert light.off_hand is WeaponType.NONE

    assert heavy.active_bar == "back"
    assert heavy.weapon_skill_line is WeaponSkillLine.DUAL_WIELD
    assert heavy.main_hand is WeaponType.DAGGER
    assert heavy.off_hand is WeaponType.AXE


def test_same_timestamp_sequence_controls_weapon_attack_identity() -> None:
    projection = RotationWeaponAttackProjectionService().project(
        build=_build(),
        plan=_plan(
            RotationAction(10.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(10.0, 1, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(10.0, 2, RotationActionKind.LIGHT_ATTACK, bar="back"),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is True
    assert tuple(item.active_bar for item in projection.resolutions) == ("front", "back")
    assert tuple(item.weapon_skill_line for item in projection.resolutions) == (
        WeaponSkillLine.DESTRUCTION_STAFF,
        WeaponSkillLine.DUAL_WIELD,
    )


def test_explicit_light_attack_bar_must_match_reconstructed_active_bar() -> None:
    projection = RotationWeaponAttackProjectionService().project(
        build=_build(),
        plan=_plan(
            RotationAction(5.0, 0, RotationActionKind.LIGHT_ATTACK, bar="back"),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is False
    assert projection.resolutions == ()
    assert len(projection.violations) == 1
    assert "plan has front bar active" in projection.violations[0].reason


def test_missing_active_build_bar_remains_unresolved() -> None:
    build = CharacterBuild(
        name="Weapon Attack Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF),
        back_bar=None,
    )
    projection = RotationWeaponAttackProjectionService().project(
        build=build,
        plan=_plan(
            RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is False
    assert projection.resolutions == ()
    assert projection.violations == ()
    assert "bar is unavailable on the build" in projection.unresolved[0]


def test_rotation_action_rejects_invalid_swap_destination_before_weapon_projection() -> None:
    with pytest.raises(ValueError, match="rotation action bar must be 'front' or 'back'"):
        RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="sideways")


def test_initial_bar_is_explicit() -> None:
    with pytest.raises(ValueError, match="initial_bar must be front or back"):
        RotationWeaponAttackProjectionService().project(
            build=_build(),
            plan=_plan(),
            initial_bar="",
        )
