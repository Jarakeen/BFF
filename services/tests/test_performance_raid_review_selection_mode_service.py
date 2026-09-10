from __future__ import annotations

from services.performance_raid_review_selection_mode_service import (
    PerformanceRaidReviewSelectionModeService,
)


def test_no_selected_pulls_has_no_comparison_capability() -> None:
    mode = PerformanceRaidReviewSelectionModeService.classify(())

    assert mode.key == "none"
    assert mode.selected_pull_count == 0
    assert mode.supports_repeated_patterns is False
    assert mode.supports_cross_pull_comparison is False


def test_one_pull_is_explicit_single_pull_review() -> None:
    mode = PerformanceRaidReviewSelectionModeService.classify((7,))

    assert mode.key == "single_pull"
    assert mode.display_name == "Single-pull review"
    assert mode.selected_pull_count == 1
    assert mode.supports_repeated_patterns is False
    assert mode.supports_cross_pull_comparison is False
    assert "kill-vs-wipe comparisons are unavailable" in mode.note


def test_multiple_pulls_enable_cross_pull_mode_without_promising_findings() -> None:
    mode = PerformanceRaidReviewSelectionModeService.classify((7, 8, 9))

    assert mode.key == "cross_pull"
    assert mode.display_name == "Cross-pull review"
    assert mode.selected_pull_count == 3
    assert mode.supports_repeated_patterns is True
    assert mode.supports_cross_pull_comparison is True
    assert "where the underlying analyzer has enough comparable evidence" in mode.note


def test_duplicate_or_nonpositive_fight_ids_do_not_inflate_selection_mode() -> None:
    mode = PerformanceRaidReviewSelectionModeService.classify((7, 7, 0, -3))

    assert mode.key == "single_pull"
    assert mode.selected_pull_count == 1
