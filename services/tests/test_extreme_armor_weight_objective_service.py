from __future__ import annotations

import pytest

from services.extreme_armor_weight_objective_service import (
    ExtremeArmorWeightObjectiveService,
)


def test_legal_compositions_cover_every_seven_piece_weight_split_once():
    rows = ExtremeArmorWeightObjectiveService.legal_compositions()

    assert len(rows) == 36
    assert len(set(rows)) == 36
    assert all(sum(row) == 7 for row in rows)
    assert (7, 0, 0) in rows
    assert (0, 7, 0) in rows
    assert (0, 0, 7) in rows


@pytest.mark.parametrize(
    ("objective", "expected_composition"),
    [
        ("critical_damage", "0L/7M/0H"),
        ("spell_resistance", "7L/0M/0H"),
        ("spell_critical", "7L/0M/0H"),
        ("weapon_critical", "7L/0M/0H"),
    ],
)
def test_direct_ratio_or_flat_objectives_choose_expected_weight_extreme(
    objective,
    expected_composition,
):
    best = ExtremeArmorWeightObjectiveService.best_for_objective(objective)

    assert best is not None
    assert best.composition_label == expected_composition
    assert best.projected_delta is not None
    assert best.projected_delta > 0.0


@pytest.mark.parametrize(
    ("objective", "reference_value", "expected_composition"),
    [
        ("magicka_recovery", 1000.0, "7L/0M/0H"),
        ("stamina_recovery", 1000.0, "0L/7M/0H"),
        ("spell_damage", 3000.0, "0L/7M/0H"),
        ("weapon_damage", 3000.0, "0L/7M/0H"),
    ],
)
def test_reference_scaled_objectives_choose_expected_weight_extreme(
    objective,
    reference_value,
    expected_composition,
):
    best = ExtremeArmorWeightObjectiveService.best_for_objective(
        objective,
        reference_value=reference_value,
    )

    assert best is not None
    assert best.composition_label == expected_composition
    assert best.projected_delta is not None
    assert best.projected_delta > 0.0


def test_reference_scaled_objective_refuses_fake_fixed_score_without_reference_value():
    rows = ExtremeArmorWeightObjectiveService.candidates_for_objective("spell_damage")
    medium = next(row for row in rows if row.composition_label == "0L/7M/0H")

    assert medium.percent_of_reference > 0.0
    assert medium.projected_delta is None


def test_physical_resistance_has_no_reviewed_armor_passive_contribution():
    rows = ExtremeArmorWeightObjectiveService.candidates_for_objective("physical_resistance")

    assert rows
    assert all(row.projected_delta == 0.0 for row in rows)
    assert all(row.sources == () for row in rows)


def test_invalid_composition_is_rejected_instead_of_being_normalized_silently():
    with pytest.raises(ValueError, match="exactly seven"):
        ExtremeArmorWeightObjectiveService.candidate_for_composition(
            "critical_damage",
            light_pieces=4,
            medium_pieces=4,
            heavy_pieces=0,
        )


def test_unknown_objective_is_rejected():
    with pytest.raises(KeyError, match="unreviewed Extreme armor objective"):
        ExtremeArmorWeightObjectiveService.best_for_objective("max_health")
