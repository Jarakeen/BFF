from types import SimpleNamespace

import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_weapon_poison_consequence_authority_factory_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
)


def _state(*, poison=True, triple=False):
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
        source_triple_traits=("Breach",) if triple else (),
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


def test_generated_poison_consequence_factory_projects_reviewed_named_effect_end_to_end():
    state = _state()
    poison_id = state.late.assembled.build.FrontBarPoison

    def item_evidence(*, poison_id, formula, occurrence):
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

    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        item_evidence_resolver=item_evidence,
        dilution_mode_resolver=lambda **_kwargs: "base",
    )
    frontier = service.resolve(state)
    occurrence = ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_activation",
            source="Light Attack",
            target="Boss",
            source_bar="front",
        ),
        poison_id=poison_id,
    )

    result = frontier.consequence_resolver.resolve(
        poison_id=poison_id,
        occurrence=occurrence,
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.effects) == 1
    effect = result.effects[0]
    assert effect.name == "minor_breach"
    assert effect.duration == 10.0
    assert effect.target == "Boss"
    assert effect.source == poison_id


def test_generated_poison_consequence_factory_uses_source_bar_tier_for_same_formula():
    state = _state()
    formula = state.late.poison_loadout.front.formula
    poison_id = formula.canonical_id
    same_formula_loadout = ExtremeSustainedDPSWeaponPoisonLoadoutCandidate(
        structural_index=2,
        front=ExtremeSustainedDPSWeaponPoisonSelection(
            selected_label=poison_id,
            formula=formula,
        ),
        back=ExtremeSustainedDPSWeaponPoisonSelection(
            selected_label=poison_id,
            formula=formula,
        ),
        build=PlayerBuild(
            FrontBarPoison=poison_id,
            BackBarPoison=poison_id,
        ),
    )
    state.late.poison_loadout = same_formula_loadout
    state.late.assembled.poison_loadout = same_formula_loadout
    state.late.assembled.build = PlayerBuild(
        FrontBarPoison=poison_id,
        BackBarPoison=poison_id,
    )

    def tier_evidence(duration):
        return ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id=poison_id,
            possible_effects=(
                ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                    effect_name="Breach",
                    base_duration_seconds=duration,
                    triple_duration_seconds=duration / 2.0,
                    solvent="Alkahest",
                    level=50,
                ),
            ),
            source_evidence_complete=True,
        )

    state.late.assembled.poison_tier_loadout = SimpleNamespace(
        front=SimpleNamespace(
            poison_id=poison_id,
            tier=SimpleNamespace(item_evidence=tier_evidence(10.0)),
        ),
        back=SimpleNamespace(
            poison_id=poison_id,
            tier=SimpleNamespace(item_evidence=tier_evidence(6.0)),
        ),
    )
    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        dilution_mode_resolver=lambda **_kwargs: "base",
    )
    frontier = service.resolve(state)

    def occurrence(bar):
        return ExtremeSustainedDPSWeaponPoisonProcOccurrence(
            event=RuntimeEvent(
                time_seconds=1.0,
                sequence=0,
                trigger="weapon_poison_activation",
                source="Weapon Hit",
                target="Boss",
                source_bar=bar,
            ),
            poison_id=poison_id,
        )

    front = frontier.consequence_resolver.resolve(
        poison_id=poison_id,
        occurrence=occurrence("front"),
    )
    back = frontier.consequence_resolver.resolve(
        poison_id=poison_id,
        occurrence=occurrence("back"),
    )

    assert front.resolved is True
    assert back.resolved is True
    assert front.effects[0].duration == 10.0
    assert back.effects[0].duration == 6.0

def test_generated_poison_consequence_factory_defaults_to_literal_formula_dilution_witness():
    state = _state(triple=True)
    formula = state.late.poison_loadout.front.formula
    poison_id = formula.canonical_id
    state.late.assembled.poison_tier_loadout = SimpleNamespace(
        front=SimpleNamespace(
            poison_id=poison_id,
            tier=SimpleNamespace(
                item_evidence=ExtremeSustainedDPSWeaponPoisonItemEvidence(
                    poison_id=poison_id,
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
                )
            ),
        ),
        back=SimpleNamespace(poison_id="", tier=None),
    )
    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService()
    frontier = service.resolve(state)
    occurrence = ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_activation",
            source="Light Attack",
            target="Boss",
            source_bar="front",
        ),
        poison_id=poison_id,
    )

    result = frontier.consequence_resolver.resolve(
        poison_id=poison_id,
        occurrence=occurrence,
    )

    assert result.resolved is True
    assert result.effects[0].duration == 5.0



def test_generated_poison_consequence_does_not_fall_back_to_stale_late_tier_provenance():
    state = _state()
    formula = state.late.assembled.poison_loadout.front.formula
    poison_id = formula.canonical_id
    stale_tier = SimpleNamespace(
        front=SimpleNamespace(
            poison_id=poison_id,
            tier=SimpleNamespace(
                item_evidence=ExtremeSustainedDPSWeaponPoisonItemEvidence(
                    poison_id=poison_id,
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
                )
            ),
        ),
        back=SimpleNamespace(poison_id="", tier=None),
    )
    state.late.poison_tier_loadout = stale_tier
    state.late.assembled.poison_tier_loadout = None

    service = ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService(
        dilution_mode_resolver=lambda **_kwargs: "base",
    )
    frontier = service.resolve(state)
    occurrence = ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_activation",
            source="Light Attack",
            target="Boss",
            source_bar="front",
        ),
        poison_id=poison_id,
    )

    with pytest.raises(
        ValueError,
        match="requires retained poison tier loadout",
    ):
        frontier.consequence_resolver.resolve(
            poison_id=poison_id,
            occurrence=occurrence,
        )
