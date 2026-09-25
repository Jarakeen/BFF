import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
    ExtremeSustainedDPSWeaponPoisonDilutionSelectionService,
)
from services.extreme_sustained_dps_weapon_poison_formula_selection_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaSelection,
)
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


def _source(name, *, base=6.0, triple=3.0):
    return ExtremeSustainedDPSWeaponPoisonPossibleEffect(
        effect_name=name,
        base_duration_seconds=base,
        triple_duration_seconds=triple,
    )


def _selection(*effects):
    formula = AlchemyFormula(
        reagents=("A", "B", "C"),
        traits=tuple(row.effect_name for row in effects),
        game_update=GameUpdate.U50,
    )
    return ExtremeSustainedDPSWeaponPoisonFormulaSelection(
        poison_id="Test Poison IX",
        formula_id=formula.canonical_id,
        selected_effects=tuple(effects),
    )


def test_base_dilution_uses_source_preserved_base_durations() -> None:
    result = ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
        formula_selection=_selection(
            _source("Breach", base=10.0, triple=5.0),
            _source("Protection", base=5.8, triple=2.5),
        ),
        mode=ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE,
    )

    assert result.resolved is True
    assert [(row.effect_name, row.duration_seconds) for row in result.effects] == [
        ("Breach", 10.0),
        ("Protection", 5.8),
    ]


def test_triple_dilution_uses_source_preserved_triple_durations() -> None:
    result = ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
        formula_selection=_selection(
            _source("Breach", base=10.0, triple=5.0),
            _source("Protection", base=5.8, triple=2.5),
        ),
        mode="triple",
    )

    assert result.resolved is True
    assert [(row.effect_name, row.duration_seconds) for row in result.effects] == [
        ("Breach", 5.0),
        ("Protection", 2.5),
    ]


def test_missing_triple_duration_fails_closed() -> None:
    result = ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
        formula_selection=_selection(
            _source("Breach", triple=None),
        ),
        mode="triple",
    )

    assert result.resolved is False
    assert any(
        "has no source-preserved triple-effect duration" in row
        for row in result.unresolved
    )


def test_dilution_does_not_infer_mode_from_effect_count() -> None:
    with pytest.raises(ValueError, match="unsupported weapon-poison dilution mode"):
        ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
            formula_selection=_selection(
                _source("Breach"),
                _source("Protection"),
                _source("Defile"),
            ),
            mode="",
        )


def test_generated_formula_can_override_runtime_poison_identity_without_losing_tier_evidence() -> None:
    result = ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
        formula_selection=_selection(
            _source("Breach", base=10.0, triple=5.0),
        ),
        mode="base",
        poison_id_override="alchemy_formula:u50:a+b:breach",
    )

    assert result.resolved is True
    assert result.poison_id == "alchemy_formula:u50:a+b:breach"
    assert any(
        "Runtime poison identity override: alchemy_formula:u50:a+b:breach" in row
        for row in result.evidence
    )
