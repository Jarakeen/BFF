from types import SimpleNamespace

import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_weapon_poison_consequence_authority_factory_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)


def _state(*, poison=True):
    if not poison:
        return SimpleNamespace(
            late=SimpleNamespace(
                assembled=SimpleNamespace(
                    build=PlayerBuild(),
                    poison_loadout=None,
                ),
                poison_loadout=None,
            )
        )

    formula = AlchemyFormula(
        reagents=("A", "B"),
        traits=("Breach",),
        game_update=GameUpdate.U50,
    )
    front = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label=formula.canonical_id,
        formula=formula,
    )
    back = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label="",
        formula=None,
    )
    loadout = ExtremeSustainedDPSWeaponPoisonLoadoutCandidate(
        structural_index=1,
        front=front,
        back=back,
        build=PlayerBuild(FrontBarPoison=formula.canonical_id),
    )
    return SimpleNamespace(
        late=SimpleNamespace(
            assembled=SimpleNamespace(
                build=PlayerBuild(FrontBarPoison=formula.canonical_id),
                poison_loadout=loadout,
            ),
            poison_loadout=loadout,
        )
    )


def test_generated_poison_consequence_factory_builds_candidate_scoped_frontier():
    item_resolver = object()
    mode_resolver = object()
    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        item_evidence_resolver=item_resolver,
        dilution_mode_resolver=mode_resolver,
    )

    result = service.resolve(_state())

    assert result is not None
    named = result.consequence_resolver
    dilution = named.dilution_selection_resolver
    assert dilution.item_evidence_resolver is item_resolver
    assert dilution.dilution_mode_resolver is mode_resolver
    assert dilution.formula_authority.entries


def test_generated_poison_consequence_factory_returns_none_for_explicit_no_poison():
    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        item_evidence_resolver=object(),
        dilution_mode_resolver=object(),
    )

    assert service.resolve(_state(poison=False)) is None


def test_generated_poison_consequence_factory_fails_closed_on_identity_mismatch():
    state = _state()
    state.late.assembled.build.FrontBarPoison = "alchemy_formula:u50:wrong:wrong"
    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        item_evidence_resolver=object(),
        dilution_mode_resolver=object(),
    )

    with pytest.raises(ValueError, match="formula authority is unresolved"):
        service.resolve(state)
