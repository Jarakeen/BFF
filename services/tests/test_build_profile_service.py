from __future__ import annotations

from models.build_model import GearSlot, PlayerBuild
from services.build_profile_service import (
    BuildProfile,
    BuildProfileService,
    build_profile_exception_count,
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
