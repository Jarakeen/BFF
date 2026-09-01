from __future__ import annotations

from minmax.alchemy_formula_catalog import AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate


def _payload():
    return {
        "effects": [
            {
                "effect_name": "Increase Spell Power",
                "source_files": ["spell_power.html"],
                "formulas": [
                    {
                        "ingredients": ["Corn Flower", "Lady's Smock", "Water Hyacinth"],
                        "effects": ["Restore Magicka", "Increase Spell Power", "Spell Critical"],
                    }
                ],
            },
            {
                "effect_name": "Spell Critical",
                "source_files": ["spell_critical.html"],
                "formulas": [
                    {
                        "ingredients": ["Water Hyacinth", "Corn Flower", "Lady's Smock"],
                        "effects": ["Spell Critical", "Restore Magicka", "Increase Spell Power"],
                    }
                ],
            },
        ]
    }


def test_u50_catalog_deduplicates_formula_evidence():
    catalog = AlchemyFormulaCatalog.from_processed_payload(_payload(), game_update=GameUpdate.U50)

    assert catalog.unresolved == ()
    assert len(catalog.formulas) == 1
    formula = catalog.formulas[0]
    assert set(formula.reagents) == {"Corn Flower", "Lady's Smock", "Water Hyacinth"}
    assert set(formula.traits) == {"Restore Magicka", "Increase Spell Power", "Spell Critical"}
    assert formula.source_effects == ("Increase Spell Power", "Spell Critical")
    assert formula.source_files == ("spell_power.html", "spell_critical.html")


def test_effect_page_name_is_primary_formula_evidence():
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "source_files": ["restore_magicka.html"],
                "formulas": [
                    {
                        "ingredients": ["Corn Flower", "Lady's Smock"],
                        "effects": ["Increase Spell Power"],
                    }
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)

    assert catalog.unresolved == ()
    assert len(catalog.formulas) == 1
    assert set(catalog.formulas[0].traits) == {"Restore Magicka", "Increase Spell Power"}


def test_u51_legacy_alias_migrates_power_and_critical_traits():
    catalog = AlchemyFormulaCatalog.from_processed_payload(
        _payload(),
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    )

    assert catalog.unresolved == ()
    assert len(catalog.formulas) == 1
    assert set(catalog.formulas[0].traits) == {"Restore Magicka", "Increase Power", "Critical"}


def test_u51_strict_source_semantics_fail_closed_on_removed_traits():
    catalog = AlchemyFormulaCatalog.from_processed_payload(_payload(), game_update=GameUpdate.U51)

    assert catalog.formulas == ()
    assert any("obsolete traits for U51" in message for message in catalog.unresolved)


def test_find_by_traits_supports_exact_and_subset_queries():
    catalog = AlchemyFormulaCatalog.from_processed_payload(_payload(), game_update=GameUpdate.U50)

    assert len(catalog.find_by_traits("Restore Magicka", "Increase Spell Power", "Spell Critical")) == 1
    assert catalog.find_by_traits("Spell Critical") == ()
    assert len(catalog.find_by_traits("Spell Critical", exact=False)) == 1


def test_primary_effect_can_stand_alone_when_secondary_effect_cells_are_blank():
    payload = {
        "effects": [
            {
                "effect_name": "Timidity",
                "source_files": ["timidity.html"],
                "formulas": [
                    {"ingredients": ["A", "B"], "effects": []},
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)

    assert catalog.unresolved == ()
    assert len(catalog.formulas) == 1
    assert catalog.formulas[0].traits == ("Timidity",)


def test_malformed_formula_rows_remain_explicitly_unresolved():
    payload = {
        "effects": [
            {
                "effect_name": "Timidity",
                "source_files": ["timidity.html"],
                "formulas": [
                    {"ingredients": ["One Reagent"], "effects": ["Timidity"]},
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)

    assert catalog.formulas == ()
    assert len(catalog.unresolved) == 1
    assert "fewer than two reagents" in catalog.unresolved[0]


def test_non_trait_cells_from_malformed_uesp_table_are_rejected():
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "source_files": ["restore_magicka.html"],
                "formulas": [
                    {
                        "ingredients": ["Corn Flower", "Lady's Smock", "Water Hyacinth"],
                        "effects": [
                            "Increase Spell Power",
                            "Spell Critical",
                            "Bugloss",
                            "Main Ingredients",
                        ],
                    }
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)

    assert catalog.formulas == ()
    assert len(catalog.unresolved) == 1
    assert "non-trait source cells rejected" in catalog.unresolved[0]
    assert "Bugloss" in catalog.unresolved[0]
