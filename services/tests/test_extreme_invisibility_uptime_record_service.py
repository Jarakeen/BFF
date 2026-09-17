from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_invisibility_gear_provider_service import (
    ExtremeReviewedInvisibilityGearProvider,
)
from services.extreme_invisibility_uptime_record_service import (
    ExtremeInvisibilityUptimeRecordService,
)


class _GearProviders:
    def reviewed_providers(self):
        return (
            ExtremeReviewedInvisibilityGearProvider(
                name="Prowler's Talisman",
                entity_id="prowlers_talisman",
                duration_seconds=10.0,
                cooldown_seconds=45.0,
                evidence=(
                    "Prowler's Talisman 1pc: 10s invisibility",
                    "Prowler's Talisman 1pc: once every 45s",
                ),
            ),
        )


class _NoProviders:
    def reviewed_providers(self):
        return ()


def test_prowlers_constructive_schedule_reuses_interval_coverage() -> None:
    result = ExtremeInvisibilityUptimeRecordService(
        "unused.db",
        gear_providers=_GearProviders(),
    ).evaluate(duration_seconds=100.0)

    # Windows are [0,10], [45,55], [90,100] after clipping.
    assert result.provider is not None
    assert result.provider.name == "Prowler's Talisman"
    assert result.covered_seconds == pytest.approx(30.0)
    assert result.uptime_ratio == pytest.approx(0.30)
    assert result.window_count == 3
    assert result.mechanic_complete is False
    assert "provider corpus" in result.unresolved[0].casefold()


def test_partial_last_window_is_clipped_to_requested_horizon() -> None:
    result = ExtremeInvisibilityUptimeRecordService(
        "unused.db",
        gear_providers=_GearProviders(),
    ).evaluate(duration_seconds=50.0)

    # [0,10] plus [45,50] = 15 seconds covered.
    assert result.covered_seconds == pytest.approx(15.0)
    assert result.uptime_ratio == pytest.approx(0.30)
    assert result.window_count == 2


def test_no_reviewed_provider_fails_closed() -> None:
    result = ExtremeInvisibilityUptimeRecordService(
        "unused.db",
        gear_providers=_NoProviders(),
    ).evaluate(duration_seconds=60.0)

    assert result.provider is None
    assert result.covered_seconds == 0.0
    assert result.uptime_ratio == 0.0
    assert result.mechanic_complete is False
    assert "No reviewed legal invisibility provider" in result.unresolved[0]


def test_invalid_horizon_is_rejected_before_fake_uptime_can_be_reported() -> None:
    service = ExtremeInvisibilityUptimeRecordService(
        "unused.db",
        gear_providers=_GearProviders(),
    )
    with pytest.raises(ValueError, match="duration must be greater than zero"):
        service.evaluate(duration_seconds=0.0)
