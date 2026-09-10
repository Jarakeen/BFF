from __future__ import annotations

"""Adapt saved Performance Dashboard picks into explicit Raid Review sources.

This is a request-construction seam only. It does not fetch ESO Logs, run combat
analysis, or infer cross-report player identity from display names. ESO Logs actor IDs
remain report-scoped. Callers may provide explicit stable member keys and primary
resource names keyed by ``(report_code, actor_id)`` when that evidence is known.
"""

from dataclasses import dataclass
from typing import Iterable, Mapping

from models.performance_model import PerformanceProfile
from services.performance_raid_review_observation_service import RaidReviewSource


ActorKey = tuple[str, int]


@dataclass(frozen=True, slots=True)
class RaidReviewProfileSourceResult:
    sources: tuple[RaidReviewSource, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewProfileSourceService:
    """Build validated RaidReviewSource rows from persisted performance picks."""

    def build(
        self,
        profiles: Iterable[PerformanceProfile],
        *,
        member_keys: Mapping[ActorKey, str] | None = None,
        primary_resources: Mapping[ActorKey, str] | None = None,
    ) -> RaidReviewProfileSourceResult:
        stable_keys = dict(member_keys or {})
        resource_names = dict(primary_resources or {})
        sources: list[RaidReviewSource] = []
        unresolved: list[str] = []
        seen: set[tuple[str, int, int]] = set()

        for index, profile in enumerate(tuple(profiles), start=1):
            report_code = str(profile.ReportCode or "").strip()
            actor_label = str(profile.ActorLabel or profile.Name or "").strip()

            try:
                fight_id = int(str(profile.FightId or "").strip())
            except (TypeError, ValueError):
                fight_id = 0

            try:
                actor_id = int(profile.ActorId) if profile.ActorId is not None else 0
            except (TypeError, ValueError):
                actor_id = 0

            problems: list[str] = []
            if not report_code:
                problems.append("report code")
            if fight_id <= 0:
                problems.append("positive fight id")
            if actor_id <= 0:
                problems.append("positive actor id")
            if not actor_label:
                problems.append("actor label")

            if problems:
                unresolved.append(
                    f"Performance profile {index} cannot become a Raid Review source; missing/invalid "
                    + ", ".join(problems)
                    + "."
                )
                continue

            dedupe_key = (report_code.casefold(), fight_id, actor_id)
            if dedupe_key in seen:
                unresolved.append(
                    f"Duplicate Raid Review source skipped for {report_code} #{fight_id} actor {actor_id}."
                )
                continue
            seen.add(dedupe_key)

            actor_key = (report_code, actor_id)
            member_key = str(stable_keys.get(actor_key, "") or "").strip()
            primary_resource_name = str(resource_names.get(actor_key, "") or "").strip()

            sources.append(
                RaidReviewSource(
                    report_code=report_code,
                    fight_id=fight_id,
                    actor_id=actor_id,
                    actor_label=actor_label,
                    role=str(profile.Role or "DPS"),
                    member_key=member_key,
                    immunity_buff_name=str(profile.ImmunityBuffName or ""),
                    immunity_buff_kind=str(profile.ImmunityBuffKind or "Buff"),
                    primary_resource_name=primary_resource_name,
                )
            )

        return RaidReviewProfileSourceResult(
            sources=tuple(sources),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "PerformanceRaidReviewProfileSourceService",
    "RaidReviewProfileSourceResult",
]
