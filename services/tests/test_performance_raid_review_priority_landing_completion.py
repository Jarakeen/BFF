from services.performance_raid_review_priority_service import PerformanceRaidReviewPriorityService
from services.performance_raid_review_service import RaidReviewFinding


def _finding(category: str, title: str) -> RaidReviewFinding:
    return RaidReviewFinding(
        scope="player",
        subject="Tank One",
        role="Tank",
        category=category,
        priority="medium",
        title=title,
        evidence="reviewed evidence",
        recommendation="review the landing sequence",
        confidence="medium",
    )


def test_landing_recovery_completion_shares_landing_execution_priority_theme() -> None:
    result = PerformanceRaidReviewPriorityService().rank(
        (
            _finding("landing_recovery_completion", "Boss Control is missed more often on wipe pulls"),
            _finding("landing_recovery", "Boss Control is slower on wipe pulls"),
        )
    )

    assert len(result) == 1
    assert result[0].category == "landing_recovery_completion"
