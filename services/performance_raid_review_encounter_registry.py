from __future__ import annotations

"""Encounter adapter registry for Raid Review.

The generic review UI should not know about encounter-specific services. Each adapter
exposes a stable encounter key/display label and delegates fight discovery/review to
that encounter's application runner.

Adapters also expose a review level so baseline cross-pull support is never confused
with encounter-specific mechanic enrichment. Baseline adapters use the canonical
shared Raid Review pipeline but must not invent encounter mechanics that have not yet
been mapped to reviewed runtime evidence.
"""

from dataclasses import dataclass
from typing import Protocol

from services.performance_raid_review_lokkestiiz_runner_service import (
    PerformanceRaidReviewLokkestiizRunnerService,
)
from services.performance_raid_review_named_boss_runner_service import (
    PerformanceRaidReviewNamedBossRunnerService,
)


class RaidReviewEncounterAdapter(Protocol):
    key: str
    display_name: str
    review_level: str

    def list_fights(self, report_code: str): ...

    def review_report(self, report_code: str, fight_ids): ...


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewEncounterAdapter:
    runner: PerformanceRaidReviewLokkestiizRunnerService
    key: str = "lokkestiiz"
    display_name: str = "Lokkestiiz"
    review_level: str = "mechanic_enriched"

    def list_fights(self, report_code: str):
        return self.runner.list_lokkestiiz_fights(report_code)

    def review_report(self, report_code: str, fight_ids):
        return self.runner.review_report(report_code, fight_ids)


@dataclass(frozen=True, slots=True)
class XalvakkaRaidReviewEncounterAdapter:
    runner: PerformanceRaidReviewNamedBossRunnerService
    key: str = "xalvakka"
    display_name: str = "Xalvakka"
    review_level: str = "baseline"

    def list_fights(self, report_code: str):
        return self.runner.list_fights(report_code)

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
        review_level = str(getattr(adapter, "review_level", "") or "").strip().casefold()
        if review_level not in {"baseline", "mechanic_enriched"}:
            raise ValueError(
                "Raid Review encounter adapter review_level must be 'baseline' or 'mechanic_enriched'."
            )
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
        xalvakka_runner = PerformanceRaidReviewNamedBossRunnerService("Xalvakka")
        return cls(
            (
                LokkestiizRaidReviewEncounterAdapter(lokke_runner),
                XalvakkaRaidReviewEncounterAdapter(xalvakka_runner),
            )
        )


__all__ = [
    "RaidReviewEncounterAdapter",
    "LokkestiizRaidReviewEncounterAdapter",
    "XalvakkaRaidReviewEncounterAdapter",
    "RaidReviewEncounterRegistry",
]
