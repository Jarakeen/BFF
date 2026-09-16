from __future__ import annotations

import pytest

from minmax.resource_costs import ResourceType
from minmax.sustain_result import SustainFailure, SustainResult
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.extreme_resource_timeline_record_service import (
    ExtremeResourceTimelineRecordService,
)


def _sustain(*, starting: int, ending: int, minimum: int, sustains: bool = True) -> SustainResult:
    failure = None
    if not sustains:
        failure = SustainFailure(
            time_seconds=8.0,
            source="fixture cast",
            shortfall=250,
            resource_before=500,
            attempted_cost=750,
        )
    return SustainResult(
        resource=ResourceType.MAGICKA,
        sustains=sustains,
        starting_amount=starting,
        ending_amount=ending,
        ending_margin=ending,
        minimum_amount=minimum,
        first_failure=failure,
        total_cost_attempted=0,
        total_cost_paid=0,
        total_restoration_applied=0,
        total_restoration_wasted=0,
    )


def test_resource_sustain_projects_net_change_over_explicit_window() -> None:
    record = ExtremeResourceTimelineRecordService.resource_sustain(
        _sustain(starting=30000, ending=36000, minimum=22000),
        duration_seconds=30.0,
    )

    assert record.net_resource == 6000
    assert record.net_resource_per_second == pytest.approx(200.0)
    assert record.minimum_amount == 22000
    assert record.mechanic_complete is True


def test_resource_sustain_preserves_shortfall_as_blocker() -> None:
    record = ExtremeResourceTimelineRecordService.resource_sustain(
        _sustain(starting=30000, ending=0, minimum=0, sustains=False),
        duration_seconds=10.0,
    )

    assert record.mechanic_complete is False
    assert any("resource shortfall" in item for item in record.unresolved)


def test_ultimate_generation_scores_explicit_events_without_inventing_spend() -> None:
    record = ExtremeResourceTimelineRecordService.ultimate_generation(
        (
            UltimateGenerationEvent(1.0, 3.0, "light attack"),
            UltimateGenerationEvent(5.0, 6.0, "heroism"),
            UltimateGenerationEvent(9.0, 3.0, "light attack"),
        ),
        duration_seconds=12.0,
    )

    assert record.total_generated == pytest.approx(12.0)
    assert record.generated_per_second == pytest.approx(1.0)
    assert record.event_count == 3
    assert record.mechanic_complete is True


def test_ultimate_generation_rejects_events_after_window() -> None:
    with pytest.raises(ValueError, match="cannot occur after Extreme timeline duration"):
        ExtremeResourceTimelineRecordService.ultimate_generation(
            (UltimateGenerationEvent(11.0, 3.0, "late event"),),
            duration_seconds=10.0,
        )
