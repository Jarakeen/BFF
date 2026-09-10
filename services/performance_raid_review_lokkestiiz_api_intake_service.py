from __future__ import annotations

"""Build Lokkestiiz Raid Review pull requests directly from ESO Logs API data.

This is an intake/orchestration service, not a combat-analysis engine. It resolves
report actors from ESO Logs master data, gets role-grouped friendly players through
the existing PerformanceDashboardService API wrapper, and emits the existing
LokkestiizRaidReviewPullRequest contract.

Actor IDs remain report-scoped. For pulls selected from one report, the stable
member key is therefore ``<normalized report code>:<actor id>``. Cross-report
identity linking is intentionally outside this service and must remain explicit.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
)
from services.performance_raid_review_observation_service import RaidReviewSource


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewApiIntakeResult:
    pulls: tuple[LokkestiizRaidReviewPullRequest, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLokkestiizApiIntakeService:
    """Resolve selected Lokke pulls directly from one ESO Logs report."""

    def __init__(self, performance_service) -> None:
        self.performance_service = performance_service
        self.client = performance_service.client

    def build(
        self,
        report_code: str,
        fight_ids: Iterable[int],
        *,
        evidence_source: str = "ESO Logs API reviewed runtime evidence",
    ) -> LokkestiizRaidReviewApiIntakeResult:
        code = self.client.normalize_report_code(report_code)
        if not code:
            return LokkestiizRaidReviewApiIntakeResult(
                pulls=(),
                unresolved=("Raid Review requires an ESO Logs report code or report URL.",),
            )

        requested_ids = tuple(dict.fromkeys(int(value) for value in fight_ids if int(value) > 0))
        if not requested_ids:
            return LokkestiizRaidReviewApiIntakeResult(
                pulls=(),
                unresolved=(f"No positive fight IDs were selected from report {code}.",),
            )

        try:
            boss_actor_id = self._resolve_report_lokkestiiz_actor_id(code)
        except Exception as exc:
            return LokkestiizRaidReviewApiIntakeResult(
                pulls=(),
                unresolved=(f"Could not resolve Lokkestiiz boss actor for report {code}: {exc}",),
            )

        pulls: list[LokkestiizRaidReviewPullRequest] = []
        unresolved: list[str] = []
        for fight_id in requested_ids:
            try:
                fight = self.client.get_fight(code, fight_id)
            except Exception as exc:
                unresolved.append(f"Could not load report {code} fight #{fight_id}: {exc}")
                continue

            fight_name = str(fight.get("name") or "").strip()
            if fight_name.casefold() != "lokkestiiz":
                unresolved.append(
                    f"Report {code} fight #{fight_id} is {fight_name or 'unnamed'}, not Lokkestiiz; pull was skipped."
                )
                continue

            try:
                _summary, actors = self.performance_service.list_actors(code, fight_id)
            except Exception as exc:
                unresolved.append(
                    f"Could not resolve player roster for report {code} fight #{fight_id}: {exc}"
                )
                continue

            sources = tuple(
                RaidReviewSource(
                    report_code=code,
                    fight_id=fight_id,
                    actor_id=int(actor.ActorId),
                    actor_label=str(actor.Label),
                    role=str(actor.Role),
                    member_key=f"{code.casefold()}:{int(actor.ActorId)}",
                )
                for actor in actors
                if int(actor.ActorId) > 0
            )
            if not sources:
                unresolved.append(
                    f"No friendly player actors were resolved for report {code} fight #{fight_id}."
                )
                continue

            pulls.append(
                LokkestiizRaidReviewPullRequest(
                    report_code=code,
                    fight_id=fight_id,
                    boss_actor_id=boss_actor_id,
                    sources=sources,
                    evidence_source=evidence_source,
                )
            )

        return LokkestiizRaidReviewApiIntakeResult(
            pulls=tuple(pulls),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _resolve_report_lokkestiiz_actor_id(self, report_code: str) -> int:
        query = """
        query RaidReviewMasterActors($code: String!) {
          reportData {
            report(code: $code) {
              masterData {
                actors {
                  id
                  name
                  type
                  subType
                }
              }
            }
          }
        }
        """
        data = self.client._query(query, {"code": report_code})
        report = (data.get("reportData") or {}).get("report") or {}
        master = report.get("masterData") or {}
        actors = master.get("actors") or []

        candidates: list[int] = []
        for actor in actors:
            if not isinstance(actor, dict):
                continue
            if str(actor.get("name") or "").strip().casefold() != "lokkestiiz":
                continue
            actor_type = str(actor.get("type") or "").strip().casefold()
            subtype = str(actor.get("subType") or "").strip().casefold()
            if actor_type and actor_type not in {"npc", "enemy", "boss"}:
                continue
            if subtype and subtype != "boss":
                continue
            actor_id = actor.get("id")
            if actor_id is not None and int(actor_id) > 0:
                candidates.append(int(actor_id))

        unique = tuple(dict.fromkeys(candidates))
        if not unique:
            raise ValueError("report master data did not contain a named Lokkestiiz boss actor")
        if len(unique) != 1:
            raise ValueError(
                f"report master data contained {len(unique)} distinct named Lokkestiiz boss actors"
            )
        return unique[0]


__all__ = [
    "LokkestiizRaidReviewApiIntakeResult",
    "PerformanceRaidReviewLokkestiizApiIntakeService",
]
