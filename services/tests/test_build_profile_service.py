from __future__ import annotations

from models.build_model import GearSlot, PlayerBuild
from services.build_profile_service import (
    BuildProfile,
    BuildProfileService,
    build_profile_exception_count,
    build_with_effective_item_profile,
    effective_item_profile,
)


def test_missing_profile_resolves_to_endgame_defaults(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")

    profile = service.get("build-1")

    assert profile.quality == "Gold"
    assert profile.item_level == "CP160"
    assert profile.enchantment_tier == "Truly Superb"
    assert profile.favorite is False
    assert profile.archived is False
    assert profile.ownership == "mine"


def test_profile_update_is_additive_and_round_trips(tmp_path) -> None:
    path = tmp_path / "build_profiles.json"
    service = BuildProfileService(path)

    service.update("build-1", favorite=True, ownership="team", source_owner="@friend")
    service.update("build-2", archived=True)

    again = BuildProfileService(path)
    assert again.get("build-1").favorite is True
    assert again.get("build-1").ownership == "team"
    assert again.get("build-1").source_owner == "@friend"
    assert again.get("build-2").archived is True


def test_blank_item_fields_inherit_without_becoming_overrides() -> None:
    effective = effective_item_profile(GearSlot(), BuildProfile())

    assert effective.quality == "Gold"
    assert effective.item_level == "CP160"
    assert effective.enchantment_tier == "Truly Superb"
    assert effective.has_override is False


def test_explicit_matching_values_do_not_count_as_exceptions() -> None:
    item = GearSlot(Quality="Gold", Level="CP160", EnchantTier="Truly Superb")

    effective = effective_item_profile(item, BuildProfile())

    assert effective.has_override is False


def test_only_differing_explicit_values_count_as_exceptions() -> None:
    build = PlayerBuild()
    build.FrontBarWeapon = GearSlot(Quality="Purple", Level="CP160", EnchantTier="Truly Superb")
    build.BackBarWeapon = GearSlot(Quality="Gold", Level="CP150", EnchantTier="Truly Superb")

    assert build_profile_exception_count(build, BuildProfile()) == 2


def test_custom_baseline_changes_effective_resolution_without_mutating_item() -> None:
    item = GearSlot(Quality="Purple")
    profile = BuildProfile(quality="Purple", item_level="Level 35", enchantment_tier="Superior")

    effective = effective_item_profile(item, profile)

    assert effective.quality == "Purple"
    assert effective.item_level == "Level 35"
    assert effective.enchantment_tier == "Superior"
    assert effective.has_override is False
    assert item.Level == ""
    assert item.EnchantTier == ""


def test_calculation_copy_inherits_baseline_only_on_equipped_items() -> None:
    build = PlayerBuild(BuildId="build-1")
    build.Armor["Head"].update(Set="Ozezan the Inferno", Weight="Light")
    build.Armor["Chest"].update(Set="Trial Set", Weight="Medium", Quality="Purple")
    build.Necklace = GearSlot(Set="Jewelry Set", Trait="Bloodthirsty")
    build.FrontBarWeapon = GearSlot(Set="Weapon Set", WeaponType="Restoration Staff")
    profile = BuildProfile(quality="Gold", item_level="CP160", enchantment_tier="Truly Superb")

    calculated = build_with_effective_item_profile(build, profile)

    assert calculated.Armor["Head"]["Quality"] == "Gold"
    assert calculated.Armor["Head"]["Level"] == "CP160"
    assert calculated.Armor["Chest"]["Quality"] == "Purple"
    assert calculated.Necklace.EnchantTier == "Truly Superb"
    assert calculated.FrontBarWeapon.Level == "CP160"
    assert calculated.BackBarWeapon.is_empty
    assert not any(calculated.Armor["Feet"].values())
    assert build.Armor["Head"]["Quality"] == ""
    assert build.Necklace.Level == ""


def test_build_profiles_are_isolated_by_canonical_build_id(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")

    service.update(
        "build-mine",
        favorite=True,
        ownership="mine",
        source_owner="",
    )
    service.update(
        "build-team",
        archived=True,
        ownership="team",
        source_owner="CobblestoneKing",
    )

    mine = service.get("build-mine")
    team = service.get("build-team")

    assert mine.favorite is True
    assert mine.archived is False
    assert mine.ownership == "mine"
    assert mine.source_owner == ""

    assert team.favorite is False
    assert team.archived is True
    assert team.ownership == "team"
    assert team.source_owner == "CobblestoneKing"


def test_build_profile_ownership_update_preserves_other_metadata(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")

    service.update(
        "build-1",
        favorite=True,
        quality="Purple",
        ownership="TEAM",
        source_owner="CobblestoneKing",
    )
    updated = service.update("build-1", ownership="mine", source_owner="")

    assert updated.favorite is True
    assert updated.quality == "Purple"
    assert updated.ownership == "mine"
    assert updated.source_owner == ""


def test_armor_and_jewelry_defaults_round_trip_without_touching_legacy_defaults(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")
    service.update(
        "build-1",
        armor_trait="Divines",
        armor_weight="Medium",
        armor_enchant="Max Magicka",
        jewelry_trait="Bloodthirsty",
        jewelry_enchant="Spell Damage",
    )

    profile = BuildProfileService(tmp_path / "build_profiles.json").get("build-1")

    assert profile.armor_trait == "Divines"
    assert profile.armor_weight == "Medium"
    assert profile.armor_enchant == "Max Magicka"
    assert profile.jewelry_trait == "Bloodthirsty"
    assert profile.jewelry_enchant == "Spell Damage"
    assert profile.quality == "Gold"
    assert profile.item_level == "CP160"
    assert profile.enchantment_tier == "Truly Superb"


def test_calculation_copy_applies_armor_and_jewelry_defaults_only_to_blank_equipped_fields() -> None:
    build = PlayerBuild(BuildId="build-1")
    build.Armor["Head"].update(Set="Monster Set")
    build.Armor["Chest"].update(
        Set="Trial Set", Weight="Heavy", Trait="Reinforced", Enchant="Max Health"
    )
    build.Necklace = GearSlot(Set="Jewelry Set")
    build.Ring1 = GearSlot(Set="Jewelry Set", Trait="Infused", Enchant="Magicka Recovery")
    profile = BuildProfile(
        armor_trait="Divines",
        armor_weight="Medium",
        armor_enchant="Max Magicka",
        jewelry_trait="Bloodthirsty",
        jewelry_enchant="Spell Damage",
    )

    calculated = build_with_effective_item_profile(build, profile)

    assert calculated.Armor["Head"]["Trait"] == "Divines"
    assert calculated.Armor["Head"]["Weight"] == "Medium"
    assert calculated.Armor["Head"]["Enchant"] == "Max Magicka"
    assert calculated.Armor["Chest"]["Trait"] == "Reinforced"
    assert calculated.Armor["Chest"]["Weight"] == "Heavy"
    assert calculated.Armor["Chest"]["Enchant"] == "Max Health"
    assert calculated.Necklace.Trait == "Bloodthirsty"
    assert calculated.Necklace.Enchant == "Spell Damage"
    assert calculated.Ring1.Trait == "Infused"
    assert calculated.Ring1.Enchant == "Magicka Recovery"
    assert build.Armor["Head"]["Trait"] == ""
    assert build.Necklace.Trait == ""


def test_build_profile_pydantic_rejects_unknown_trait(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")

    import pytest
    with pytest.raises(ValueError, match="unknown armor trait"):
        service.update("build-1", armor_trait="Extremely Fashionable")


def test_build_profile_pydantic_rejects_unknown_weight(tmp_path) -> None:
    service = BuildProfileService(tmp_path / "build_profiles.json")

    import pytest
    with pytest.raises(ValueError, match="unknown armor weight"):
        service.update("build-1", armor_weight="Cardboard")
