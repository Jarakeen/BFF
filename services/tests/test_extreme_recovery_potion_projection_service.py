from __future__ import annotations

from minmax.alchemy_formula_catalog import AlchemyFormula, AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate, U50_ALCHEMY_TRAITS
from services.extreme_recovery_potion_projection_service import (
    ExtremeRecoveryPotionProjectionService,
)


class _Repository:
    def __init__(self, formulas, *, unresolved=()):
        self.game_update = GameUpdate.U50
        self._catalog = AlchemyFormulaCatalog(
            tuple(formulas),
            GameUpdate.U50,
            tuple(unresolved),
        )

    def catalog(self):
        return self._catalog


def _formula(*traits: str) -> AlchemyFormula:
    return AlchemyFormula(
        reagents=("A", "B"),
        traits=tuple(traits),
        game_update=GameUpdate.U50,
    )


def test_health_recovery_retains_restore_health_major_fortitude_formulas():
    repository = _Repository(
        (
            _formula("Restore Health", "Vitality"),
            _formula("Restore Magicka", "Increase Spell Power"),
            _formula("Invisible", "Speed"),
        )
    )

    result = ExtremeRecoveryPotionProjectionService(repository).build("health_recovery")

    assert result.denominator_proven is True
    assert len(result.relevant_formulas) == 1
    assert result.relevant_buffs == ("Major Fortitude",)
    assert result.traits_reviewed == tuple(sorted(U50_ALCHEMY_TRAITS, key=str.casefold))
    assert result.unresolved == ()


def test_non_trait_source_cell_warnings_are_neutral_after_complete_u50_trait_review():
    repository = _Repository(
        (_formula("Restore Health", "Increase Armor"),),
        unresolved=(
            "Breach formula #1: non-trait source cells rejected: Lady's Smock, Beetle Scuttle",
        ),
    )

    result = ExtremeRecoveryPotionProjectionService(repository).build("health_recovery")

    assert result.denominator_proven is True
    assert result.relevant_buffs == ("Major Fortitude",)
    assert result.unresolved == ()


def test_other_catalog_unresolved_evidence_still_blocks_recovery_potion_proof():
    repository = _Repository(
        (_formula("Restore Health"),),
        unresolved=("Alchemy formula #9: fewer than two reagents",),
    )

    result = ExtremeRecoveryPotionProjectionService(repository).build("health_recovery")

    assert result.denominator_proven is False
    assert result.unresolved == ("Alchemy formula #9: fewer than two reagents",)


def test_unknown_formula_trait_fails_closed():
    repository = _Repository((_formula("Mystery Recovery Trait"),))

    result = ExtremeRecoveryPotionProjectionService(repository).build("health_recovery")

    assert result.denominator_proven is False
    assert any("outside the reviewed U50 universe" in row for row in result.unresolved)
