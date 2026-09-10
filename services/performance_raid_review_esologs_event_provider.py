from __future__ import annotations

"""Read-only ESO Logs event provider for raid-review evidence.

The provider fetches one full fight event stream at most once per service instance,
then reuses that cached evidence for every consumer of the same fight. Observation
enrichment and encounter-specific review services should use this shared event stream
rather than fetching or caching parallel copies of runtime truth.

Raw numeric ability/resource IDs remain raw evidence. Semantic interpretation belongs
in higher layers, which already refuse unsupported inference.
"""

import json
from typing import Any

from services.performance_raid_review_event_enrichment_service import (
    PerformanceRaidReviewEventEnrichmentService,
    RaidReviewEventEnrichment,
)
from services.performance_raid_review_observation_service import RaidReviewSource


EVENT_QUERY = """
query RaidReviewEvents(
  $code: String!
  $fightIDs: [Int]!
  $startTime: Float!
  $endTime: Float!
  $includeResources: Boolean!
  $limit: Int!
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        includeResources: $includeResources
        limit: $limit
        translate: true
        useAbilityIDs: true
        useActorIDs: true
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


class PerformanceRaidReviewEsoLogsEventProvider:
    """Fetch and cache one authoritative raw event stream per reviewed fight."""

    def __init__(
        self,
        client,
        *,
        enrichment_service: PerformanceRaidReviewEventEnrichmentService | None = None,
        limit: int = 10_000,
        max_pages: int = 200,
    ) -> None:
        self.client = client
        self.enrichment_service = enrichment_service or PerformanceRaidReviewEventEnrichmentService()
        self.limit = max(100, min(int(limit), 10_000))
        self.max_pages = max(1, int(max_pages))
        self._fight_event_cache: dict[tuple[str, int, float, float], tuple[dict, ...]] = {}

    def resolve(self, source: RaidReviewSource, fight: dict) -> RaidReviewEventEnrichment:
        start = float(fight.get("startTime", 0.0) or 0.0)
        end = float(fight.get("endTime", 0.0) or 0.0)
        events = self.events_for_fight(
            report_code=source.report_code,
            fight_id=int(source.fight_id),
            start_time=start,
            end_time=end,
        )
        return self.enrichment_service.enrich(
            events,
            actor_id=int(source.actor_id),
            fight_start_time_ms=start,
            primary_resource_name=source.primary_resource_name,
        )

    def events_for_fight(
        self,
        *,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
    ) -> tuple[dict, ...]:
        """Return the shared complete raw event stream for one explicit fight.

        This is the public runtime-evidence contract for Raid Review consumers. The
        returned tuple is immutable at the collection level and is cached by exact
        report/fight clock identity. Partial pagination is never accepted.
        """

        start = float(start_time)
        end = float(end_time)
        if end <= start:
            raise ValueError(
                f"Fight {report_code} #{int(fight_id)} has invalid start/end timestamps."
            )
        return self._events_for_fight(
            report_code,
            int(fight_id),
            start,
            end,
        )

    def _events_for_fight(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
    ) -> tuple[dict, ...]:
        key = (
            str(report_code).strip(),
            int(fight_id),
            float(start_time),
            float(end_time),
        )
        cached = self._fight_event_cache.get(key)
        if cached is not None:
            return cached

        events: list[dict] = []
        page_start = float(start_time)
        exhausted = False

        for _ in range(self.max_pages):
            data = self.client._query(
                EVENT_QUERY,
                {
                    "code": key[0],
                    "fightIDs": [key[1]],
                    "startTime": page_start,
                    "endTime": float(end_time),
                    "includeResources": True,
                    "limit": self.limit,
                },
            )
            report = (data.get("reportData") or {}).get("report") or {}
            page = report.get("events") or {}
            rows = self._json_scalar(page.get("data")) or []
            if not isinstance(rows, list):
                rows = [rows]
            events.extend(row for row in rows if isinstance(row, dict))

            next_timestamp = page.get("nextPageTimestamp")
            if not next_timestamp or not rows:
                exhausted = True
                break
            next_timestamp = float(next_timestamp)
            if next_timestamp <= page_start or next_timestamp >= float(end_time):
                exhausted = True
                break
            page_start = next_timestamp

        if not exhausted:
            raise RuntimeError(
                f"ESO Logs event pagination exceeded {self.max_pages} pages for "
                f"{key[0]} #{key[1]}; enrichment was not accepted as complete."
            )

        result = tuple(events)
        self._fight_event_cache[key] = result
        return result

    @staticmethod
    def _json_scalar(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value


__all__ = ["PerformanceRaidReviewEsoLogsEventProvider"]
