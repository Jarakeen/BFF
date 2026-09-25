from dataclasses import dataclass

import pytest

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.combat_effect_semantics import GameUpdate
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_weapon_poison_tier_frontier_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate,
    ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier,
)
from services.extreme_sustained_dps_generated_weapon_poison_tier_loadout_frontier_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection,
    ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate,
    ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier,
    ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


def _formula(name):
    return AlchemyFormula(
        reagents=(f"{name} A", f"{name} B"),
        traits=(name,),
        game_update=GameUpdate.U50,
    )


def _tier(formula, index, solvent, level):
    return ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate(
        structural_index=index,
        solvent=solvent,
        level=level,
        item_evidence=ExtremeSustainedDPSWeaponPoisonItemEvidence(
            poison_id=formula.canonical_id,
            possible_effects=(
                ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                    effect_name=formula.traits[0],
                    base_duration_seconds=6.0,
                    triple_duration_seconds=3.0,
                    solvent=solvent,
                    level=level,
                ),
            ),
            source_evidence_complete=True,
        ),
    )


class _TierFrontier:
    def frontier(self, formula):
        rows = (
            _tier(formula, 0, "Oil", 40),
            _tier(formula, 1, "Alkahest", 50),
        )
        return ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier(
            candidates=rows,
            candidate_count=2,
            denominator_proven=True,
            evidence=(f"tiers for {formula.canonical_id}",),
        )


def _loadout(*, front=True, back=True):
    front_formula = _formula("Breach") if front else None
    back_formula = _formula("Protection") if back else None
    front_selection = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label="" if front_formula is None else front_formula.canonical_id,
        formula=front_formula,
    )
    back_selection = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label="" if back_formula is None else back_formula.canonical_id,
        formula=back_formula,
    )
    return ExtremeSustainedDPSWeaponPoisonLoadoutCandidate(
        structural_index=3,
        front=front_selection,
        back=back_selection,
        build=PlayerBuild(
            FrontBarPoison=front_selection.selected_label,
            BackBarPoison=back_selection.selected_label,
        ),
    )


def test_tier_loadout_frontier_crosses_front_and_back_tiers():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService(
        _TierFrontier()
    ).frontier(_loadout())

    assert result.denominator_proven is True
    assert result.candidate_count == 4
    assert [
        (
            row.front.tier.solvent,
            row.front.tier.level,
            row.back.tier.solvent,
            row.back.tier.level,
        )
        for row in result.candidates
    ] == [
        ("Oil", 40, "Oil", 40),
        ("Oil", 40, "Alkahest", 50),
        ("Alkahest", 50, "Oil", 40),
        ("Alkahest", 50, "Alkahest", 50),
    ]


def test_tier_loadout_frontier_no_poison_bar_contributes_one_choice():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService(
        _TierFrontier()
    ).frontier(_loadout(front=True, back=False))

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    assert all(row.back.tier is None for row in result.candidates)
    assert all(row.back.poison_id == "" for row in result.candidates)


def test_tier_loadout_frontier_one_bar_rejects_back_poison():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService(
        _TierFrontier()
    ).frontier(_loadout(), one_bar_only=True)

    assert result.denominator_proven is False
    assert result.candidates == ()
    assert any("one-bar" in row for row in result.unresolved)


def test_tier_loadout_frontier_one_bar_allows_explicit_no_poison_back_bar():
    result = ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService(
        _TierFrontier()
    ).frontier(
        _loadout(front=True, back=False),
        one_bar_only=True,
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    assert all(row.back.tier is None for row in result.candidates)


def test_bar_tier_selection_rejects_named_poison_without_tier_evidence():
    with pytest.raises(
        ValueError,
        match="cannot name poison without tier evidence",
    ):
        ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
            poison_id="alchemy_formula:u50:test",
            tier=None,
        )


def test_bar_tier_selection_requires_identity_to_match_tier_evidence():
    formula = _formula("Breach")
    tier = _tier(formula, 0, "Alkahest", 50)

    with pytest.raises(
        ValueError,
        match="identity must match tier item evidence",
    ):
        ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
            poison_id="alchemy_formula:u50:wrong",
            tier=tier,
        )


def test_tier_loadout_frontier_rejects_candidate_count_drift():
    formula = _formula("Breach")
    tier = _tier(formula, 0, "Alkahest", 50)
    selection = ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
        poison_id=formula.canonical_id,
        tier=tier,
    )
    candidate = ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate(
        structural_index=0,
        front=selection,
        back=ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
            poison_id="",
            tier=None,
        ),
    )

    with pytest.raises(
        ValueError,
        match="candidate_count must equal candidate tuple length",
    ):
        ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier(
            candidates=(candidate,),
            candidate_count=2,
            denominator_proven=True,
        )
