from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class SemiStaticRotationEntry:
    """One explicitly timed or repeating action in a semi-static rotation.

    ``recast_interval_seconds`` is caller-supplied schedule intent, not inferred
    canonical ESO duration. Later Phase 13 timing evidence may justify or replace
    that assumption without changing the authoritative RotationPlan contract.
    """

    first_time_seconds: float
    sequence: int
    kind: RotationActionKind
    name: str | None = None
    bar: str | None = None
    recast_interval_seconds: float | None = None

    def __post_init__(self) -> None:
        first = float(self.first_time_seconds)
        if not math.isfinite(first) or first < 0:
            raise ValueError("semi-static first action time must be finite and non-negative")
        object.__setattr__(self, "first_time_seconds", first)

        if self.sequence < 0:
            raise ValueError("semi-static sequence cannot be negative")

        if self.recast_interval_seconds is not None:
            interval = float(self.recast_interval_seconds)
            if not math.isfinite(interval) or interval <= 0:
                raise ValueError("semi-static recast interval must be finite and positive")
            object.__setattr__(self, "recast_interval_seconds", interval)

        # Reuse the authoritative action validator for kind/name/bar semantics.
        validated = RotationAction(
            time_seconds=first,
            sequence=self.sequence,
            kind=self.kind,
            name=self.name,
            bar=self.bar,
        )
        object.__setattr__(self, "kind", validated.kind)
        object.__setattr__(self, "name", validated.name)
        object.__setattr__(self, "bar", validated.bar)


def create_semi_static_rotation_plan(
    *,
    character_name: str,
    build_name: str,
    duration_seconds: float,
    entries: tuple[SemiStaticRotationEntry, ...],
    assumptions: tuple[str, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> RotationPlan:
    """Expand explicit bounded recast entries into a deterministic RotationPlan.

    Repeating timestamps are computed as ``first + interval * occurrence`` rather
    than by accumulated addition. This mirrors the deterministic scheduling rule
    already used by Phase 7 periodic runtime events.
    """

    duration = float(duration_seconds)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("semi-static rotation duration must be finite and non-negative")

    actions: list[RotationAction] = []
    has_manual_recast = False

    for entry in entries:
        if entry.first_time_seconds > duration:
            continue

        if entry.recast_interval_seconds is None:
            occurrence_count = 1
        else:
            has_manual_recast = True
            span = duration - entry.first_time_seconds
            occurrence_count = math.floor((span / entry.recast_interval_seconds) + 1e-12) + 1

        for occurrence in range(occurrence_count):
            if entry.recast_interval_seconds is None:
                time_seconds = entry.first_time_seconds
            else:
                time_seconds = (
                    entry.first_time_seconds
                    + entry.recast_interval_seconds * occurrence
                )
            if time_seconds > duration + 1e-12:
                break
            actions.append(
                RotationAction(
                    time_seconds=time_seconds,
                    sequence=entry.sequence,
                    kind=entry.kind,
                    name=entry.name,
                    bar=entry.bar,
                )
            )

    schedule_assumptions = list(assumptions)
    if has_manual_recast:
        schedule_assumptions.append(
            "semi-static recast intervals are explicit caller-supplied assumptions; "
            "they are not inferred from canonical skill duration evidence"
        )

    return RotationPlan(
        character_name=character_name,
        build_name=build_name,
        duration_seconds=duration,
        actions=tuple(actions),
        assumptions=tuple(schedule_assumptions),
        unresolved=unresolved,
    )
