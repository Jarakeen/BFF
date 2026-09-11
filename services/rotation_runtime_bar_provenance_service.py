from __future__ import annotations

"""Bind unified runtime evidence to the RotationPlan's proven active-bar timeline.

The rotation plan already owns BAR_SWAP ordering through ``RotationActiveBarAssessor``.
This service projects that existing authority onto Extreme runtime history by wrapping
ordinary ``RuntimeEffectEventAttempt`` entries with ``ExtremeRuntimeBarEffectAttempt``
and by carrying explicit ``ExtremeRuntimeBarTransition`` entries for real swaps. It
does not create a second bar timeline, mutate generic RuntimeEvent, or change proc
semantics.

Pre-tagged attempts and pre-existing transition evidence are verified against the plan
and fail closed on disagreement. Non-bar runtime entries are preserved unchanged.
"""

from dataclasses import dataclass

from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


@dataclass(frozen=True)
class RotationRuntimeBarProvenanceResult:
    snapshot: ExtremeRuntimeSnapshot | None
    attempts_tagged: int = 0
    attempts_verified: int = 0
    transitions_projected: int = 0
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.snapshot is not None and not self.unresolved


class RotationRuntimeBarProvenanceService:
    """Project plan-owned BAR_SWAP state onto unified runtime evidence."""

    def __init__(self, *, active_bar_assessor: RotationActiveBarAssessor | None = None) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()

    @staticmethod
    def _normalize_bar(value: str) -> str:
        bar = str(value or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("rotation initial bar must be front or back")
        return bar

    def _expected_transitions(
        self,
        plan: RotationPlan,
        *,
        initial_bar: str,
    ) -> tuple[ExtremeRuntimeBarTransition, ...]:
        active_bar = self._normalize_bar(initial_bar)
        transitions: list[ExtremeRuntimeBarTransition] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            destination = str(action.bar)
            if destination == active_bar:
                continue
            transitions.append(
                ExtremeRuntimeBarTransition(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    from_bar=active_bar,
                    to_bar=destination,
                )
            )
            active_bar = destination
        return tuple(transitions)

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

        expected_transitions = self._expected_transitions(plan, initial_bar=initial_bar)
        supplied_transitions = snapshot.bar_transitions
        if supplied_transitions and supplied_transitions != expected_transitions:
            return RotationRuntimeBarProvenanceResult(
                snapshot=None,
                unresolved=(
                    "runtime bar-transition evidence disagrees with RotationPlan BAR_SWAP history",
                ),
            )

        history: list[object] = []
        unresolved: list[str] = []
        tagged = 0
        verified = 0
        epsilon = 1e-12

        for entry in snapshot.ordered_runtime_history:
            if isinstance(entry, ExtremeRuntimeBarTransition):
                # Canonical transitions are appended once below after verification.
                continue

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
                transitions_projected=len(expected_transitions),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        history.extend(expected_transitions)
        return RotationRuntimeBarProvenanceResult(
            snapshot=ExtremeRuntimeSnapshot(
                runtime_history=tuple(history),
                snapshot_time_seconds=snapshot.snapshot_time_seconds,
                recipient_actor_id=snapshot.recipient_actor_id,
                group_member_ids=snapshot.group_member_ids,
            ),
            attempts_tagged=tagged,
            attempts_verified=verified,
            transitions_projected=len(expected_transitions),
            unresolved=(),
        )


__all__ = [
    "RotationRuntimeBarProvenanceResult",
    "RotationRuntimeBarProvenanceService",
]
