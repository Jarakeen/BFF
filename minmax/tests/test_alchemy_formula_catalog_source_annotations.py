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
    assert set(catalog.formulas[0].traits) == {
        "Restore Magicka",
        "Restore Health",
        "Ravage Magicka",
    }
