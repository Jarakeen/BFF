from __future__ import annotations

import pytest

from services.extreme_objective_coverage_service import (
    ExtremeObjectiveClaim,
    ExtremeObjectiveCoverage,
    ExtremeObjectiveCoverageService,
    ExtremeSourceCoverageStatus,
    ExtremeSourceFamilyCoverage,
)


def _by_source(coverage):
    return {row.source_family: row for row in coverage.sources}


@pytest.mark.parametrize(
    "objective",
    ExtremeObjectiveCoverageService.REVIEWED_OBJECTIVES,
)
def test_every_current_extreme_objective_is_explicitly_a_lower_bound(objective):
    coverage = ExtremeObjectiveCoverageService.coverage_for(objective)

    assert coverage.objective_key == objective
    assert coverage.claim is ExtremeObjectiveClaim.BEST_REVIEWED_LOWER_BOUND
    assert coverage.global_maximum_ready is False
    assert coverage.source_universe_reviewed is False
    assert coverage.blocking_sources


def test_skill_universe_is_split_into_explicit_player_skill_families():
    coverage = ExtremeObjectiveCoverageService.coverage_for("physical_resistance")
    sources = _by_source(coverage)

    expected = {
        "active_skills",
        "class_skill_passives",
        "weapon_skill_passives",
        "armor_skill_passives",
        "guild_skill_passives",
        "alliance_war_passives",
        "world_skill_passives",
        "racial_skill_passives",
        "craft_utility_passives",
    }
    assert expected.issubset(sources)
    assert all(
        sources[source].status is ExtremeSourceCoverageStatus.PARTIAL
        for source in expected
    )
    assert all(sources[source].blocks_global_maximum for source in expected)


def test_old_class_passives_umbrella_no_longer_masquerades_as_complete():
    coverage = ExtremeObjectiveCoverageService.coverage_for("critical_damage")
    sources = _by_source(coverage)

    assert "class_passives" not in sources
    assert "slotted_skills" not in sources
    assert sources["class_skill_passives"].status is ExtremeSourceCoverageStatus.PARTIAL
    assert sources["active_skills"].status is ExtremeSourceCoverageStatus.PARTIAL


@pytest.mark.parametrize(
    "source_family",
    [
        "gear_sets",
        "champion_points",
        "enchantments",
    ],
)
def test_unmodeled_whole_build_sources_block_global_maximum(source_family):
    coverage = ExtremeObjectiveCoverageService.coverage_for("physical_resistance")
    sources = _by_source(coverage)

    assert sources[source_family].status is ExtremeSourceCoverageStatus.NOT_MODELED
    assert sources[source_family].blocks_global_maximum is True


def test_armor_base_values_and_traits_are_partial_not_missing():
    coverage = ExtremeObjectiveCoverageService.coverage_for("physical_resistance")
    armor = _by_source(coverage)["armor_base_values_traits"]

    assert armor.status is ExtremeSourceCoverageStatus.PARTIAL
    assert armor.blocks_global_maximum is True
    assert "base values" in armor.note.casefold()
    assert "trait" in armor.note.casefold()


def test_race_structured_projection_is_partial_until_nonstructured_passives_are_exhaustive():
    coverage = ExtremeObjectiveCoverageService.coverage_for("critical_damage")
    race = _by_source(coverage)["race"]

    assert race.status is ExtremeSourceCoverageStatus.PARTIAL
    assert race.blocks_global_maximum is True
    assert "conditional" in race.note.casefold()
    assert "non-structured" in race.note.casefold()


def test_mundus_base_projection_is_partial_until_multiplier_inputs_are_exhaustive():
    coverage = ExtremeObjectiveCoverageService.coverage_for("critical_damage")
    mundus = _by_source(coverage)["mundus"]

    assert mundus.status is ExtremeSourceCoverageStatus.PARTIAL
    assert mundus.blocks_global_maximum is True
    assert "multiplier" in mundus.note.casefold()


def test_supplied_context_support_does_not_masquerade_as_exhaustive_generation():
    coverage = ExtremeObjectiveCoverageService.coverage_for("spell_damage")
    sources = _by_source(coverage)

    assert sources["consumables"].status is ExtremeSourceCoverageStatus.PARTIAL
    assert sources["runtime_procs"].status is ExtremeSourceCoverageStatus.PARTIAL
    assert sources["group_context"].status is ExtremeSourceCoverageStatus.CONTEXT_ONLY
    assert sources["encounter_context"].status is ExtremeSourceCoverageStatus.CONTEXT_ONLY
    assert all(
        sources[key].blocks_global_maximum
        for key in ("consumables", "runtime_procs", "group_context", "encounter_context")
    )


def test_reviewed_matrix_contains_every_current_objective_once():
    matrix = ExtremeObjectiveCoverageService.reviewed_matrix()

    assert tuple(row.objective_key for row in matrix) == (
        ExtremeObjectiveCoverageService.REVIEWED_OBJECTIVES
    )
    assert len({row.objective_key for row in matrix}) == len(matrix)


def test_unknown_objective_is_rejected_instead_of_inheriting_false_coverage():
    with pytest.raises(KeyError, match="unreviewed Extreme objective"):
        ExtremeObjectiveCoverageService.coverage_for("max_health")


def test_global_maximum_gate_can_open_only_after_source_universe_and_sources_are_reviewed():
    coverage = ExtremeObjectiveCoverage(
        objective_key="synthetic_complete_objective",
        source_universe_reviewed=True,
        sources=(
            ExtremeSourceFamilyCoverage(
                "class_skill_passives", ExtremeSourceCoverageStatus.REVIEWED
            ),
            ExtremeSourceFamilyCoverage(
                "race", ExtremeSourceCoverageStatus.REVIEWED
            ),
            ExtremeSourceFamilyCoverage(
                "encounter_context", ExtremeSourceCoverageStatus.NOT_APPLICABLE
            ),
        ),
    )

    assert coverage.blocking_sources == ()
    assert coverage.global_maximum_ready is True
    assert coverage.claim is ExtremeObjectiveClaim.GLOBAL_MAXIMUM_READY


def test_complete_reviewed_contract_can_be_reported_without_overclaiming_global_proof():
    coverage = ExtremeObjectiveCoverage(
        objective_key="synthetic_contract_complete_objective",
        source_universe_reviewed=False,
        sources=(
            ExtremeSourceFamilyCoverage(
                "class_skill_passives", ExtremeSourceCoverageStatus.REVIEWED
            ),
            ExtremeSourceFamilyCoverage(
                "race", ExtremeSourceCoverageStatus.NOT_APPLICABLE
            ),
        ),
    )

    assert coverage.blocking_sources == ()
    assert coverage.global_maximum_ready is False
    assert coverage.claim is ExtremeObjectiveClaim.COMPLETE_WITHIN_REVIEWED_SOURCE_CONTRACT


def test_reviewed_source_universe_with_a_partial_source_still_refuses_complete_claim():
    coverage = ExtremeObjectiveCoverage(
        objective_key="synthetic_partial_objective",
        source_universe_reviewed=True,
        sources=(
            ExtremeSourceFamilyCoverage(
                "class_skill_passives", ExtremeSourceCoverageStatus.REVIEWED
            ),
            ExtremeSourceFamilyCoverage(
                "gear_sets", ExtremeSourceCoverageStatus.PARTIAL
            ),
        ),
    )

    assert coverage.global_maximum_ready is False
    assert [row.source_family for row in coverage.blocking_sources] == ["gear_sets"]
    assert coverage.claim is ExtremeObjectiveClaim.BEST_REVIEWED_LOWER_BOUND
