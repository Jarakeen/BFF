from __future__ import annotations

"""Build one explicit Lokkestiiz Raid Review pull request from saved Performance picks.

This service composes the generic Performance-profile source adapter with the existing
Lokkestiiz session request contract. It owns no encounter mechanics and performs no
network access. A single invocation must resolve to exactly one report/fight pair;
callers compose several validated pull requests for a cross-pull session.
"""

from dataclasses import dataclass
from typing import Iterable, Mapping

from models.performance_model import PerformanceProfile
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
)
from services.performance_raid_review_profile_source_service import (
    ActorKey,
    PerformanceRaidReviewProfileSourceService,
)


@dataclass(frozen=True, slots=True)
class LokkestiizProfilePullRequestResult:
    request: LokkestiizRaidReviewPullRequest | None
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLokkestiizProfileRequestService:
    """Adapt one saved Performance roster into one Lokke session pull request."""

    def __init__(
        self,
        source_service: PerformanceRaidReviewProfileSourceService | None = None,
    ) -> None:
        self.source_service = source_service or PerformanceRaidReviewProfileSourceService()

    def build(
        self,
        profiles: Iterable[PerformanceProfile],
        *,
        boss_actor_id: int,
        member_keys: Mapping[ActorKey, str] | None = None,
        primary_resources: Mapping[ActorKey, str] | None = None,
        evidence_source: str = "ESO Logs reviewed runtime evidence",
    ) -> LokkestiizProfilePullRequestResult:
        source_result = self.source_service.build(
            tuple(profiles),
            member_keys=member_keys,
            primary_resources=primary_resources,
        )
        unresolved = list(source_result.unresolved)
        sources = tuple(source_result.sources)

        if int(boss_actor_id) <= 0:
            unresolved.append("Lokkestiiz pull request requires a positive boss_actor_id.")
            return LokkestiizProfilePullRequestResult(None, tuple(dict.fromkeys(unresolved)))

        if not sources:
            unresolved.append("No valid Performance profiles were available for the Lokkestiiz pull request.")
            return LokkestiizProfilePullRequestResult(None, tuple(dict.fromkeys(unresolved)))

        pull_keys = {
            (str(source.report_code), int(source.fight_id))
            for source in sources
        }
        if len(pull_keys) != 1:
            labels = ", ".join(
                f"{report} #{fight_id}"
                for report, fight_id in sorted(pull_keys, key=lambda item: (item[0].casefold(), item[1]))
            )
            unresolved.append(
                "Performance profiles span multiple pulls; build one Lokkestiiz pull request at a time: "
                + labels
                + "."
            )
            return LokkestiizProfilePullRequestResult(None, tuple(dict.fromkeys(unresolved)))

        report_code, fight_id = next(iter(pull_keys))
        request = LokkestiizRaidReviewPullRequest(
            report_code=report_code,
            fight_id=fight_id,
            boss_actor_id=int(boss_actor_id),
            sources=sources,
            evidence_source=str(evidence_source or "ESO Logs reviewed runtime evidence"),
        )
        return LokkestiizProfilePullRequestResult(
            request=request,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "LokkestiizProfilePullRequestResult",
    "PerformanceRaidReviewLokkestiizProfileRequestService",
]
