from __future__ import annotations

"""Generic application runner for Raid Review encounter adapters.

The UI supplies an encounter key, report code/URL, and selected fight IDs. This
facade delegates discovery and review to the registered encounter adapter so UI code
does not need encounter-specific runner method names.

Fight discovery also establishes the evidence-selection context used by the picker.
If the encounter or report input changes after fights were loaded, the runner fails
closed instead of reviewing stale fight IDs against a different source.
"""

from dataclasses import dataclass

from services.performance_raid_review_encounter_registry import (
    RaidReviewEncounterRegistry,
)


@dataclass(frozen=True, slots=True)
class RaidReviewEncounterChoice:
    key: str
    display_name: str
    review_level: str
    trial_key: str
    trial_display_name: str
    boss_order: int


class PerformanceRaidReviewRunnerService:
    """Encounter-neutral Raid Review application facade."""

    def __init__(self, registry: RaidReviewEncounterRegistry | None = None) -> None:
        self.registry = registry or RaidReviewEncounterRegistry.default()
        self._loaded_selection_context: tuple[str, str] | None = None

    @staticmethod
    def _selection_context(encounter_key: str, report_code: str) -> tuple[str, str]:
        return (
            str(encounter_key or "").strip().casefold(),
            str(report_code or "").strip(),
        )

    def available_encounters(self) -> tuple[RaidReviewEncounterChoice, ...]:
        return tuple(
            RaidReviewEncounterChoice(
                key=str(adapter.key),
                display_name=str(adapter.display_name),
                review_level=str(adapter.review_level),
                trial_key=str(adapter.trial_key),
                trial_display_name=str(adapter.trial_display_name),
                boss_order=int(adapter.boss_order),
            )
            for adapter in self.registry.available()
        )

    def list_fights(self, encounter_key: str, report_code: str):
        adapter = self.registry.get(encounter_key)
        self._loaded_selection_context = None
        fights = adapter.list_fights(report_code)
        self._loaded_selection_context = self._selection_context(encounter_key, report_code)
        return fights

    def review_report(self, encounter_key: str, report_code: str, fight_ids):
        adapter = self.registry.get(encounter_key)
        requested_context = self._selection_context(encounter_key, report_code)
        if (
            self._loaded_selection_context is not None
            and requested_context != self._loaded_selection_context
        ):
            raise RuntimeError(
                "Raid Review encounter/report changed after fights were loaded. "
                "Load fights again before running the review."
            )
        return adapter.review_report(report_code, tuple(int(value) for value in fight_ids))


__all__ = [
    "RaidReviewEncounterChoice",
    "PerformanceRaidReviewRunnerService",
]
