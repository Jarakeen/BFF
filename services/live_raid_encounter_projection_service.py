from __future__ import annotations

"""Read-only Live Raid encounter projection.

This layer composes canonical encounter guide/evidence into UI-ready operational
context. It never invents boss health, phase, timing, or telemetry.
"""

from dataclasses import dataclass
import math
import re
from pathlib import Path

from models.raid_plan import RaidPlan
from services.encounter_boss_guide import (
    BossGuideEncounterSummary,
    BossGuideTimelineFact,
    EncounterBossGuide,
    EncounterBossGuideNotFound,
    EncounterBossGuideService,
)
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjection,
    EncounterGuideEvidenceProjectionService,
)


_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _clean(value: object) -> str:
    return str(value or "").strip()


def _token(value: object) -> str:
    return _TOKEN_RE.sub("", _clean(value).casefold())


def _seconds(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0:
        return None
    return parsed


def _label_for_fact(fact: BossGuideTimelineFact) -> str:
    payload = fact.payload
    return _clean(
        payload.get("label")
        or payload.get("name")
        or fact.fact_key.replace("_", " ").title()
        or "Encounter event"
    )


def _detail_for_fact(fact: BossGuideTimelineFact) -> str:
    payload = fact.payload
    return _clean(payload.get("description") or payload.get("detail"))


@dataclass(frozen=True)
class LiveRaidClockEvent:
    start_seconds: float
    end_seconds: float
    label: str
    detail: str
    fact_key: str


@dataclass(frozen=True)
class LiveRaidEncounterContext:
    encounter_id: str
    encounter_name: str
    content_name: str
    summary: str
    location: str
    phase_lines: tuple[str, ...]
    callouts: tuple[str, ...]
    checklist: tuple[str, ...]
    clock_events: tuple[LiveRaidClockEvent, ...]


class LiveRaidEncounterProjectionService:
    def __init__(self, database: Path, data_root: Path) -> None:
        self.guide_service = EncounterBossGuideService(database)
        self.evidence_service = EncounterGuideEvidenceProjectionService(data_root)

    def encounters_for_trial(self, trial_id: str) -> tuple[BossGuideEncounterSummary, ...]:
        wanted = _token(trial_id)
        if not wanted:
            return ()
        rows = []
        for row in self.guide_service.encounter_summaries():
            candidates = {_token(row.content_id), _token(row.content_name)}
            if wanted in candidates or any(
                wanted and candidate and (wanted in candidate or candidate in wanted)
                for candidate in candidates
            ):
                rows.append(row)
        return tuple(rows)

    def context_for(self, plan: RaidPlan, encounter_id: str) -> LiveRaidEncounterContext | None:
        encounter_id = _clean(encounter_id)
        if not encounter_id:
            return None
        try:
            guide = self.guide_service.get(encounter_id)
        except EncounterBossGuideNotFound:
            return None

        evidence = self.evidence_service.get(encounter_id, guide.name)
        clock_events = self._clock_events(
            self.guide_service.reviewed_clock_facts(encounter_id)
        )

        phase_lines = tuple(
            " • ".join(
                piece
                for piece in (
                    _clean(phase.threshold),
                    _clean(phase.label),
                )
                if piece
            )
            for phase in guide.phases
            if _clean(phase.label) or _clean(phase.threshold)
        )

        callouts = list(evidence.callouts)
        for responsibility in plan.triggered_responsibilities:
            if responsibility.encounter_id.casefold() != encounter_id.casefold():
                continue
            directive = _clean(responsibility.directive)
            if directive:
                callouts.append(
                    f"{responsibility.seat_id}: {directive}"
                )

        checklist = list(evidence.callouts)
        if not checklist:
            checklist.extend(
                f"{row.mechanic}: {row.mitigation}"
                for row in evidence.strategy
                if _clean(row.mitigation)
                and _clean(row.mitigation) != "Reviewed handling not yet recorded."
            )
        if plan.plan_note:
            checklist.append(f"Plan note: {plan.plan_note}")

        return LiveRaidEncounterContext(
            encounter_id=guide.encounter_id,
            encounter_name=guide.name,
            content_name=guide.content_name,
            summary=guide.summary,
            location=guide.location,
            phase_lines=tuple(dict.fromkeys(line for line in phase_lines if line))[:8],
            callouts=tuple(dict.fromkeys(_clean(line) for line in callouts if _clean(line)))[:10],
            checklist=tuple(dict.fromkeys(_clean(line) for line in checklist if _clean(line)))[:8],
            clock_events=clock_events,
        )

    @staticmethod
    def _clock_events(
        facts: tuple[BossGuideTimelineFact, ...],
    ) -> tuple[LiveRaidClockEvent, ...]:
        events: list[LiveRaidClockEvent] = []
        for fact in facts:
            payload = fact.payload
            start = _seconds(payload.get("start_seconds"))
            end = _seconds(payload.get("end_seconds"))
            if start is not None and end is not None and end > start:
                events.append(
                    LiveRaidClockEvent(
                        start_seconds=start,
                        end_seconds=end,
                        label=_label_for_fact(fact),
                        detail=_detail_for_fact(fact),
                        fact_key=fact.fact_key,
                    )
                )
                continue

            point = _seconds(payload.get("time_seconds"))
            if point is None:
                point = _seconds(payload.get("at_seconds"))
            if point is None:
                continue
            events.append(
                LiveRaidClockEvent(
                    start_seconds=point,
                    end_seconds=point,
                    label=_label_for_fact(fact),
                    detail=_detail_for_fact(fact),
                    fact_key=fact.fact_key,
                )
            )
        return tuple(sorted(events, key=lambda row: (row.start_seconds, row.label.casefold())))


__all__ = [
    "LiveRaidClockEvent",
    "LiveRaidEncounterContext",
    "LiveRaidEncounterProjectionService",
]
