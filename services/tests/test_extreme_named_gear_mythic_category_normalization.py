from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


def _eligibility(category: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=1,
        name="Mythic Fixture",
        category=category,
        max_equip_count=1,
        jewelry_slots=("Ring",),
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


def test_catalog_realization_shape_uses_canonical_mythic_predicate():
    shape = ExtremeNamedGearSetCatalogRealizationService._eligibility_shape(
        _eligibility("Mythic Item")
    )
    assert shape.mythic is True


def test_partial_feasibility_shape_uses_canonical_mythic_predicate():
    shape = ExtremePartialNamedGearPhysicalFeasibilityService._shape(
        _eligibility("Mythic Items")
    )
    assert shape[0] is True
