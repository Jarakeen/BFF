from __future__ import annotations

"""Generic application runner for Raid Review encounter adapters.

The UI supplies an encounter key, report code/URL, and selected fight IDs. This
facade delegates discovery and review to the registered encounter adapter so UI code
does not need encounter-specific runner method names.
"""

from dataclasses import dataclass

from services.performance_raid_review_encounter_registry import (
    RaidReviewEncounterRegistry,
)


@dataclass(frozen=True, slots=True)
class RaidReviewEncounterChoice:
    key: str
    display_name: str


class PerformanceRaidReviewRunnerService:
    """Encounter-neutral Raid Review application facade."""

    def __init__(self, registry: RaidReviewEncounterRegistry | None = None) -> None:
        self.registry = registry or RaidReviewEncounterRegistry.default()

    def available_encounters(self) -> tuple[RaidReviewEncounterChoice, ...]:
        return tuple(
            RaidReviewEncounterChoice(
                key=str(adapter.key),
                display_name=str(adapter.display_name),
            )
            for adapter in self.registry.available()
        )

    def list_fights(self, encounter_key: str, report_code: str):
        adapter = self.registry.get(encounter_key)
        return adapter.list_fights(report_code)

    def review_report(self, encounter_key: str, report_code: str, fight_ids):
        adapter = self.registry.get(encounter_key)
        return adapter.review_report(report_code, tuple(int(value) for value in fight_ids))


__all__ = [
    "RaidReviewEncounterChoice",
    "PerformanceRaidReviewRunnerService",
]
