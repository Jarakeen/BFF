from __future__ import annotations

"""Fresh ESO Logs observation collection for cross-pull raid review.

This service deliberately reuses PerformanceDashboardService rather than persisting
computed snapshots. Sources are explicit and actor IDs remain scoped to their report.
A stable member_key is required from the caller when the same person is linked across
reports.

Death/resource/mechanic enrichment is intentionally separate. Missing enrichment is
left missing rather than inferred from output or uptime data.
"""

from dataclasses import dataclass
from typing import Iterable

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


@dataclass(frozen=True, slots=True)
class RaidReviewCollectionResult:
    observations: tuple[RaidReviewObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewObservationService:
    """Build fresh review observations from explicit ESO Logs actor/fight sources."""

    def __init__(self, performance_service):
        self.performance_service = performance_service

    def collect(
        self,
        sources: Iterable[RaidReviewSource],
    ) -> RaidReviewCollectionResult:
        observations: list[RaidReviewObservation] = []
        unresolved: list[str] = []

        for source in sources:
            try:
                fight = self.performance_service.client.get_fight(
                    source.report_code,
                    int(source.fight_id),
                )
                snapshot = self.performance_service.build_snapshot(
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

            observations.append(
                RaidReviewObservation(
                    report_code=str(source.report_code),
                    fight_id=int(source.fight_id),
                    fight_name=str(getattr(snapshot, "FightName", "") or fight.get("name") or ""),
                    kill=bool(fight.get("kill")),
                    actor_id=int(source.actor_id),
                    actor_label=str(source.actor_label),
                    role=str(getattr(snapshot, "Role", source.role) or source.role),
                    fight_duration_seconds=float(
                        getattr(snapshot, "FightDurationSeconds", 0.0) or 0.0
                    ),
                    member_key=str(source.member_key),
                    output_total=float(getattr(snapshot, "OutputTotal", 0.0) or 0.0),
                    output_per_second=float(
                        getattr(snapshot, "OutputPerSecond", 0.0) or 0.0
                    ),
                    boss_active_seconds=getattr(snapshot, "BossActiveSeconds", None),
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
    "RaidReviewSource",
]
