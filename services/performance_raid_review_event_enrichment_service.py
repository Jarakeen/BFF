from __future__ import annotations

"""Conservative event-derived enrichment for raid review observations.

This module intentionally understands only evidence that is explicit in the raw
ESO Logs event stream. Numeric resource type IDs and numeric ability IDs are not
promoted into semantic identities here. If ESO Logs does not provide a readable
resource/ability name, the corresponding coaching field stays unresolved.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RaidReviewEventEnrichment:
    death_count: int = 0
    first_death_seconds: float | None = None
    first_death_ability: str = ""
    minimum_primary_resource_percent: float | None = None
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewEventEnrichmentService:
    """Extract death and named resource evidence from raw fight events."""

    _DEATH_TYPES = {"death"}
    _DAMAGE_TYPES = {"damage", "calculateddamage"}

    def enrich(
        self,
        events: Iterable[dict],
        *,
        actor_id: int,
        fight_start_time_ms: float,
        primary_resource_name: str = "",
    ) -> RaidReviewEventEnrichment:
        rows = tuple(event for event in events if isinstance(event, dict))
        actor_id = int(actor_id)
        start = float(fight_start_time_ms)

        deaths = [
            event
            for event in rows
            if self._event_type(event) in self._DEATH_TYPES
            and self._int_or_none(event.get("targetID")) == actor_id
        ]
        deaths.sort(key=self._timestamp)

        first_death_seconds: float | None = None
        first_death_ability = ""
        if deaths:
            first = deaths[0]
            first_time = self._timestamp(first)
            first_death_seconds = max(0.0, (first_time - start) / 1000.0)
            first_death_ability = self._ability_name(first)
            if not first_death_ability:
                first_death_ability = self._preceding_named_damage_cause(
                    rows,
                    actor_id=actor_id,
                    death_timestamp=first_time,
                )

        unresolved: list[str] = []
        minimum_resource: float | None = None
        requested_resource = str(primary_resource_name or "").strip()
        if requested_resource:
            samples = self._named_resource_percent_samples(
                rows,
                actor_id=actor_id,
                resource_name=requested_resource,
            )
            if samples:
                minimum_resource = min(samples)
            else:
                unresolved.append(
                    f"No explicit named {requested_resource} resource snapshots were present for actor {actor_id}; numeric resource type IDs were not inferred."
                )

        return RaidReviewEventEnrichment(
            death_count=len(deaths),
            first_death_seconds=first_death_seconds,
            first_death_ability=first_death_ability,
            minimum_primary_resource_percent=minimum_resource,
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _event_type(event: dict) -> str:
        return str(event.get("type") or "").strip().casefold()

    @staticmethod
    def _timestamp(event: dict) -> float:
        try:
            return float(event.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _int_or_none(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ability_name(event: dict) -> str:
        for key in ("abilityName", "name"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        ability = event.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        elif isinstance(ability, str) and ability.strip():
            return ability.strip()

        return ""

    def _preceding_named_damage_cause(
        self,
        rows: tuple[dict, ...],
        *,
        actor_id: int,
        death_timestamp: float,
        window_ms: float = 2500.0,
    ) -> str:
        candidates: list[dict] = []
        lower = death_timestamp - float(window_ms)
        for event in rows:
            timestamp = self._timestamp(event)
            if timestamp < lower or timestamp > death_timestamp:
                continue
            if self._event_type(event) not in self._DAMAGE_TYPES:
                continue
            if self._int_or_none(event.get("targetID")) != actor_id:
                continue
            if not self._ability_name(event):
                continue
            candidates.append(event)

        if not candidates:
            return ""
        candidates.sort(key=self._timestamp)
        return self._ability_name(candidates[-1])

    def _named_resource_percent_samples(
        self,
        rows: tuple[dict, ...],
        *,
        actor_id: int,
        resource_name: str,
    ) -> list[float]:
        wanted = resource_name.strip().casefold()
        samples: list[float] = []

        for event in rows:
            event_actor_ids = {
                value
                for value in (
                    self._int_or_none(event.get("sourceID")),
                    self._int_or_none(event.get("targetID")),
                )
                if value is not None
            }
            if actor_id not in event_actor_ids:
                continue

            resources = event.get("resources")
            if isinstance(resources, list):
                for resource in resources:
                    if not isinstance(resource, dict):
                        continue
                    if self._resource_name(resource) != wanted:
                        continue
                    percent = self._resource_percent(resource)
                    if percent is not None:
                        samples.append(percent)

            top_level_name = self._resource_name(event)
            if top_level_name == wanted:
                percent = self._resource_percent(event)
                if percent is not None:
                    samples.append(percent)

        return samples

    @staticmethod
    def _resource_name(row: dict) -> str:
        for key in (
            "resourceTypeName",
            "resourceName",
            "resourceType",
            "typeName",
        ):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().casefold()
        return ""

    @staticmethod
    def _resource_percent(row: dict) -> float | None:
        current = None
        maximum = None

        for key in ("resourceAmount", "currentAmount", "current", "amountCurrent"):
            value = row.get(key)
            if isinstance(value, (int, float)):
                current = float(value)
                break

        for key in ("maxResourceAmount", "maxAmount", "maximum", "max"):
            value = row.get(key)
            if isinstance(value, (int, float)):
                maximum = float(value)
                break

        if current is None or maximum is None or maximum <= 0:
            return None
        return max(0.0, min(100.0, (current / maximum) * 100.0))


__all__ = [
    "PerformanceRaidReviewEventEnrichmentService",
    "RaidReviewEventEnrichment",
]
