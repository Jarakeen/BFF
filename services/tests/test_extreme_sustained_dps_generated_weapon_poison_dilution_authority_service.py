from types import SimpleNamespace

import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_generated_weapon_poison_dilution_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService,
)
from services.extreme_sustained_dps_generated_weapon_poison_formula_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority,
    ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry,
)
from services.extreme_sustained_dps_weapon_poison_formula_dilution_witness_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService,
)
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


def _formula():
    return AlchemyFormula(
        reagents=("A", "B"),
        traits=("Breach",),
        game_update=GameUpdate.U50,
    )


def _formula_authority():
    formula = _formula()
    return (
        formula,
        ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
            entries=(
                ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry(
                    bar="front",
                    poison_id=formula.canonical_id,
                    formula=formula,
                ),
            ),
        ),
    )


def _item_evidence():
    return ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id="Damage Health Poison IX",
        possible_effects=(
            ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                effect_name="Breach",
                base_duration_seconds=10.0,
                triple_duration_seconds=5.0,
                solvent="Alkahest",
                level=50,
            ),
        ),
        source_evidence_complete=True,
        exact_selection_proven=False,
        evidence=("reviewed Poison IX tier witness",),
        unresolved=(
            "saved poison item label proves possible effects but not exact formula",
        ),
    )


def test_generated_dilution_authority_combines_formula_tier_and_mode_without_identity_loss():
    formula, formula_authority = _formula_authority()
    seen = {}

    def item_evidence(*, poison_id, formula, occurrence):
        seen["item"] = (poison_id, formula, occurrence)
        return _item_evidence()

    def dilution_mode(*, poison_id, formula, occurrence):
        seen["mode"] = (poison_id, formula, occurrence)
        return "triple"

    occurrence = SimpleNamespace(marker="proc")
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=formula_authority,
        item_evidence_resolver=item_evidence,
        dilution_mode_resolver=dilution_mode,
    )

    result = service.resolve(
        poison_id=formula.canonical_id,
        occurrence=occurrence,
    )

    assert result.resolved is True
    assert result.poison_id == formula.canonical_id
    assert result.formula_id == formula.canonical_id
    assert [(row.effect_name, row.duration_seconds) for row in result.effects] == [
        ("Breach", 5.0),
    ]
    assert seen["item"] == (formula.canonical_id, formula, occurrence)
    assert seen["mode"] == (formula.canonical_id, formula, occurrence)
    assert any("Runtime poison identity override" in row for row in result.evidence)


def test_generated_dilution_authority_requires_formula_witness():
    _formula_value, _authority = _formula_authority()
    empty_authority = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(entries=())
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=empty_authority,
        item_evidence_resolver=lambda **_kwargs: _item_evidence(),
        dilution_mode_resolver=lambda **_kwargs: "base",
    )

    with pytest.raises(ValueError, match="no unique formula witness"):
        service.resolve(
            poison_id="alchemy_formula:u50:missing:missing",
            occurrence=object(),
        )


def test_generated_dilution_authority_requires_item_tier_witness():
    formula, authority = _formula_authority()
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=authority,
        item_evidence_resolver=lambda **_kwargs: None,
        dilution_mode_resolver=lambda **_kwargs: "base",
    )

    with pytest.raises(ValueError, match="returned no witness"):
        service.resolve(poison_id=formula.canonical_id, occurrence=object())


def test_generated_dilution_authority_requires_explicit_dilution_mode():
    formula, authority = _formula_authority()
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=authority,
        item_evidence_resolver=lambda **_kwargs: _item_evidence(),
        dilution_mode_resolver=lambda **_kwargs: None,
    )

    with pytest.raises(ValueError, match="dilution-mode resolver returned no witness"):
        service.resolve(poison_id=formula.canonical_id, occurrence=object())


def test_generated_dilution_authority_accepts_per_effect_mode_witness():
    formula = AlchemyFormula(
        reagents=("A", "B", "C"),
        traits=("Breach", "Protection"),
        game_update=GameUpdate.U50,
    )
    authority = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
        entries=(
            ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry(
                bar="front",
                poison_id=formula.canonical_id,
                formula=formula,
            ),
        ),
    )
    item_evidence = ExtremeSustainedDPSWeaponPoisonItemEvidence(
        poison_id=formula.canonical_id,
        possible_effects=(
            ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                effect_name="Breach",
                base_duration_seconds=10.0,
                triple_duration_seconds=5.0,
                solvent="Alkahest",
                level=50,
            ),
            ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                effect_name="Protection",
                base_duration_seconds=5.8,
                triple_duration_seconds=2.5,
                solvent="Alkahest",
                level=50,
            ),
        ),
        source_evidence_complete=True,
        exact_selection_proven=False,
    )
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=authority,
        item_evidence_resolver=lambda **_kwargs: item_evidence,
        dilution_mode_resolver=lambda **_kwargs: (
            ("Breach", "triple"),
            ("Protection", "base"),
        ),
    )

    result = service.resolve(
        poison_id=formula.canonical_id,
        occurrence=object(),
    )

    assert result.resolved is True
    assert result.mode is None
    assert [(row.effect_name, row.duration_seconds) for row in result.effects] == [
        ("Breach", 5.0),
        ("Protection", 5.8),
    ]

def test_generated_dilution_authority_accepts_formula_literal_triple_witness():
    formula = AlchemyFormula(
        reagents=("A", "B"),
        traits=("Breach",),
        game_update=GameUpdate.U50,
        source_triple_traits=("Breach",),
    )
    authority = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
        entries=(
            ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry(
                bar="front",
                poison_id=formula.canonical_id,
                formula=formula,
            ),
        ),
    )
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=authority,
        item_evidence_resolver=lambda **_kwargs: _item_evidence(),
        dilution_mode_resolver=(
            ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService
        ),
    )

    result = service.resolve(
        poison_id=formula.canonical_id,
        occurrence=object(),
    )

    assert result.resolved is True
    assert result.mode is None
    assert [(row.effect_name, row.duration_seconds) for row in result.effects] == [
        ("Breach", 5.0),
    ]



def test_generated_dilution_authority_prefers_resolve_method_on_callable_class():
    formula = AlchemyFormula(
        reagents=("A", "B"),
        traits=("Breach",),
        game_update=GameUpdate.U50,
        source_triple_traits=("Breach",),
    )
    authority = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthority(
        entries=(
            ExtremeSustainedDPSGeneratedWeaponPoisonFormulaEntry(
                bar="front",
                poison_id=formula.canonical_id,
                formula=formula,
            ),
        ),
    )
    service = ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
        formula_authority=authority,
        item_evidence_resolver=lambda **_kwargs: _item_evidence(),
        dilution_mode_resolver=(
            ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService
        ),
    )

    result = service.resolve(
        poison_id=formula.canonical_id,
        occurrence=object(),
    )

    assert result.resolved is True
    assert result.effects[0].duration_seconds == 5.0
