from __future__ import annotations

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_heavy_attack_weapon_projection_service import (
    RotationHeavyAttackWeaponProjectionService,
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
    front_main: WeaponType,
    front_off: WeaponType | None = None,
    back_main: WeaponType = WeaponType.RESTORATION_STAFF,
    back_off: WeaponType | None = None,
) -> CharacterBuild:
    return CharacterBuild(
        name="Heavy Projection Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, front_main, front_off),
        back_bar=_bar(BarId.BACK, back_main, back_off),
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Heavy Projection Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _heavy(time: float, sequence: int = 0, *, bar: str | None = None) -> RotationAction:
    return RotationAction(
        time_seconds=time,
        sequence=sequence,
        kind=RotationActionKind.HEAVY_ATTACK,
        bar=bar,
    )


@pytest.mark.parametrize(
    ("main", "off", "expected_weapon", "expected_resource"),
    (
        (WeaponType.BOW, None, HeavyAttackWeaponType.BOW, ResourceType.STAMINA),
        (WeaponType.GREATSWORD, None, HeavyAttackWeaponType.TWO_HANDED, ResourceType.STAMINA),
        (WeaponType.SWORD, WeaponType.SHIELD, HeavyAttackWeaponType.ONE_HAND_AND_SHIELD, ResourceType.STAMINA),
        (WeaponType.DAGGER, WeaponType.AXE, HeavyAttackWeaponType.DUAL_WIELD, ResourceType.STAMINA),
        (WeaponType.FLAME_STAFF, None, HeavyAttackWeaponType.FIRE_STAFF, ResourceType.MAGICKA),
        (WeaponType.FROST_STAFF, None, HeavyAttackWeaponType.FROST_STAFF, ResourceType.MAGICKA),
        (WeaponType.LIGHTNING_STAFF, None, HeavyAttackWeaponType.SHOCK_STAFF, ResourceType.MAGICKA),
        (WeaponType.RESTORATION_STAFF, None, HeavyAttackWeaponType.RESTORATION_STAFF, ResourceType.MAGICKA),
    ),
)
def test_resolves_all_equipped_weapon_heavy_families(
    main: WeaponType,
    off: WeaponType | None,
    expected_weapon: HeavyAttackWeaponType,
    expected_resource: ResourceType,
) -> None:
    projection = RotationHeavyAttackWeaponProjectionService().project(
        build=_build(front_main=main, front_off=off),
        plan=_plan(_heavy(5.0)),
        initial_bar="front",
    )

    assert projection.is_legal is True
    assert projection.violations == ()
    assert projection.unresolved == ()
    assert len(projection.resolutions) == 1
    assert projection.resolutions[0].active_bar == "front"
    assert projection.resolutions[0].weapon is expected_weapon
    assert projection.resolutions[0].resource is expected_resource


def test_same_timestamp_swap_sequence_changes_heavy_weapon_identity() -> None:
    projection = RotationHeavyAttackWeaponProjectionService().project(
        build=_build(
            front_main=WeaponType.FROST_STAFF,
            back_main=WeaponType.RESTORATION_STAFF,
        ),
        plan=_plan(
            RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _heavy(10.0, 1),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is True
    assert projection.resolutions[0].active_bar == "back"
    assert projection.resolutions[0].weapon is HeavyAttackWeaponType.RESTORATION_STAFF


def test_heavy_before_same_timestamp_swap_uses_pre_swap_weapon() -> None:
    projection = RotationHeavyAttackWeaponProjectionService().project(
        build=_build(
            front_main=WeaponType.FROST_STAFF,
            back_main=WeaponType.RESTORATION_STAFF,
        ),
        plan=_plan(
            _heavy(10.0, 0),
            RotationAction(10.0, 1, RotationActionKind.BAR_SWAP, bar="back"),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is True
    assert projection.resolutions[0].active_bar == "front"
    assert projection.resolutions[0].weapon is HeavyAttackWeaponType.FROST_STAFF


def test_explicit_heavy_bar_must_match_reconstructed_active_bar() -> None:
    projection = RotationHeavyAttackWeaponProjectionService().project(
        build=_build(front_main=WeaponType.FROST_STAFF),
        plan=_plan(_heavy(5.0, bar="back")),
        initial_bar="front",
    )

    assert projection.is_legal is False
    assert projection.resolutions == ()
    assert len(projection.violations) == 1
    assert "plan has front bar active" in projection.violations[0].reason


def test_missing_active_build_bar_is_unresolved_not_inferred() -> None:
    build = CharacterBuild(
        name="Heavy Projection Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, WeaponType.RESTORATION_STAFF),
        back_bar=None,
    )
    projection = RotationHeavyAttackWeaponProjectionService().project(
        build=build,
        plan=_plan(
            RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _heavy(2.0, 0),
        ),
        initial_bar="front",
    )

    assert projection.is_legal is False
    assert projection.resolutions == ()
    assert projection.violations == ()
    assert "bar is unavailable on the build" in projection.unresolved[0]


def test_initial_bar_is_explicit() -> None:
    with pytest.raises(ValueError, match="initial_bar must be front or back"):
        RotationHeavyAttackWeaponProjectionService().project(
            build=_build(front_main=WeaponType.RESTORATION_STAFF),
            plan=_plan(_heavy(1.0)),
            initial_bar="",
        )
