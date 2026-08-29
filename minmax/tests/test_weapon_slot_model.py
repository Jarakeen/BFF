from models.build_model import ARMOR_TRAITS, GearSlot, PlayerBuild


def test_explicit_weapon_offhands_round_trip_without_breaking_legacy_main_hands():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(Set="Front Set", WeaponType="Dagger", Quality="Gold", Level="CP160"),
        FrontBarOffHand=GearSlot(Set="Front Set", WeaponType="Dagger", Quality="Gold", Level="CP160"),
        BackBarWeapon=GearSlot(Set="Back Set", WeaponType="Sword", Quality="Gold", Level="CP160"),
        BackBarOffHand=GearSlot(Set="Back Set", WeaponType="Shield", Quality="Gold", Level="CP160"),
    )

    restored = PlayerBuild.from_dict(build.to_dict())

    assert restored.FrontBarWeapon.WeaponType == "Dagger"
    assert restored.FrontBarOffHand.WeaponType == "Dagger"
    assert restored.BackBarWeapon.WeaponType == "Sword"
    assert restored.BackBarOffHand.WeaponType == "Shield"


def test_old_saved_builds_default_new_offhand_slots_to_empty():
    restored = PlayerBuild.from_dict(
        {
            "FrontBarWeapon": {"Set": "Old Front", "WeaponType": "Inferno Staff"},
            "BackBarWeapon": {"Set": "Old Back", "WeaponType": "Two-Handed"},
        }
    )

    assert restored.FrontBarWeapon.Set == "Old Front"
    assert restored.BackBarWeapon.Set == "Old Back"
    assert restored.FrontBarOffHand.is_empty
    assert restored.BackBarOffHand.is_empty


def test_active_weapon_slots_select_matching_bar():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Dagger"),
        FrontBarOffHand=GearSlot(WeaponType="Axe"),
        BackBarWeapon=GearSlot(WeaponType="Sword"),
        BackBarOffHand=GearSlot(WeaponType="Shield"),
    )

    front_main, front_off = build.active_weapon_slots("front")
    back_main, back_off = build.active_weapon_slots("back")

    assert (front_main.WeaponType, front_off.WeaponType) == ("Dagger", "Axe")
    assert (back_main.WeaponType, back_off.WeaponType) == ("Sword", "Shield")


def test_current_armor_trait_choices_expose_invigorating_not_legacy_prosperous():
    assert "Invigorating" in ARMOR_TRAITS
    assert "Prosperous" not in ARMOR_TRAITS
