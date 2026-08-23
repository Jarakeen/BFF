from minmax.character_build.bar import Bar
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponSkillLine, WeaponType


def _skill(index: int, is_ultimate: bool = False) -> SlottedSkill:
    return SlottedSkill(
        skill_id=f"skill_{index}",
        skill_line_id="dual_wield",
        is_ultimate=is_ultimate,
    )


def _valid_slots() -> tuple[SlottedSkill, ...]:
    return tuple(_skill(i) for i in range(5)) + (_skill(5, is_ultimate=True),)


def test_front_bar_weapon_skill_line_available():
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=_valid_slots(),
    )
    assert bar.weapon_skill_line == WeaponSkillLine.RESTORATION_STAFF


def test_back_bar_can_carry_a_different_weapon_than_front_bar():
    front = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=_valid_slots(),
    )
    back = Bar(
        bar_id=BarId.BACK,
        main_hand=Weapon(weapon_type=WeaponType.FROST_STAFF),
        off_hand=None,
        slots=_valid_slots(),
    )

    assert front.weapon_skill_line == WeaponSkillLine.RESTORATION_STAFF
    assert back.weapon_skill_line == WeaponSkillLine.DESTRUCTION_STAFF
    assert front.weapon_skill_line != back.weapon_skill_line


def test_valid_bar_has_no_violations():
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=_valid_slots(),
    )
    assert bar.violations() == ()


def test_wrong_slot_count_is_a_violation():
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=tuple(_skill(i) for i in range(4)),
    )
    assert any("exactly 6 slots" in problem for problem in bar.violations())


def test_missing_ultimate_is_a_violation():
    slots = tuple(_skill(i) for i in range(6))  # no ultimate flagged
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=slots,
    )
    assert any("exactly one ultimate" in problem for problem in bar.violations())


def test_two_ultimates_is_a_violation():
    slots = tuple(_skill(i) for i in range(4)) + (
        _skill(4, is_ultimate=True),
        _skill(5, is_ultimate=True),
    )
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=slots,
    )
    assert any("exactly one ultimate" in problem for problem in bar.violations())


def test_ultimate_in_wrong_slot_index_is_a_violation():
    slots = (
        _skill(0, is_ultimate=True),
        _skill(1),
        _skill(2),
        _skill(3),
        _skill(4),
        _skill(5),
    )
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.DAGGER),
        off_hand=Weapon(weapon_type=WeaponType.AXE),
        slots=slots,
    )
    assert any("ultimate must occupy" in problem for problem in bar.violations())


def test_invalid_weapon_combination_is_a_violation():
    bar = Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(weapon_type=WeaponType.GREATSWORD),
        off_hand=Weapon(weapon_type=WeaponType.SHIELD),
        slots=_valid_slots(),
    )
    assert len(bar.violations()) > 0
