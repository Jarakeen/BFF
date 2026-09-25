from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
)
from services.extreme_sustained_dps_weapon_poison_formula_dilution_witness_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService,
)


def _formula(
    *,
    traits=("Breach",),
    triple=(),
    unmarked=(),
    sections=(),
):
    return AlchemyFormula(
        reagents=("A", "B", "C"),
        traits=tuple(traits),
        game_update=GameUpdate.U50,
        source_triple_traits=tuple(triple),
        source_unmarked_traits=tuple(unmarked),
        source_sections=tuple(sections),
    )


def test_literal_triple_annotation_is_promoted_to_per_effect_witness():
    formula = _formula(triple=("Breach",))

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id=formula.canonical_id,
        formula=formula,
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert result.effect_modes == (
        ("Breach", ExtremeSustainedDPSWeaponPoisonDilutionMode.TRIPLE),
    )


def test_unmarked_source_cell_does_not_become_base_duration():
    formula = _formula(unmarked=("Breach",))

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id=formula.canonical_id,
        formula=formula,
    )

    assert result.resolved is False
    assert result.effect_modes == ()
    assert any(
        "unmarked formula source cells do not prove base dilution" in row
        for row in result.unresolved
    )


def test_implicit_formula_trait_without_annotation_fails_closed():
    formula = _formula()

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id=formula.canonical_id,
        formula=formula,
    )

    assert result.resolved is False
    assert any(
        "no literal dilution annotation" in row
        for row in result.unresolved
    )


def test_section_heading_is_provenance_not_dilution_authority():
    formula = _formula(sections=("triple_effect",))

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id=formula.canonical_id,
        formula=formula,
    )

    assert result.resolved is False
    assert result.effect_modes == ()
    assert any(
        "source sections retained as provenance only" in row
        for row in result.evidence
    )


def test_mixed_literal_and_unresolved_traits_remain_incomplete():
    formula = _formula(
        traits=("Breach", "Protection"),
        triple=("Breach",),
        unmarked=("Protection",),
    )

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id=formula.canonical_id,
        formula=formula,
    )

    assert result.resolved is False
    assert result.effect_modes == (
        ("Breach", ExtremeSustainedDPSWeaponPoisonDilutionMode.TRIPLE),
    )
    assert any("Protection" in row for row in result.unresolved)


def test_poison_identity_must_match_formula_identity():
    formula = _formula(triple=("Breach",))

    result = ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService.resolve(
        poison_id="alchemy_formula:u50:other:breach",
        formula=formula,
    )

    assert result.resolved is False
    assert any("identity does not match" in row for row in result.unresolved)
