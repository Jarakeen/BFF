from __future__ import annotations

"""Bind unified runtime effect attempts to the RotationPlan's proven active bar.

The rotation plan already owns BAR_SWAP ordering through ``RotationActiveBarAssessor``.
This service projects that existing authority onto Extreme runtime history by wrapping
ordinary ``RuntimeEffectEventAttempt`` entries with ``ExtremeRuntimeBarEffectAttempt``.
It does not create a second bar timeline, mutate generic RuntimeEvent, or change proc
semantics.

Pre-tagged attempts are verified against the plan and fail closed on disagreement.
Non-effect runtime entries are preserved unchanged.
"""

from dataclasses import dataclass

from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationPlan
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class RotationRuntimeBarProvenanceResult:
    snapshot: ExtremeRuntimeSnapshot | None
    attempts_tagged: int = 0
    attempts_verified: int = 0
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.snapshot is not None and not self.unresolved


class RotationRuntimeBarProvenanceService:
    """Project plan-owned BAR_SWAP state onto unified runtime effect attempts."""

    def __init__(self, *, active_bar_assessor: RotationActiveBarAssessor | None = None) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()

    def bind(
        self,
        plan: RotationPlan,
        snapshot: ExtremeRuntimeSnapshot,
        *,
        initial_bar: str = "front",
    ) -> RotationRuntimeBarProvenanceResult:
        if not snapshot.runtime_history:
            return RotationRuntimeBarProvenanceResult(
                snapshot=None,
                unresolved=(
                    "rotation bar provenance requires authoritative runtime_history; "
                    "legacy one-snapshot attempts cannot be reconstructed safely",
                ),
            )

        assessment = self.active_bar_assessor.assess(plan, initial_bar=initial_bar)
        if not assessment.legal:
            return RotationRuntimeBarProvenanceResult(
                snapshot=None,
                unresolved=tuple(
                    f"rotation bar legality violation at {row.time_seconds:.3f}s: {row.reason}"
                    for row in assessment.violations
                ),
            )

        history: list[object] = []
        unresolved: list[str] = []
        tagged = 0
        verified = 0
        epsilon = 1e-12

        for entry in snapshot.ordered_runtime_history:
            if isinstance(entry, ExtremeRuntimeBarEffectAttempt):
                event = entry.attempt.event
                if float(event.time_seconds) > float(plan.duration_seconds) + epsilon:
                    unresolved.append(
                        f"runtime effect attempt at {event.time_seconds:.3f}s exceeds rotation duration"
                    )
                    history.append(entry)
                    continue
                expected = self.active_bar_assessor.active_bar_at(
                    plan,
                    time_seconds=event.time_seconds,
                    sequence=event.sequence,
                    initial_bar=initial_bar,
                )
                if entry.active_bar != expected:
                    unresolved.append(
                        "runtime effect bar provenance disagrees with RotationPlan at "
                        f"{event.time_seconds:.3f}s sequence {event.sequence}: "
                        f"tagged={entry.active_bar}, expected={expected}"
                    )
                else:
                    verified += 1
                history.append(entry)
                continue

            if isinstance(entry, RuntimeEffectEventAttempt):
                event = entry.event
                if float(event.time_seconds) > float(plan.duration_seconds) + epsilon:
                    unresolved.append(
                        f"runtime effect attempt at {event.time_seconds:.3f}s exceeds rotation duration"
                    )
                    history.append(entry)
                    continue
                active_bar = self.active_bar_assessor.active_bar_at(
                    plan,
                    time_seconds=event.time_seconds,
                    sequence=event.sequence,
                    initial_bar=initial_bar,
                )
                history.append(
                    ExtremeRuntimeBarEffectAttempt(
                        attempt=entry,
                        active_bar=active_bar,
                    )
                )
                tagged += 1
                continue

            history.append(entry)

        if unresolved:
            return RotationRuntimeBarProvenanceResult(
                snapshot=None,
                attempts_tagged=tagged,
                attempts_verified=verified,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        return RotationRuntimeBarProvenanceResult(
            snapshot=ExtremeRuntimeSnapshot(
                runtime_history=tuple(history),
                snapshot_time_seconds=snapshot.snapshot_time_seconds,
                recipient_actor_id=snapshot.recipient_actor_id,
                group_member_ids=snapshot.group_member_ids,
            ),
            attempts_tagged=tagged,
            attempts_verified=verified,
            unresolved=(),
        )


__all__ = [
    "RotationRuntimeBarProvenanceResult",
    "RotationRuntimeBarProvenanceService",
]
