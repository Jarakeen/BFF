from __future__ import annotations

"""Encounter adapter registry for Raid Review.

The generic review UI should not know about encounter-specific services. Each adapter
exposes a stable encounter key/display label and delegates fight discovery/review to
that encounter's application runner. Unsupported encounters remain unsupported until
reviewed mechanics exist for them.
"""

from dataclasses import dataclass
from typing import Protocol

from services.performance_raid_review_lokkestiiz_runner_service import (
    PerformanceRaidReviewLokkestiizRunnerService,
)


class RaidReviewEncounterAdapter(Protocol):
    key: str
    display_name: str

    def list_fights(self, report_code: str): ...

    def review_report(self, report_code: str, fight_ids): ...


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewEncounterAdapter:
    runner: PerformanceRaidReviewLokkestiizRunnerService
    key: str = "lokkestiiz"
    display_name: str = "Lokkestiiz"

    def list_fights(self, report_code: str):
        return self.runner.list_lokkestiiz_fights(report_code)

    def review_report(self, report_code: str, fight_ids):
        return self.runner.review_report(report_code, fight_ids)


class RaidReviewEncounterRegistry:
    """Deterministic registry of encounters with reviewed Raid Review support."""

    def __init__(self, adapters=()) -> None:
        self._adapters: dict[str, RaidReviewEncounterAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: RaidReviewEncounterAdapter) -> None:
        key = str(adapter.key or "").strip().casefold()
        if not key:
            raise ValueError("Raid Review encounter adapter requires a non-empty key.")
        if key in self._adapters:
            raise ValueError(f"Raid Review encounter adapter {key!r} is already registered.")
        self._adapters[key] = adapter

    def get(self, key: str) -> RaidReviewEncounterAdapter:
        normalized = str(key or "").strip().casefold()
        try:
            return self._adapters[normalized]
        except KeyError as exc:
            raise KeyError(f"Raid Review encounter {normalized!r} is not supported.") from exc

    def available(self) -> tuple[RaidReviewEncounterAdapter, ...]:
        return tuple(
            sorted(
                self._adapters.values(),
                key=lambda adapter: (adapter.display_name.casefold(), adapter.key),
            )
        )

    @classmethod
    def default(cls) -> "RaidReviewEncounterRegistry":
        lokke_runner = PerformanceRaidReviewLokkestiizRunnerService()
        return cls((LokkestiizRaidReviewEncounterAdapter(lokke_runner),))


__all__ = [
    "RaidReviewEncounterAdapter",
    "LokkestiizRaidReviewEncounterAdapter",
    "RaidReviewEncounterRegistry",
]
