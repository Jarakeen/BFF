from pathlib import Path

from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"


def _catalog_by_name():
    catalog = ExtremeNamedGearSetSlotEligibilityService(DATABASE).build()
    assert not catalog.unresolved
    return {row.name: row for row in catalog.sets}


def test_antiquities_catalog_normalizes_known_mythics_but_not_prophets():
    rows = _catalog_by_name()

    for name in (
        "Torc of Tonal Constancy",
        "Stormweaver's Cavort",
        "Oakensoul Ring",
        "Ring of the Pale Order",
        "Harpooner's Wading Kilt",
    ):
        row = rows[name]
        assert row.max_equip_count == 1
        assert ExtremeNamedGearSetRealizationService.is_mythic_category(row.category)

    prophets = rows["Prophet's"]
    assert prophets.max_equip_count == 1
    assert not ExtremeNamedGearSetRealizationService.is_mythic_category(prophets.category)


def test_one_mythic_global_legality_rejects_torc_plus_cavort_but_allows_prophets():
    rows = _catalog_by_name()
    torc = rows["Torc of Tonal Constancy"]
    cavort = rows["Stormweaver's Cavort"]
    prophets = rows["Prophet's"]

    assert ExtremeNamedGearSetRealizationService._violates_global_set_legality(
        (1, 1),
        (torc, cavort),
    )
    assert not ExtremeNamedGearSetRealizationService._violates_global_set_legality(
        (1, 1),
        (torc, prophets),
    )
