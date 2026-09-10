from __future__ import annotations

from services.performance_raid_review_lokkestiiz_runner_service import (
    PerformanceRaidReviewLokkestiizRunnerService,
)


class _FakeSettings:
    def __init__(self):
        self.calls = 0

    def load(self):
        self.calls += 1
        return {"EsoLogsClientId": "id", "EsoLogsClientSecret": "secret"}


class _FakeReviewService:
    def __init__(self):
        self.calls = []

    def review_report(self, report_code, fight_ids):
        self.calls.append((report_code, tuple(fight_ids)))
        return "review-result"


def test_runner_delegates_report_and_fights_to_application_service() -> None:
    review = _FakeReviewService()
    runner = PerformanceRaidReviewLokkestiizRunnerService(
        _FakeSettings(),
        review_service_factory=lambda: review,
    )

    result = runner.review_report("ABC123", [4, 8, 9])

    assert result == "review-result"
    assert review.calls == [("ABC123", (4, 8, 9))]


def test_runner_normalizes_fight_ids_to_ints() -> None:
    review = _FakeReviewService()
    runner = PerformanceRaidReviewLokkestiizRunnerService(
        _FakeSettings(),
        review_service_factory=lambda: review,
    )

    runner.review_report("ABC123", ["4", 8])

    assert review.calls == [("ABC123", (4, 8))]
