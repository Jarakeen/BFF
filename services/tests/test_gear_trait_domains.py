from __future__ import annotations

from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS, WEAPON_TRAITS, GearSlot, PlayerBuild
from services.extreme_optimization_service import ExtremeOptimizationService


def test_eso_trait_domains_keep_jewelry_separate_from_armor_and_weapons():
    assert "Nirnhoned" in ARMOR_TRAITS
    assert "Nirnhoned" in WEAPON_TRAITS
    assert "Nirnhoned" not in JEWELRY_TRAITS

    assert "Bloodthirsty" in JEWELRY_TRAITS
    assert "Harmony" in JEWELRY_TRAITS
    assert "Swift" in JEWELRY_TRAITS
    assert "Triune" in JEWELRY_TRAITS

    assert "Bloodthirsty" not in ARMOR_TRAITS
    assert "Bloodthirsty" not in WEAPON_TRAITS


def test_extreme_jewelry_candidates_never_generate_nirnhoned():
    baseline = PlayerBuild(
        BuildName="Trait Domain Baseline",
        Necklace=GearSlot(Set="Example Set", Trait="Arcane"),
        Ring1=GearSlot(Set="Example Set", Trait="Healthy"),
        Ring2=GearSlot(Set="Example Set", Trait="Robust"),
    )

    candidates = ExtremeOptimizationService._jewelry_candidates(
        baseline,
        character_id="char-1",
        baseline_build_id="build-1",
    )

    jewelry_trait_changes = [
        change
        for candidate in candidates
        for change in candidate.changes
        if change.path.endswith(".Trait")
    ]

    assert jewelry_trait_changes
    assert all(str(change.after).casefold() != "nirnhoned" for change in jewelry_trait_changes)
