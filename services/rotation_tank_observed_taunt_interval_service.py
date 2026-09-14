from __future__ import annotations

"""Project explicit logged Taunt-state lifecycle events into observed ownership intervals.

This service is research/runtime evidence plumbing, not encounter policy. It accepts
already-observed apply/remove events for the reviewed Taunt state and returns exact
source/target scoped intervals. Missing removals stay unresolved/open; no synthetic
15-second duration is invented.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ObservedTauntStateEvent:
    report_code: str
    fight_id: int
    actor_name: str
    target_instance: int
    source_id: int | None
    timestamp_ms: float
    event_type: str

    def __post_init__(self) -> None:
        if not str(self.report_code or "").strip():
            raise ValueError("observed taunt-state event requires report_code")
        if not str(self.actor_name or "").strip():
            raise ValueError("observed taunt-state event requires actor_name")
        event_type = str(self.event_type or "").strip().casefold()
        if event_type not in {"applydebuff", "removedebuff"}:
            raise ValueError("observed taunt-state event must be applydebuff or removedebuff")
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "timestamp_ms", float(self.timestamp_ms))


@dataclass(frozen=True)
class ObservedTauntInterval:
    report_code: str
    fight_id: int
    actor_name: str
    target_instance: int
    source_id: int | None
    start_ms: float
    end_ms: float | None

    @property
    def duration_ms(self) -> float | None:
        if self.end_ms is None:
            return None
        return max(0.0, self.end_ms - self.start_ms)


class RotationTankObservedTauntIntervalService:
    def project(
        self,
        events: tuple[ObservedTauntStateEvent, ...],
    ) -> tuple[ObservedTauntInterval, ...]:
        ordered = sorted(
            tuple(events),
            key=lambda row: (
                row.report_code,
                row.fight_id,
                row.actor_name.casefold(),
                row.target_instance,
                -1 if row.source_id is None else row.source_id,
                row.timestamp_ms,
                0 if row.event_type == "removedebuff" else 1,
            ),
        )
        open_by_key: dict[tuple[str, int, str, int, int | None], float] = {}
        intervals: list[ObservedTauntInterval] = []
        for row in ordered:
            key = (
                row.report_code,
                row.fight_id,
                row.actor_name.casefold(),
                row.target_instance,
                row.source_id,
            )
            if row.event_type == "applydebuff":
                prior = open_by_key.get(key)
                if prior is not None:
                    intervals.append(
                        ObservedTauntInterval(
                            report_code=row.report_code,
                            fight_id=row.fight_id,
                            actor_name=row.actor_name,
                            target_instance=row.target_instance,
                            source_id=row.source_id,
                            start_ms=prior,
                            end_ms=row.timestamp_ms,
                        )
                    )
                open_by_key[key] = row.timestamp_ms
            else:
                prior = open_by_key.pop(key, None)
                if prior is not None:
                    intervals.append(
                        ObservedTauntInterval(
                            report_code=row.report_code,
                            fight_id=row.fight_id,
                            actor_name=row.actor_name,
                            target_instance=row.target_instance,
                            source_id=row.source_id,
                            start_ms=prior,
                            end_ms=row.timestamp_ms,
                        )
                    )
        for (report_code, fight_id, actor_key, target_instance, source_id), start_ms in open_by_key.items():
            actor_name = next(
                row.actor_name
                for row in ordered
                if row.report_code == report_code
                and row.fight_id == fight_id
                and row.actor_name.casefold() == actor_key
                and row.target_instance == target_instance
                and row.source_id == source_id
            )
            intervals.append(
                ObservedTauntInterval(
                    report_code=report_code,
                    fight_id=fight_id,
                    actor_name=actor_name,
                    target_instance=target_instance,
                    source_id=source_id,
                    start_ms=start_ms,
                    end_ms=None,
                )
            )
        return tuple(intervals)


__all__ = [
    "ObservedTauntStateEvent",
    "ObservedTauntInterval",
    "RotationTankObservedTauntIntervalService",
]
