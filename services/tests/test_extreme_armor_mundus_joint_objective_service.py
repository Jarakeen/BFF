from __future__ import annotations

import pytest

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)


@pytest.fixture
def repository(tmp_path):
    return MundusRepository(tmp_path / "u50.db", game_update=U50_GAME_UPDATE)


@pytest.mark.parametrize("objective", ["physical_resistance", "spell_resistance"])
def test_resistance_extreme_prefers_heavy_static_traits_over_divines(repository, objective):
    best = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        repository,
        objective,
    )

    assert best is not None
    assert best.composition_label == "0L/0M/7H"
    assert best.mundus_name == "The Lady"
    assert best.divines_count == 0
    assert best.divines_multiplier == pytest.approx(1.0)

    traits = {piece.slot: piece.trait for piece in best.pieces}
    assert traits == {
        "Head": "Reinforced",
        "Shoulders": "Reinforced",
        "Chest": "Reinforced",
        "Hands": "Nirnhoned",
        "Waist": "Nirnhoned",
        "Legs": "Reinforced",
        "Feet": "Reinforced",
    }
    assert best.armor_passive_delta == pytest.approx(343.0 * 7)
    assert best.mundus_delta == pytest.approx(2744.0)


def test_critical_damage_joint_extreme_uses_medium_divines_and_shadow(repository):
    best = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        repository,
        "critical_damage",
    )

    assert best is not None
    assert best.composition_label == "0L/7M/0H"
    assert best.divines_count == 7
    assert best.mundus_name == "The Shadow"
    assert best.armor_passive_delta == pytest.approx(0.14)
    assert best.mundus_delta == pytest.approx(0.11 * 1.637)
    assert best.total_delta == pytest.approx(0.14 + 0.11 * 1.637)


@pytest.mark.parametrize(
    ("objective", "reference_value", "composition", "mundus"),
    [
        ("magicka_recovery", 1000.0, "7L/0M/0H", "The Atronach"),
        ("stamina_recovery", 1000.0, "0L/7M/0H", "The Serpent"),
        ("spell_damage", 3000.0, "0L/7M/0H", "The Apprentice"),
        ("weapon_damage", 3000.0, "0L/7M/0H", "The Warrior"),
        ("spell_critical", None, "7L/0M/0H", "The Thief"),
        ("weapon_critical", None, "7L/0M/0H", "The Thief"),
    ],
)
def test_joint_optimizer_combines_weight_passives_with_divines_mundus(
    repository,
    objective,
    reference_value,
    composition,
    mundus,
):
    best = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        repository,
        objective,
        reference_value=reference_value,
    )

    assert best is not None
    assert best.composition_label == composition
    assert best.divines_count == 7
    assert best.divines_multiplier == pytest.approx(1.637)
    assert best.mundus_name == mundus


def test_reference_scaled_armor_passive_objective_fails_closed_without_reference(repository):
    best = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        repository,
        "spell_damage",
    )

    # Medium Agility is percent-of-reference. Without a supplied reference the
    # joint layer must not fabricate a fixed score. A legal zero-Medium route can
    # still be evaluated, so the returned best candidate must not pretend to
    # include unresolved Medium contribution.
    assert best is not None
    assert best.armor_passive_delta == pytest.approx(0.0)
    assert best.composition_label != "0L/7M/0H"


def test_unreviewed_objective_is_rejected(repository):
    with pytest.raises(KeyError, match="unreviewed Extreme armor/Mundus objective"):
        ExtremeArmorMundusJointObjectiveService.best_for_objective(
            repository,
            "max_health",
        )
