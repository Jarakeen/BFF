from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_weapon_poison_formula_selection_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaSelectionService,
)
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


def _effect(name):
    return ExtremeSustainedDPSWeaponPoisonPossibleEffect(
        effect_name=name,
        base_duration_seconds=6.0,
        triple_duration_seconds=3.0,
        solvent="Alkahest",
        level=50,
    )


def _evidence(*effects):
    return ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="Damage Health Poison IX",
        possible_effects=tuple(effects),
        source_evidence_complete=True,
        exact_selection_proven=False,
        evidence=("item-label possibility universe resolved",),
        unresolved=(
            "saved poison item label proves possible effects but not exact formula",
        ),
    )


def _formula(*traits, source_sections=()):
    return AlchemyFormula(
        reagents=("A", "B", "C"),
        traits=tuple(traits),
        game_update=GameUpdate.U50,
        source_sections=tuple(source_sections),
    )


def test_explicit_formula_proves_exact_effect_set_against_item_evidence() -> None:
    result = ExtremeSustainedDPSWeaponPoisonFormulaSelectionService.resolve(
        item_evidence=_evidence(
            _effect("Ravage Health"),
            _effect("Breach"),
            _effect("Protection"),
        ),
        formula=_formula("Ravage Health", "Breach"),
    )

    assert result.exact_effect_set_proven is True
    assert result.unresolved == ()
    assert [row.effect_name for row in result.selected_effects] == [
        "Ravage Health",
        "Breach",
    ]
    assert any("does not choose base-versus-triple duration" in row for row in result.evidence)


def test_formula_trait_outside_item_possibility_universe_fails_closed() -> None:
    result = ExtremeSustainedDPSWeaponPoisonFormulaSelectionService.resolve(
        item_evidence=_evidence(_effect("Ravage Health"), _effect("Breach")),
        formula=_formula("Ravage Health", "Defile"),
    )

    assert result.exact_effect_set_proven is False
    assert any(
        "not supported by the item-label Poison tier evidence" in row
        for row in result.unresolved
    )


def test_incomplete_item_source_evidence_blocks_formula_promotion() -> None:
    item_evidence = ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="Damage Health Poison IX",
        possible_effects=(_effect("Ravage Health"),),
        source_evidence_complete=False,
        exact_selection_proven=False,
        unresolved=("source conflict",),
    )

    result = ExtremeSustainedDPSWeaponPoisonFormulaSelectionService.resolve(
        item_evidence=item_evidence,
        formula=_formula("Ravage Health"),
    )

    assert result.exact_effect_set_proven is False
    assert "source conflict" in result.unresolved
    assert any(
        "requires complete item-label source evidence" in row
        for row in result.unresolved
    )


def test_formula_selection_surfaces_source_sections_without_promoting_dilution() -> None:
    result = ExtremeSustainedDPSWeaponPoisonFormulaSelectionService.resolve(
        item_evidence=_evidence(_effect("Ravage Health")),
        formula=_formula(
            "Ravage Health",
            source_sections=("single_effect", "triple_effect"),
        ),
    )

    assert result.exact_effect_set_proven is True
    assert any(
        "Formula source sections: ('single_effect', 'triple_effect')" in row
        for row in result.evidence
    )
    assert any(
        "do not independently prove base-versus-triple dilution" in row
        for row in result.evidence
    )
