import pytest

from minmax.character_build.weapon_type import (
    WeaponSkillLine,
    WeaponType,
    resolve_weapon_skill_line,
)


def test_sword_and_shield_is_one_hand_and_shield():
    assert (
        resolve_weapon_skill_line(WeaponType.SWORD, WeaponType.SHIELD)
        == WeaponSkillLine.ONE_HAND_AND_SHIELD
    )


def test_dual_daggers_is_dual_wield():
    assert (
        resolve_weapon_skill_line(WeaponType.DAGGER, WeaponType.AXE)
        == WeaponSkillLine.DUAL_WIELD
    )


def test_greatsword_alone_is_two_handed():
    assert (
        resolve_weapon_skill_line(WeaponType.GREATSWORD)
        == WeaponSkillLine.TWO_HANDED
    )


def test_restoration_staff_alone_is_restoration_staff_line():
    assert (
        resolve_weapon_skill_line(WeaponType.RESTORATION_STAFF)
        == WeaponSkillLine.RESTORATION_STAFF
    )


def test_frost_staff_alone_is_destruction_staff_line():
    assert (
        resolve_weapon_skill_line(WeaponType.FROST_STAFF)
        == WeaponSkillLine.DESTRUCTION_STAFF
    )


def test_bow_alone_is_bow_line():
    assert resolve_weapon_skill_line(WeaponType.BOW) == WeaponSkillLine.BOW


def test_invalid_combination_raises():
    with pytest.raises(ValueError):
        resolve_weapon_skill_line(WeaponType.GREATSWORD, WeaponType.SHIELD)
