from __future__ import annotations

from pathlib import Path

import pytest

from services.btv_benchmark_evidence_service import (
    BTVBenchmarkEvidenceService,
    BTVBenchmarkObservation,
    UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME,
    UPTIME_DENOMINATOR_FULL_ENCOUNTER,
    UPTIME_DENOMINATOR_UNKNOWN,
)


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "encounter_research"
    / "btv_benchmarks"
    / "lokke_hm_20260907.json"
)


def _row(*, denominator: str, observed: float = 0.75) -> BTVBenchmarkObservation:
    return BTVBenchmarkObservation(
        encounter_key="example",
        encounter_label="Example",
        effect_key="major_slayer",
        page="insights",
        observed_ratio=observed,
        target_ratio=0.90,
        reference_average_ratio=None,
        theoretical_max_ratio=None,
        contribution_percent=None,
        player_role=None,
        source_file="example.png",
        source="test",
        uptime_denominator_basis=denominator,
    )


def test_lokke_fixture_loads_as_scoped_benchmark_evidence():
    corpus = BTVBenchmarkEvidenceService.load(FIXTURE)

    assert corpus.encounter_key == "lokke_hm"
    assert corpus.encounter_label == "Lokkestiiz hard mode"
    assert len(corpus.observations) == 25
    assert corpus.default_uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN


def test_unknown_btv_denominator_does_not_claim_boss_immunity_is_excluded():
    corpus = BTVBenchmarkEvidenceService.load(FIXTURE)
    insight = corpus.find(effect_key="major_slayer", page="insights")

    assert len(insight) == 1
    assert insight[0].uptime_denominator_basis == UPTIME_DENOMINATOR_UNKNOWN
    assert insight[0].excludes_boss_immunity_time is None


def test_damageable_time_denominator_explicitly_marks_immunity_as_excluded():
    assert _row(denominator=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME).excludes_boss_immunity_time is True


def test_full_encounter_denominator_explicitly_marks_immunity_as_included():
    assert _row(denominator=UPTIME_DENOMINATOR_FULL_ENCOUNTER).excludes_boss_immunity_time is False


def test_unknown_denominator_is_not_directly_comparable_even_to_unknown():
    left = _row(denominator=UPTIME_DENOMINATOR_UNKNOWN, observed=0.85)
    right = _row(denominator=UPTIME_DENOMINATOR_UNKNOWN, observed=0.75)

    assert left.comparable_uptime_with(right) is False


def test_full_encounter_and_damageable_boss_time_are_not_directly_comparable():
    full = _row(denominator=UPTIME_DENOMINATOR_FULL_ENCOUNTER, observed=0.85)
    damageable = _row(denominator=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME, observed=0.75)

    assert full.comparable_uptime_with(damageable) is False
    assert damageable.comparable_uptime_with(full) is False


def test_matching_known_denominators_are_directly_comparable():
    left = _row(denominator=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME, observed=0.85)
    right = _row(denominator=UPTIME_DENOMINATOR_DAMAGEABLE_BOSS_TIME, observed=0.75)

    assert left.comparable_uptime_with(right) is True


def test_same_effect_remains_separate_across_group_and_player_scope():
    corpus = BTVBenchmarkEvidenceService.load(FIXTURE)
    rows = corpus.find(effect_key="major_slayer")

    assert len(rows) == 2
    assert {(row.page, row.player_role, row.observed_ratio) for row in rows} == {
        ("insights", None, 0.56),
        ("buffs", "healer", 0.40),
    }


def test_targeted_insight_projects_to_uptime_policy_with_denominator_warning():
    corpus = BTVBenchmarkEvidenceService.load(FIXTURE)
    insight = corpus.find(effect_key="powerful_assault", page="insights")[0]

    policy = insight.to_uptime_policy()

    assert policy is not None
    assert policy.encounter_key == "lokke_hm"
    assert policy.target_ratio == pytest.approx(0.95)
    assert "uptime denominator=unknown" in policy.note


def test_reference_average_only_observation_does_not_become_target_policy():
    corpus = BTVBenchmarkEvidenceService.load(FIXTURE)
    healer_buff = corpus.find(
        effect_key="major_sorcery",
        page="buffs",
        player_role="healer",
    )[0]

    assert healer_buff.reference_average_ratio == pytest.approx(0.94)
    assert healer_buff.target_ratio is None
    assert healer_buff.to_uptime_policy() is None


def test_invalid_uptime_denominator_is_rejected():
    with pytest.raises(ValueError, match="uptime_denominator_basis"):
        _row(denominator="probably_boss_time")
