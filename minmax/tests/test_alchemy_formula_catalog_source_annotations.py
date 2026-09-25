from minmax.alchemy_formula_catalog import AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate, is_known_alchemy_trait


def test_historical_ravage_resource_traits_are_known_u50_alchemy_traits():
    assert is_known_alchemy_trait("Ravage Magicka", game_update=GameUpdate.U50)
    assert is_known_alchemy_trait("Ravage Stamina", game_update=GameUpdate.U50)


def test_triple_annotation_normalizes_to_underlying_known_trait():
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "source_files": ["restore_magicka.html"],
                "formulas": [
                    {
                        "ingredients": ["A", "B", "C"],
                        "effects": ["Restore Health (triple)", "Ravage Magicka (triple)"],
                    }
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)

    assert catalog.unresolved == ()
    assert len(catalog.formulas) == 1
    formula = catalog.formulas[0]
    assert set(formula.traits) == {
        "Restore Magicka",
        "Restore Health",
        "Ravage Magicka",
    }
    assert set(formula.source_triple_traits) == {
        "Restore Health",
        "Ravage Magicka",
    }
    assert formula.source_unmarked_traits == ()


def test_unmarked_formula_cells_are_preserved_separately_from_triple_annotations():
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "formulas": [
                    {
                        "ingredients": ["A", "B", "C"],
                        "effects": ["Restore Health", "Ravage Magicka (triple)"],
                    }
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(
        payload,
        game_update=GameUpdate.U50,
    )

    assert catalog.unresolved == ()
    formula = catalog.formulas[0]
    assert formula.source_triple_traits == ("Ravage Magicka",)
    assert formula.source_unmarked_traits == ("Restore Health",)


def test_conflicting_explicit_triple_and_unmarked_annotations_fail_closed():
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "formulas": [
                    {
                        "ingredients": ["A", "B", "C"],
                        "effects": ["Restore Health (triple)"],
                    },
                    {
                        "ingredients": ["A", "B", "C"],
                        "effects": ["Restore Health"],
                    },
                ],
            }
        ]
    }

    catalog = AlchemyFormulaCatalog.from_processed_payload(
        payload,
        game_update=GameUpdate.U50,
    )

    assert any(
        "conflicting explicit triple/unmarked trait annotations" in row
        for row in catalog.unresolved
    )
