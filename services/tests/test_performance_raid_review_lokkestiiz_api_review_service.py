from __future__ import annotations

from types import SimpleNamespace

from services.performance_raid_review_lokkestiiz_api_review_service import (
    PerformanceRaidReviewLokkestiizApiReviewService,
)


class _Intake:
    def __init__(self, pulls, unresolved=()):
        self.result = SimpleNamespace(pulls=tuple(pulls), unresolved=tuple(unresolved))
        self.calls = []

    def build(self, report_code, fight_ids):
        self.calls.append((report_code, tuple(fight_ids)))
        return self.result


class _Session:
    def __init__(self, unresolved=()):
        self.result = SimpleNamespace(review=SimpleNamespace(synthesis=object()), unresolved=tuple(unresolved))
        self.calls = []

    def review(self, pulls):
        self.calls.append(tuple(pulls))
        return self.result


def test_composes_api_intake_and_existing_session_engine() -> None:
    pulls = (SimpleNamespace(fight_id=3), SimpleNamespace(fight_id=4))
    intake = _Intake(pulls)
    session = _Session()
    service = PerformanceRaidReviewLokkestiizApiReviewService(
        SimpleNamespace(client=SimpleNamespace()),
        intake_service=intake,
        session_service=session,
    )

    result = service.review_report("ABC", [3, 4])

    assert intake.calls == [("ABC", (3, 4))]
    assert session.calls == [pulls]
    assert result.session is session.result
    assert result.review is session.result.review
    assert result.unresolved == ()


def test_does_not_run_session_when_intake_has_no_valid_pulls() -> None:
    intake = _Intake((), unresolved=("no valid pulls",))
    session = _Session()
    service = PerformanceRaidReviewLokkestiizApiReviewService(
        SimpleNamespace(client=SimpleNamespace()),
        intake_service=intake,
        session_service=session,
    )

    result = service.review_report("ABC", [99])

    assert session.calls == []
    assert result.session is None
    assert result.review is None
    assert result.unresolved == ("no valid pulls",)


def test_combines_intake_and_session_unresolved_without_duplicates() -> None:
    intake = _Intake((SimpleNamespace(fight_id=3),), unresolved=("skipped fight 2", "shared"))
    session = _Session(unresolved=("shared", "missing aura"))
    service = PerformanceRaidReviewLokkestiizApiReviewService(
        SimpleNamespace(client=SimpleNamespace()),
        intake_service=intake,
        session_service=session,
    )

    result = service.review_report("ABC", [2, 3])

    assert result.unresolved == ("skipped fight 2", "shared", "missing aura")
