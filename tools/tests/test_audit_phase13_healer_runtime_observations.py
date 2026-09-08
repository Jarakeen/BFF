from pathlib import Path

from services.rotation_healer_periodic_observation_fixture_service import (
    RotationHealerPeriodicObservationFixtureReport,
    RotationHealerPeriodicObservationFixtureEntry,
)
from services.rotation_healer_periodic_runtime_observation_service import (
    RotationHealerPeriodicObservedResolution,
    RotationHealerPeriodicObservedSample,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingResolution,
)
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from tools.audit_phase13_healer_runtime_observations import render_report


def _canonical():
    return RotationHealerCanonicalPeriodicTimingResolution(
        source_name="Budding Seeds",
        coefficient_number=2,
        skill_rank_id=6910,
        ability_id=93807,
        component_fragment="healed every 1 second",
        timing=SkillComponentRuntimeTiming(
            interval_seconds=1.0,
            bound_kind=RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW,
            evidence="every 1 second",
            source="canonical",
        ),
        duration_seconds=6.0,
        evidence=("canonical cadence",),
        unresolved=(),
    )


def _sample():
    return RotationHealerPeriodicObservedSample(
        source_name="Budding Seeds",
        coefficient_number=2,
        activation_time_seconds=10.0,
        observed_tick_times_seconds=(11.0, 12.0, 13.0, 14.0, 15.0, 16.0),
        observation_end_seconds=16.1,
        provenance=("reviewed combat-log sample A",),
        game_version="U50",
    )


def test_render_report_shows_promotable_first_tick_and_expiry_rule():
    observation = RotationHealerReviewedRuntimeObservation(
        source_name="Budding Seeds",
        coefficient_number=2,
        first_tick_offset_seconds=1.0,
        tick_on_expiry_boundary=True,
        provenance=("reviewed combat-log sample A",),
        game_version="U50",
    )
    report = RotationHealerPeriodicObservationFixtureReport(
        source_path="observations.json",
        schema_version=1,
        entries=(
            RotationHealerPeriodicObservationFixtureEntry(
                sample=_sample(),
                canonical=_canonical(),
                observed=RotationHealerPeriodicObservedResolution(
                    observation=observation,
                    evidence=("observed tick spacing agrees with canonical 1s cadence",),
                    unresolved=(),
                ),
            ),
        ),
        unresolved=(),
    )

    rendered = render_report(report)

    assert "promotable runtime observation: yes" in rendered
    assert "first tick offset: +1s" in rendered
    assert "tick on expiry:    yes" in rendered
    assert "refresh policy:    unresolved" in rendered
    assert "REPORT UNRESOLVED\n-----------------\nnone" in rendered


def test_render_report_keeps_incomplete_observation_unpromoted():
    report = RotationHealerPeriodicObservationFixtureReport(
        source_path="observations.json",
        schema_version=1,
        entries=(
            RotationHealerPeriodicObservationFixtureEntry(
                sample=_sample(),
                canonical=_canonical(),
                observed=RotationHealerPeriodicObservedResolution(
                    observation=None,
                    evidence=("reviewed combat-log sample A",),
                    unresolved=("observation does not extend through canonical expiry",),
                ),
            ),
        ),
        unresolved=(
            "sample 1 Budding Seeds coefficient 2: observation does not extend through canonical expiry",
        ),
    )

    rendered = render_report(report)

    assert "promotable runtime observation: no" in rendered
    assert "observation does not extend through canonical expiry" in rendered


def test_render_report_handles_empty_valid_entry_set():
    report = RotationHealerPeriodicObservationFixtureReport(
        source_path=str(Path("empty.json")),
        schema_version=1,
        entries=(),
        unresolved=("sample 1: provenance must be a string or list of strings",),
    )

    rendered = render_report(report)

    assert "No valid observation entries were loaded." in rendered
    assert "sample 1:" in rendered
