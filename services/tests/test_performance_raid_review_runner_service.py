from __future__ import annotations

from dataclasses import dataclass

from services.performance_raid_review_encounter_registry import RaidReviewEncounterRegistry
from services.performance_raid_review_runner_service import PerformanceRaidReviewRunnerService


@dataclass(frozen=True)
class _Adapter:
    key: str
    display_name: str
    review_level: str = "baseline"
    trial_key: str = "test_trial"
    trial_display_name: str = "Test Trial"
    boss_order: int = 1

    def list_fights(self, report_code):
        return (self.key, report_code, "fights")

    def review_report(self, report_code, fight_ids):
        return (self.key, report_code, tuple(fight_ids), "review")


def test_available_encounters_comes_from_registry_with_trial_metadata() -> None:
    registry = RaidReviewEncounterRegistry((
        _Adapter("zeta", "Zeta", trial_key="trial_b", trial_display_name="Trial B", boss_order=2),
        _Adapter("alpha", "Alpha", trial_key="trial_a", trial_display_name="Trial A", boss_order=1),
    ))
    runner = PerformanceRaidReviewRunnerService(registry)

    choices = runner.available_encounters()

    assert [
        (
            row.key,
            row.display_name,
            row.review_level,
            row.trial_key,
            row.trial_display_name,
            row.boss_order,
        )
        for row in choices
    ] == [
        ("alpha", "Alpha", "baseline", "trial_a", "Trial A", 1),
        ("zeta", "Zeta", "baseline", "trial_b", "Trial B", 2),
    ]


def test_list_fights_delegates_to_selected_adapter() -> None:
    runner = PerformanceRaidReviewRunnerService(
        RaidReviewEncounterRegistry((_Adapter("alpha", "Alpha"),))
    )

    result = runner.list_fights("alpha", "ABC123")

    assert result == ("alpha", "ABC123", "fights")


def test_review_report_delegates_selected_fights_to_adapter() -> None:
    runner = PerformanceRaidReviewRunnerService(
        RaidReviewEncounterRegistry((_Adapter("alpha", "Alpha"),))
    )

    result = runner.review_report("alpha", "ABC123", ["4", 8])

    assert result == ("alpha", "ABC123", (4, 8), "review")


def test_review_report_rejects_stale_report_after_fights_were_loaded() -> None:
    runner = PerformanceRaidReviewRunnerService(
        RaidReviewEncounterRegistry((_Adapter("alpha", "Alpha"),))
    )
    runner.list_fights("alpha", "REPORT_A")

    try:
        runner.review_report("alpha", "REPORT_B", [4, 8])
    except RuntimeError as exc:
        assert "Load fights again" in str(exc)
    else:
        raise AssertionError("Stale report fight selection should fail closed.")


def test_review_report_rejects_stale_encounter_after_fights_were_loaded() -> None:
    runner = PerformanceRaidReviewRunnerService(
        RaidReviewEncounterRegistry((
            _Adapter("alpha", "Alpha", boss_order=1),
            _Adapter("beta", "Beta", boss_order=2),
        ))
    )
    runner.list_fights("alpha", "ABC123")

    try:
        runner.review_report("beta", "ABC123", [4, 8])
    except RuntimeError as exc:
        assert "Load fights again" in str(exc)
    else:
        raise AssertionError("Stale encounter fight selection should fail closed.")


def test_failed_fight_reload_clears_previous_selection_context() -> None:
    @dataclass(frozen=True)
    class _FailingAdapter(_Adapter):
        def list_fights(self, report_code):
            raise RuntimeError("API unavailable")

    good = _Adapter("alpha", "Alpha", boss_order=1)
    failing = _FailingAdapter("beta", "Beta", boss_order=2)
    runner = PerformanceRaidReviewRunnerService(
        RaidReviewEncounterRegistry((good, failing))
    )
    runner.list_fights("alpha", "REPORT_A")

    try:
        runner.list_fights("beta", "REPORT_B")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected failing adapter to raise.")

    result = runner.review_report("beta", "REPORT_B", [7])
    assert result == ("beta", "REPORT_B", (7,), "review")


def test_unknown_encounter_fails_closed_through_registry() -> None:
    runner = PerformanceRaidReviewRunnerService(RaidReviewEncounterRegistry())

    try:
        runner.list_fights("missing", "ABC123")
    except KeyError as exc:
        assert "not supported" in str(exc)
    else:
        raise AssertionError("Unknown encounter should fail closed.")
