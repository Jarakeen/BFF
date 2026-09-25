from minmax.character_build.effect_layer import BarId
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
    ExtremeSustainedDPSWeaponPoisonDilutionSelection,
    ExtremeSustainedDPSWeaponPoisonSelectedEffect,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_authority_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
)


def _occurrence(poison_id="Damage Health Poison IX"):
    return ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=2,
            trigger="weapon_poison_activation",
            source="Weapon Hit",
            target="Boss",
            source_bar=BarId.FRONT.value,
        ),
        poison_id=poison_id,
    )


def _selection(poison_id="Damage Health Poison IX"):
    return ExtremeSustainedDPSWeaponPoisonDilutionSelection(
        poison_id=poison_id,
        formula_id="alchemy_formula:u50:test",
        mode=ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE,
        effects=(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                effect_name="Breach",
                duration_seconds=10.0,
            ),
        ),
    )


class _SelectionResolver:
    def __init__(self, selection):
        self.selection = selection
        self.calls = []

    def resolve(self, *, poison_id, occurrence):
        self.calls.append((poison_id, occurrence))
        return self.selection


def test_explicit_dilution_authority_projects_reviewed_named_effect():
    selection = _selection()
    resolver = _SelectionResolver(selection)
    authority = ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService(
        dilution_selection_resolver=resolver
    )
    occurrence = _occurrence()

    result = authority.resolve(
        poison_id=occurrence.poison_id,
        occurrence=occurrence,
    )

    assert result.resolved is True
    assert [effect.name for effect in result.effects] == ["minor_breach"]
    assert resolver.calls == [(occurrence.poison_id, occurrence)]


def test_missing_selection_witness_fails_closed():
    authority = ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService(
        dilution_selection_resolver=lambda **_: None
    )

    try:
        authority.resolve(
            poison_id="Damage Health Poison IX",
            occurrence=_occurrence(),
        )
    except ValueError as exc:
        assert "no explicit dilution-selection witness" in str(exc)
    else:
        raise AssertionError("missing poison dilution witness must fail closed")


def test_mismatched_selection_identity_stays_unresolved():
    authority = ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService(
        dilution_selection_resolver=lambda **_: _selection("Different Poison")
    )
    occurrence = _occurrence()

    result = authority.resolve(
        poison_id=occurrence.poison_id,
        occurrence=occurrence,
    )

    assert result.resolved is False
    assert any("belongs to Different Poison" in row for row in result.unresolved)
