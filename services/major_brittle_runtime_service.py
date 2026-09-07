from __future__ import annotations

"""Target-scoped Major Brittle uptime from explicit Chilled applications.

Frost damage and a successful Chilled application are deliberately separate
runtime facts.  Callers must resolve each source's proc or guaranteed-apply
rules before submitting a ``ChillApplicationEvent`` here.  This keeps Frost
enchantments, Frost Elemental Blockade, and Winter's Revenge from being treated
as guaranteed Chilled applications while allowing deterministic sources such
as Elemental Susceptibility to use the same downstream timeline.
"""

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class ChillApplicationEvent:
    """One observed or otherwise resolved Chilled application."""

    time_seconds: float
    source: str
    target: str
    sequence: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError("Chilled application time must be finite and non-negative")
        if not str(self.source or "").strip():
            raise ValueError("Chilled application requires a source")
        if not str(self.target or "").strip():
            raise ValueError("Chilled application requires a target")
        if self.sequence < 0:
            raise ValueError("Chilled application sequence cannot be negative")


@dataclass(frozen=True)
class MajorBrittleWindow:
    """One merged period where Major Brittle is active on the target."""

    start_time_seconds: float
    end_time_seconds: float
    target: str
    sources: tuple[str, ...]

    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds


@dataclass(frozen=True)
class MajorBrittleUptimeProjection:
    """Auditable effect windows and uptime over one encounter horizon."""

    target: str
    encounter_duration_seconds: float
    windows: tuple[MajorBrittleWindow, ...]
    application_count_by_source: tuple[tuple[str, int], ...]
    active_seconds: float | None
    uptime_fraction: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


def project_major_brittle_from_chilled(
    applications: Iterable[ChillApplicationEvent],
    *,
    target: str,
    encounter_duration_seconds: float,
    tundras_maw_active: bool | None,
    major_brittle_duration_seconds: float,
    evidence_complete: bool,
) -> MajorBrittleUptimeProjection:
    """Project Tundra's Maw Major Brittle without inventing Chill procs.

    Each submitted Chilled application creates one Major Brittle window when
    Tundra's Maw is active.  Applications from every source refresh the same
    named effect on the same target, so overlapping windows are merged rather
    than summed.  Incomplete application evidence preserves the partial windows
    for audit but leaves total uptime unknown.
    """

    if not str(target or "").strip():
        raise ValueError("Major Brittle projection requires a target")
    if (
        not math.isfinite(encounter_duration_seconds)
        or encounter_duration_seconds <= 0
    ):
        raise ValueError("encounter duration must be finite and positive")
    if (
        not math.isfinite(major_brittle_duration_seconds)
        or major_brittle_duration_seconds <= 0
    ):
        raise ValueError("Major Brittle duration must be finite and positive")

    selected = tuple(
        sorted(
            (event for event in applications if event.target == target),
            key=lambda event: (event.time_seconds, event.sequence, event.source),
        )
    )

    counts: dict[str, int] = {}
    for event in selected:
        if event.time_seconds < encounter_duration_seconds:
            counts[event.source] = counts.get(event.source, 0) + 1

    if tundras_maw_active is not True:
        unresolved = () if tundras_maw_active is False else ("tundras_maw_state_required",)
        known_zero = tundras_maw_active is False
        return MajorBrittleUptimeProjection(
            target=target,
            encounter_duration_seconds=float(encounter_duration_seconds),
            windows=(),
            application_count_by_source=tuple(sorted(counts.items())),
            active_seconds=0.0 if known_zero else None,
            uptime_fraction=0.0 if known_zero else None,
            unresolved=unresolved,
        )

    merged: list[MajorBrittleWindow] = []
    for event in selected:
        if event.time_seconds >= encounter_duration_seconds:
            continue
        end = min(
            event.time_seconds + major_brittle_duration_seconds,
            encounter_duration_seconds,
        )
        if merged and event.time_seconds <= merged[-1].end_time_seconds:
            previous = merged[-1]
            merged[-1] = MajorBrittleWindow(
                start_time_seconds=previous.start_time_seconds,
                end_time_seconds=max(previous.end_time_seconds, end),
                target=target,
                sources=tuple(sorted({*previous.sources, event.source})),
            )
        else:
            merged.append(
                MajorBrittleWindow(
                    start_time_seconds=event.time_seconds,
                    end_time_seconds=end,
                    target=target,
                    sources=(event.source,),
                )
            )

    unresolved = () if evidence_complete else ("chilled_application_evidence_incomplete",)
    active_seconds = sum(window.duration_seconds for window in merged)
    return MajorBrittleUptimeProjection(
        target=target,
        encounter_duration_seconds=float(encounter_duration_seconds),
        windows=tuple(merged),
        application_count_by_source=tuple(sorted(counts.items())),
        active_seconds=active_seconds if evidence_complete else None,
        uptime_fraction=(active_seconds / encounter_duration_seconds) if evidence_complete else None,
        unresolved=unresolved,
    )
