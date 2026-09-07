from __future__ import annotations

import pytest

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from minmax.static_build_inputs import DIVINES_PERCENT_BY_QUALITY
from services.extreme_divines_mundus_objective_service import (
    ExtremeDivinesMundusObjectiveService,
)


@pytest.fixture
def repository(tmp_path):
    return MundusRepository(tmp_path / "u50.db", game_update=U50_GAME_UPDATE)


def test_gold_divines_ratio_reuses_static_build_contract():
    assert ExtremeDivinesMundusObjectiveService.GOLD_DIVINES_RATIO == pytest.approx(
        DIVINES_PERCENT_BY_QUALITY["gold"] / 100.0
    )


@pytest.mark.parametrize(
    ("armor_count", "shield", "expected_multiplier"),
    [
        (0, False, 1.0),
        (1, False, 1.091),
        (7, False, 1.637),
        (7, True, 1.728),
    ],
)
def test_configuration_projects_each_legal_divines_source_once(
    armor_count,
    shield,
    expected_multiplier,
):
    row = ExtremeDivinesMundusObjectiveService.configuration(
        armor_divines_count=armor_count,
        shield_divines=shield,
    )

    assert row.multiplier == pytest.approx(expected_multiplier)
    assert row.divines_source_count == armor_count + int(shield)


def test_shadow_critical_damage_is_amplified_by_seven_gold_divines(repository):
    row = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        repository,
        "The Shadow",
        "critical_damage",
        armor_divines_count=7,
    )

    assert row.configuration.multiplier == pytest.approx(1.637)
    assert row.projected_delta == pytest.approx(0.11 * 1.637)


def test_shield_divines_is_an_eighth_source_when_configuration_legally_has_one(repository):
    seven = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        repository,
        "The Lady",
        "physical_resistance",
        armor_divines_count=7,
        shield_divines=False,
    )
    eight = ExtremeDivinesMundusObjectiveService.candidate_for_name(
        repository,
        "The Lady",
        "physical_resistance",
        armor_divines_count=7,
        shield_divines=True,
    )

    assert seven.projected_delta == pytest.approx(2744.0 * 1.637)
    assert eight.projected_delta == pytest.approx(2744.0 * 1.728)
    assert eight.projected_delta > seven.projected_delta


def test_best_mundus_for_fixed_configuration_does_not_claim_equipment_is_globally_best(repository):
    row = ExtremeDivinesMundusObjectiveService.best_mundus_for_configuration(
        repository,
        "spell_damage",
        armor_divines_count=4,
    )

    assert row is not None
    assert row.mundus.mundus_name == "The Apprentice"
    assert row.configuration.armor_divines_count == 4
    assert row.projected_delta == pytest.approx(238.0 * (1.0 + 4 * 0.091))


def test_legal_configuration_inventory_can_include_or_exclude_shield_routes():
    armor_only = ExtremeDivinesMundusObjectiveService.legal_configurations(
        include_shield=False
    )
    with_shield = ExtremeDivinesMundusObjectiveService.legal_configurations(
        include_shield=True
    )

    assert len(armor_only) == 8
    assert len(with_shield) == 16
    assert all(not row.shield_divines for row in armor_only)
    assert any(row.shield_divines for row in with_shield)


def test_impossible_armor_divines_counts_are_rejected():
    with pytest.raises(ValueError, match="between 0 and 7"):
        ExtremeDivinesMundusObjectiveService.configuration(armor_divines_count=-1)
    with pytest.raises(ValueError, match="between 0 and 7"):
        ExtremeDivinesMundusObjectiveService.configuration(armor_divines_count=8)
