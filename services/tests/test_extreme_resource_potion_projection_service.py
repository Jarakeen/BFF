from __future__ import annotations

from minmax.alchemy_formula_catalog import AlchemyFormula, AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_resource_potion_projection_service import (
    ExtremeResourcePotionProjectionService,
)


class _Repository:
    def __init__(self, formulas):
        self.game_update = GameUpdate.U50
        self._catalog = AlchemyFormulaCatalog(tuple(formulas), GameUpdate.U50)

    def catalog(self):
        return self._catalog


def _formula(*traits: str) -> AlchemyFormula:
    return AlchemyFormula(
        reagents=("A", "B"),
        traits=tuple(traits),
        game_update=GameUpdate.U50,
    )


def test_u50_potion_catalog_is_proven_irrelevant_to_max_magicka():
    repository = _Repository(
        (
            _formula("Restore Magicka", "Increase Spell Power", "Spell Critical"),
            _formula("Restore Health", "Increase Armor"),
        )
    )

    result = ExtremeResourcePotionProjectionService(repository).build("max_magicka")

    assert result.formulas_reviewed == 2
    assert result.relevant_formulas == ()
    assert result.objective_irrelevance_proven is True


def test_u50_potion_catalog_is_proven_irrelevant_to_max_stamina():
    repository = _Repository(
        (
            _formula("Restore Stamina", "Increase Weapon Power", "Weapon Critical"),
            _formula("Restore Health", "Increase Spell Resist"),
        )
    )

    result = ExtremeResourcePotionProjectionService(repository).build("max_stamina")

    assert result.formulas_reviewed == 2
    assert result.relevant_formulas == ()
    assert result.objective_irrelevance_proven is True


def test_unknown_potion_trait_fails_closed_instead_of_assuming_irrelevance():
    repository = _Repository((_formula("Mystery Maximum Resource"),))

    result = ExtremeResourcePotionProjectionService(repository).build("max_magicka")

    assert result.objective_irrelevance_proven is False
    assert any("no reviewed named-buff semantics" in row for row in result.unresolved)
