import pytest

from minmax.heavy_attack_restoration import (
    HeavyAttackRestorationModifiers,
    HeavyAttackWeaponType,
    calculate_heavy_attack_restoration,
    create_heavy_attack_restoration_event,
    resource_for_heavy_attack_weapon,
)
from minmax.resource_costs import ResourceType


def test_heavy_attack_weapon_resource_mapping_is_explicit() -> None:
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.BOW) is ResourceType.STAMINA
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.DUAL_WIELD) is ResourceType.STAMINA
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.TWO_HANDED) is ResourceType.STAMINA
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.ONE_HAND_AND_SHIELD) is ResourceType.STAMINA
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.RESTORATION_STAFF) is ResourceType.MAGICKA
    assert resource_for_heavy_attack_weapon(HeavyAttackWeaponType.FIRE_STAFF) is ResourceType.MAGICKA


def test_unverified_heavy_attack_base_restore_is_rejected() -> None:
    with pytest.raises(ValueError, match="not live-verified"):
        calculate_heavy_attack_restoration(
            weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
            verified_base_restore=None,
        )


def test_verified_modifier_structure_is_deterministic() -> None:
    value = calculate_heavy_attack_restoration(
        weapon=HeavyAttackWeaponType.BOW,
        verified_base_restore=2000,
        modifiers=HeavyAttackRestorationModifiers(
            champion_point_percent=0.10,
            skill_set_buff_percent=0.20,
            heavy_armor_revitalize_percent=0.08,
        ),
    )

    assert value == pytest.approx(2000 * 1.10 * 1.28)


def test_cycle_of_life_is_restoration_staff_only() -> None:
    modifiers = HeavyAttackRestorationModifiers(
        restoration_staff_cycle_of_life_percent=0.30,
    )

    assert calculate_heavy_attack_restoration(
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        verified_base_restore=3000,
        modifiers=modifiers,
    ) == pytest.approx(3900)

    with pytest.raises(ValueError, match="requires a Restoration Staff"):
        calculate_heavy_attack_restoration(
            weapon=HeavyAttackWeaponType.SHOCK_STAFF,
            verified_base_restore=3000,
            modifiers=modifiers,
        )


def test_heavy_attack_restore_emits_generic_restoration_event() -> None:
    event = create_heavy_attack_restoration_event(
        time_seconds=4.2,
        weapon=HeavyAttackWeaponType.TWO_HANDED,
        verified_base_restore=2400,
        modifiers=HeavyAttackRestorationModifiers(heavy_armor_revitalize_percent=0.12),
    )

    assert event.time_seconds == 4.2
    assert event.resource is ResourceType.STAMINA
    assert event.amount == pytest.approx(2688)
    assert event.source == "Fully charged heavy attack: two_handed"
