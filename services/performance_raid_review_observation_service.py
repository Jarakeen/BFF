from __future__ import annotations

"""Fresh ESO Logs observation collection for cross-pull raid review.

This service deliberately reuses shared Performance data contracts rather than
persisting computed snapshots. Sources are explicit and actor IDs remain scoped to
their report. A stable member_key is required from the caller when the same person is
linked across reports.

Optional snapshot/fight resolvers let the production coordinator reuse one lean,
cached per-pull fetch path. Tests and other callers may omit them and retain the
existing PerformanceDashboardService behavior.

Optional event enrichment is additive. A failure to collect death/resource evidence
never erases an otherwise valid base performance observation.
"""

from dataclasses import dataclass
from typing import Callable, Iterable

from services.performance_raid_review_event_enrichment_service import (
    RaidReviewEventEnrichment,
)
from services.performance_raid_review_service import RaidReviewObservation


@dataclass(frozen=True, slots=True)
class RaidReviewSource:
    report_code: str
    fight_id: int
    actor_id: int
    actor_label: str
    role: str
    member_key: str = ""
    immunity_buff_name: str = ""
    immunity_buff_kind: str = "Buff"
    primary_resource_name: str = ""


@dataclass(frozen=True, slots=True)
class RaidReviewCollectionResult:
    observations: tuple[RaidReviewObservation, ...]
    unresolved: tuple[str, ...] = ()


RaidReviewEnrichmentResolver = Callable[
    [RaidReviewSource, dict],
    RaidReviewEventEnrichment,
]
RaidReviewSnapshotResolver = Callable[..., object]
RaidReviewFightResolver = Callable[[str, int], dict]


class PerformanceRaidReviewObservationService:
    """Build fresh review observations from explicit ESO Logs actor/fight sources."""

    def __init__(
        self,
        performance_service,
        *,
        enrichment_resolver: RaidReviewEnrichmentResolver | None = None,
        snapshot_resolver: RaidReviewSnapshotResolver | None = None,
        fight_resolver: RaidReviewFightResolver | None = None,
    ):
        self.performance_service = performance_service
        self.enrichment_resolver = enrichment_resolver
        self.snapshot_resolver = snapshot_resolver or performance_service.build_snapshot
        self.fight_resolver = fight_resolver or performance_service.client.get_fight

    def collect(
        self,
        sources: Iterable[RaidReviewSource],
    ) -> RaidReviewCollectionResult:
        observations: list[RaidReviewObservation] = []
        unresolved: list[str] = []

        for source in sources:
            try:
                fight = self.fight_resolver(
                    source.report_code,
                    int(source.fight_id),
                )
                snapshot = self.snapshot_resolver(
                    source.report_code,
                    int(source.fight_id),
                    int(source.actor_id),
                    source.actor_label,
                    source.role,
                    immunity_buff_name=source.immunity_buff_name,
                    immunity_buff_kind=source.immunity_buff_kind,
                )
            except Exception as exc:
                unresolved.append(
                    f"{source.report_code} #{source.fight_id} {source.actor_label}: {exc}"
                )
                continue

            uptimes: dict[str, float] = {}
            for rows in (
                getattr(snapshot, "BuffUptimes", ()),
                getattr(snapshot, "DebuffUptimes", ()),
                getattr(snapshot, "RaidDebuffUptimes", ()),
            ):
                for row in rows or ():
                    name = str(getattr(row, "Name", "") or "").strip()
                    if not name:
                        continue
                    percent = float(getattr(row, "UptimePercent", 0.0) or 0.0)
                    # Same named ESO effect can arrive under multiple raw IDs/tables.
                    # Keep the strongest named observation rather than summing duplicates.
                    uptimes[name] = max(percent, uptimes.get(name, 0.0))

            enrichment = RaidReviewEventEnrichment()
            if self.enrichment_resolver is not None:
                try:
                    enrichment = self.enrichment_resolver(source, fight)
                except Exception as exc:
                    unresolved.append(
                        f"{source.report_code} #{source.fight_id} {source.actor_label} enrichment: {exc}"
                    )
                else:
                    unresolved.extend(
                        f"{source.report_code} #{source.fight_id} {source.actor_label}: {message}"
                        for message in enrichment.unresolved
                    )

            observations.append(
                RaidReviewObservation(
                    report_code=str(source.report_code),
                    fight_id=int(source.fight_id),
                    fight_name=str(
                        getattr(snapshot, "FightName", "")
                        or fight.get("name")
                        or ""
                    ),
                    kill=bool(fight.get("kill")),
                    actor_id=int(source.actor_id),
                    actor_label=str(source.actor_label),
                    role=str(getattr(snapshot, "Role", source.role) or source.role),
                    fight_duration_seconds=float(
                        getattr(snapshot, "FightDurationSeconds", 0.0) or 0.0
                    ),
                    member_key=str(source.member_key),
                    output_total=float(
                        getattr(snapshot, "OutputTotal", 0.0) or 0.0
                    ),
                    output_per_second=float(
                        getattr(snapshot, "OutputPerSecond", 0.0) or 0.0
                    ),
                    boss_active_seconds=getattr(snapshot, "BossActiveSeconds", None),
                    death_count=enrichment.death_count,
                    first_death_seconds=enrichment.first_death_seconds,
                    first_death_ability=enrichment.first_death_ability,
                    minimum_primary_resource_percent=(
                        enrichment.minimum_primary_resource_percent
                    ),
                    key_uptimes=uptimes,
                )
            )

        return RaidReviewCollectionResult(
            observations=tuple(observations),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "PerformanceRaidReviewObservationService",
    "RaidReviewCollectionResult",
    "RaidReviewEnrichmentResolver",
    "RaidReviewFightResolver",
    "RaidReviewSnapshotResolver",
    "RaidReviewSource",
]
