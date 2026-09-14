from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)


def test_mythic_category_accepts_importer_label_variants():
    service = ExtremeNamedGearSetRealizationService
    assert service.is_mythic_category("Mythic")
    assert service.is_mythic_category("Mythic Item")
    assert service.is_mythic_category("Mythic Items")
    assert service.is_mythic_category("  MYTHIC   ITEM  ")


def test_mythic_category_rejects_non_mythic_categories():
    service = ExtremeNamedGearSetRealizationService
    assert not service.is_mythic_category("Dungeon")
    assert not service.is_mythic_category("Monster Set")
    assert not service.is_mythic_category("")
