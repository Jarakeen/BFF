from minmax.character_build.effect_layer import BarId
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
    ExtremeSustainedDPSWeaponPoisonDilutionSelection,
    ExtremeSustainedDPSWeaponPoisonSelectedEffect,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_consequence_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
)


def _occurrence(poison_id="Test Poison IX"):
    return ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_activation",
            source="Light Attack",
            target="Boss",
            source_bar="front",
        ),
        poison_id=poison_id,
        source_bar=BarId.FRONT,
    )


def _selection(*effects):
    return ExtremeSustainedDPSWeaponPoisonDilutionSelection(
        poison_id="Test Poison IX",
        formula_id="alchemy_formula:u50:test",
        mode=ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE,
        effects=tuple(effects),
    )


def test_breach_projects_minor_breach_to_enemy_runtime() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Breach",
                10.0,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is True
    assert len(result.effects) == 1
    effect = result.effects[0]
    assert effect.name == "minor_breach"
    assert effect.duration == 10.0
    assert effect.target == "Boss"
    assert effect.target_type.value == "enemy"
    assert effect.chance is None


def test_protection_projects_enemy_vulnerability_and_skips_defensive_self_side() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Protection",
                2.5,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is True
    assert [effect.name for effect in result.effects] == ["minor_vulnerability"]
    assert any(
        "self-side Minor Protection is defensive-only" in row
        for row in result.evidence
    )


def test_unreviewed_damage_trait_remains_fail_closed() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Ravage Health",
                6.8,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is False
    assert result.effects == ()
    assert any(
        "has no reviewed Objective #32 named-effect relationship" in row
        for row in result.unresolved
    )


def test_consequence_selection_cannot_be_reused_for_different_poison() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Breach",
                10.0,
            ),
        )
    ).resolve(
        poison_id="Other Poison IX",
        occurrence=_occurrence("Other Poison IX"),
    )

    assert result.resolved is False
    assert any(
        "consequence selection belongs to Test Poison IX" in row
        for row in result.unresolved
    )
