from __future__ import annotations

from models.build_model import GearSlot, PlayerBuild
from services.extreme_actual_heal_weapon_candidate_service import (
    ExtremeActualHealWeaponCandidateService,
)


def _build() -> PlayerBuild:
    return PlayerBuild(
        BuildName="H1",
        FrontBarWeapon=GearSlot(
            Set="Existing Set",
            Trait="Powered",
            Quality="Gold",
            Level="CP160",
            WeaponType="Restoration Staff",
        ),
        BackBarWeapon=GearSlot(
            Trait="Nirnhoned",
            Quality="Gold",
            Level="CP160",
            WeaponType="Inferno Staff",
        ),
    )


def test_actual_heal_weapon_candidates_cover_all_other_legal_front_bar_shapes() -> None:
    candidates = ExtremeActualHealWeaponCandidateService().build_candidates(
        _build(),
        character_id="char",
        baseline_build_id="build",
        active_bar="front",
    )

    assert len(candidates) == 27
    assert len({candidate.candidate_id for candidate in candidates}) == 27
    assert all(len(candidate.changes) == 1 for candidate in candidates)


def test_actual_heal_weapon_candidate_preserves_main_metadata_and_materializes_offhand() -> None:
    candidates = ExtremeActualHealWeaponCandidateService().build_candidates(
        _build(),
        character_id="char",
        baseline_build_id="build",
        active_bar="front",
    )
    dual_sword = next(
        candidate
        for candidate in candidates
        if candidate.candidate_id.endswith("sword+sword")
    )

    build = dual_sword.candidate_build
    assert build.FrontBarWeapon.WeaponType == "Sword"
    assert build.FrontBarWeapon.Set == "Existing Set"
    assert build.FrontBarWeapon.Trait == "Powered"
    assert build.FrontBarWeapon.Quality == "Gold"
    assert build.FrontBarWeapon.Level == "CP160"
    assert build.FrontBarOffHand.WeaponType == "Sword"
    assert build.FrontBarOffHand.Quality == "Gold"
    assert build.FrontBarOffHand.Level == "CP160"


def test_actual_heal_weapon_candidates_only_change_requested_bar() -> None:
    baseline = _build()
    candidates = ExtremeActualHealWeaponCandidateService().build_candidates(
        baseline,
        character_id="char",
        baseline_build_id="build",
        active_bar="front",
    )

    assert all(
        candidate.candidate_build.BackBarWeapon.to_dict()
        == baseline.BackBarWeapon.to_dict()
        for candidate in candidates
    )
