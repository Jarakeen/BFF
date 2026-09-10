from __future__ import annotations

"""Evidence-mode classification for Raid Review pull selections.

One pull can support observations about that pull, but it cannot support claims about
repeat patterns or kill-vs-wipe differences. Multi-pull mode enables comparison only
where downstream analyzers also meet their own evidence thresholds.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RaidReviewSelectionMode:
    selected_pull_count: int
    key: str
    display_name: str
    supports_repeated_patterns: bool
    supports_cross_pull_comparison: bool
    note: str


class PerformanceRaidReviewSelectionModeService:
    """Classify selected pulls without inventing comparison evidence."""

    @staticmethod
    def classify(fight_ids: Iterable[int]) -> RaidReviewSelectionMode:
        unique_ids = tuple(dict.fromkeys(int(value) for value in fight_ids if int(value) > 0))
        count = len(unique_ids)

        if count == 0:
            return RaidReviewSelectionMode(
                selected_pull_count=0,
                key="none",
                display_name="No pulls selected",
                supports_repeated_patterns=False,
                supports_cross_pull_comparison=False,
                note="Select at least one pull to run Raid Review.",
            )

        if count == 1:
            return RaidReviewSelectionMode(
                selected_pull_count=1,
                key="single_pull",
                display_name="Single-pull review",
                supports_repeated_patterns=False,
                supports_cross_pull_comparison=False,
                note=(
                    "Single-pull review can describe this pull, but repeated-pattern and "
                    "kill-vs-wipe comparisons are unavailable. Select multiple pulls for "
                    "cross-pull coaching."
                ),
            )

        return RaidReviewSelectionMode(
            selected_pull_count=count,
            key="cross_pull",
            display_name="Cross-pull review",
            supports_repeated_patterns=True,
            supports_cross_pull_comparison=True,
            note=(
                f"{count} pulls selected. Cross-pull patterns may be evaluated where the "
                "underlying analyzer has enough comparable evidence."
            ),
        )


__all__ = [
    "RaidReviewSelectionMode",
    "PerformanceRaidReviewSelectionModeService",
]
