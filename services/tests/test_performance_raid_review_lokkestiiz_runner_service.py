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


class _FakeClient:
    def __init__(self, fights=None):
        self.fights = fights or []
        self.calls = []

    @staticmethod
    def normalize_report_code(value):
        return str(value).rstrip("/").split("/")[-1]

    def get_fights(self, report_code):
        self.calls.append(report_code)
        return list(self.fights)


class _FakePerformanceService:
    def __init__(self, client):
        self.client = client


class _FakeReviewService:
    def __init__(self, client=None):
        self.calls = []
        self.performance_service = _FakePerformanceService(client or _FakeClient())

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


def test_runner_lists_only_lokkestiiz_fights_in_fight_id_order() -> None:
    client = _FakeClient([
        {
            "id": 9,
            "name": "Lokkestiiz",
            "kill": False,
            "bossPercentage": 1234,
            "startTime": 5000,
            "endTime": 65000,
        },
        {"id": 2, "name": "Yolnahkriin", "kill": True, "startTime": 0, "endTime": 10000},
        {
            "id": 4,
            "name": "Lokkestiiz",
            "kill": True,
            "bossPercentage": 0,
            "startTime": 1000,
            "endTime": 31000,
        },
    ])
    review = _FakeReviewService(client)
    runner = PerformanceRaidReviewLokkestiizRunnerService(
        _FakeSettings(),
        review_service_factory=lambda: review,
    )

    rows = runner.list_lokkestiiz_fights("https://www.esologs.com/reports/ABC123")

    assert [row.fight_id for row in rows] == [4, 9]
    assert rows[0].kill is True
    assert rows[0].duration_seconds == 30.0
    assert rows[1].boss_percentage == 1234.0
    assert client.calls == ["ABC123"]


def test_runner_skips_lokkestiiz_rows_without_positive_fight_id() -> None:
    client = _FakeClient([
        {"id": 0, "name": "Lokkestiiz", "kill": False},
        {"id": None, "name": "Lokkestiiz", "kill": False},
        {"id": 6, "name": "Lokkestiiz", "kill": False},
    ])
    review = _FakeReviewService(client)
    runner = PerformanceRaidReviewLokkestiizRunnerService(
        _FakeSettings(),
        review_service_factory=lambda: review,
    )

    rows = runner.list_lokkestiiz_fights("ABC123")

    assert [row.fight_id for row in rows] == [6]
