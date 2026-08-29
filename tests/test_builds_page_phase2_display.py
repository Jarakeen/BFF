from models.build_model import ChampionPointEntry, GearSlot, PlayerBuild
from ui.components.builds_page_phase2_display import build_status_rows, weapon_rows


def _slot(set_name: str = "Set A", trait: str = "Divines", weapon_type: str = "") -> GearSlot:
    return GearSlot(Set=set_name, Trait=trait, WeaponType=weapon_type)


def test_weapon_rows_show_explicit_front_and_back_offhands():
    build = PlayerBuild(
        FrontBarWeapon=_slot(weapon_type="Dagger"),
        FrontBarOffHand=_slot(weapon_type="Dagger"),
        BackBarWeapon=_slot(weapon_type="Sword"),
        BackBarOffHand=_slot(weapon_type="Shield"),
    )

    labels = [label for label, _slot_value in weapon_rows(build)]

    assert labels == [
        "Front Main Hand",
        "Front Off Hand",
        "Back Main Hand",
        "Back Off Hand",
    ]


def test_weapon_rows_do_not_invent_offhand_for_two_handed_or_legacy_aggregate_bar():
    build = PlayerBuild(
        FrontBarWeapon=_slot(weapon_type="Inferno Staff"),
        BackBarWeapon=GearSlot(Set="Set B", Set2="Set C", Trait="Precise", WeaponType="Dual Wield"),
    )

    labels = [label for label, _slot_value in weapon_rows(build)]

    assert labels == ["Front Main Hand", "Back Main Hand"]


def test_readiness_denominator_expands_only_for_explicit_one_handed_slots():
    build = PlayerBuild(
        FrontBarWeapon=_slot(weapon_type="Dagger"),
        FrontBarOffHand=_slot(weapon_type="Dagger"),
        BackBarWeapon=_slot(weapon_type="Inferno Staff"),
        ChampionPoints=[ChampionPointEntry(Name="Boundless Vitality", Points="50")],
        FrontBarSkills=["Skill"] * 6,
        BackBarSkills=["Skill"] * 6,
    )
    for entry in build.Armor.values():
        entry["Set"] = "Set A"
        entry["Trait"] = "Divines"
    for slot in (build.Necklace, build.Ring1, build.Ring2):
        slot.Set = "Set A"
        slot.Trait = "Bloodthirsty"

    rows = dict(build_status_rows(build))

    assert rows["Gear Complete"] == "13/13"
    assert rows["Traits"] == "13/13"
    assert rows["Skills"] == "12/12"
    assert rows["Readiness"] == "100%"
