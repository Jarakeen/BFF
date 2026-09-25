from types import SimpleNamespace

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_weapon_poison_formula_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)


def _formula(name="Ravage Health"):
    return AlchemyFormula(
        reagents=("A", "B"),
        traits=(name,),
        game_update=GameUpdate.U50,
    )


def _state(*, mismatch=False, retain=True):
    formula = _formula()
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
    build = PlayerBuild(
        FrontBarPoison=("alchemy_formula:u50:wrong:wrong" if mismatch else formula.canonical_id)
    )
    assembled = SimpleNamespace(
        build=build,
        poison_loadout=(loadout if retain else None),
    )
    return SimpleNamespace(
        late=SimpleNamespace(
            assembled=assembled,
            poison_loadout=(loadout if retain else None),
        )
    )


def test_generated_formula_authority_retains_exact_selected_formula():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService.resolve(
        _state()
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.bar == "front"
    assert entry.poison_id == entry.formula.canonical_id
    assert result.formula_for(entry.poison_id) is entry.formula


def test_generated_formula_authority_fails_closed_on_flattened_identity_mismatch():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService.resolve(
        _state(mismatch=True)
    )

    assert result.resolved is False
    assert any("generated poison identity mismatch" in row for row in result.unresolved)


def test_generated_formula_authority_rejects_flattened_poison_without_provenance():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService.resolve(
        _state(retain=False)
    )

    assert result.resolved is False
    assert result.entries == ()
    assert any(
        "without retained poison-loadout provenance" in row
        for row in result.unresolved
    )


def test_generated_formula_authority_accepts_explicit_no_poison_candidate():
    state = SimpleNamespace(
        late=SimpleNamespace(
            assembled=SimpleNamespace(
                build=PlayerBuild(),
                poison_loadout=None,
            ),
            poison_loadout=None,
        )
    )

    result = ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService.resolve(
        state
    )

    assert result.resolved is True
    assert result.entries == ()
    assert any("no weapon poison" in row for row in result.evidence)
