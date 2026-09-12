from models.build_model import BuildRoster, GearSlot, PlayerBuild
from services.build_gear_enchantment_compatibility_service import (
    BuildGearEnchantmentCompatibilityService,
)


def test_truly_superb_slot_canonicalizes_lower_saved_level_to_cp160() -> None:
    slot = GearSlot(
        Set="Test Set",
        Trait="Infused",
        Enchant="Weapon Damage",
        EnchantTier="Truly Superb",
        Level="CP70",
    )

    normalized = BuildGearEnchantmentCompatibilityService.normalize_slot(slot)

    assert normalized.Level == "CP160"
    assert normalized.EnchantTier == "Truly Superb"
    assert normalized.Enchant == "Weapon Damage"
    assert slot.Level == "CP70"


def test_non_truly_superb_slot_is_not_reinterpreted() -> None:
    slot = GearSlot(
        Enchant="Weapon Damage",
        EnchantTier="Grand",
        Level="CP70",
    )

    normalized = BuildGearEnchantmentCompatibilityService.normalize_slot(slot)

    assert normalized is slot
    assert normalized.Level == "CP70"
    assert normalized.EnchantTier == "Grand"


def test_build_normalization_covers_armor_and_jewelry_without_mutating_source() -> None:
    build = PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        Armor={
            "Head": {
                "Set": "Test Set",
                "Enchant": "Max Magicka",
                "EnchantTier": "Truly Superb",
                "Level": "CP30",
            }
        },
        Ring2=GearSlot(
            Set="Test Set",
            Trait="Bloodthirsty",
            Enchant="Weapon Damage",
            EnchantTier="Truly Superb",
            Level="CP70",
        ),
    )

    normalized = BuildGearEnchantmentCompatibilityService.normalize_build(build)

    assert normalized.Ring2.Level == "CP160"
    assert normalized.Armor["Head"]["Level"] == "CP160"
    assert build.Ring2.Level == "CP70"
    assert build.Armor["Head"]["Level"] == "CP30"


def test_roster_normalization_preserves_member_count_and_identity() -> None:
    roster = BuildRoster(
        Members=[
            PlayerBuild(
                Name="Rylonia",
                BuildName="Corpsebuster DD",
                Ring2=GearSlot(
                    Enchant="Weapon Damage",
                    EnchantTier="Truly Superb",
                    Level="CP70",
                ),
            )
        ]
    )

    normalized = BuildGearEnchantmentCompatibilityService.normalize_roster(roster)

    assert len(normalized.Members) == 1
    assert normalized.Members[0].Name == "Rylonia"
    assert normalized.Members[0].BuildName == "Corpsebuster DD"
    assert normalized.Members[0].Ring2.Level == "CP160"
