from models.build_model import GearSlot, PlayerBuild
from minmax.gear_stat_inputs import GearStatInputResolver


def _counts(build: PlayerBuild, bar: str = "front") -> dict[str, int]:
    return dict(GearStatInputResolver.equipped_set_counts(build, active_bar=bar))


def test_two_slot_weapon_counts_its_set_twice():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Ansuul", WeaponType="Inferno Staff"),
    )

    assert _counts(build) == {"Ansuul": 2}


def test_explicit_dual_wield_counts_each_physical_weapon_once():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Ansuul", Set2="Legacy Noise", WeaponType="Dagger"),
        FrontBarOffHand=GearSlot(Set="Ansuul", WeaponType="Dagger"),
    )

    assert _counts(build) == {"Ansuul": 2}


def test_explicit_sword_and_board_counts_weapon_and_shield_once_each():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Turning Tide", WeaponType="Sword"),
        FrontBarOffHand=GearSlot(Set="Turning Tide", WeaponType="Shield"),
    )

    assert _counts(build) == {"Turning Tide": 2}


def test_explicit_mixed_dual_wield_can_count_two_different_sets():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Set A", WeaponType="Dagger"),
        FrontBarOffHand=GearSlot(Set="Set B", WeaponType="Axe"),
    )

    assert _counts(build) == {"Set A": 1, "Set B": 1}


def test_legacy_aggregate_dual_wield_preserves_set2_as_second_item():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Set A", Set2="Set B", WeaponType="Dual Wield"),
    )

    assert _counts(build) == {"Set A": 1, "Set B": 1}


def test_back_bar_uses_back_bar_weapon_slots_only():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Front", WeaponType="Inferno Staff"),
        BackBarWeapon=GearSlot(Set="Back", WeaponType="Sword"),
        BackBarOffHand=GearSlot(Set="Back", WeaponType="Shield"),
    )

    assert _counts(build, "back") == {"Back": 2}
