from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition


@dataclass(frozen=True)
class ExtremeRuntimePotionUse:
    """One explicit potion activation on the shared Extreme runtime timeline."""

    time_seconds: float
    sequence: int = 0

    def __post_init__(self) -> None:
        timestamp = float(self.time_seconds)
        if not math.isfinite(timestamp) or timestamp < 0.0:
            raise ValueError("runtime potion-use time must be a finite non-negative number")
        if int(self.sequence) < 0:
            raise ValueError("runtime potion-use sequence cannot be negative")
        object.__setattr__(self, "time_seconds", timestamp)
        object.__setattr__(self, "sequence", int(self.sequence))


ExtremeRuntimeHistoryEntry = (
    RuntimeEffectEventAttempt
    | ExtremeRuntimeBarEffectAttempt
    | ExtremeRuntimeBarTransition
    | ExtremeRuntimePotionUse
    | ExternalGroupBuffApplication
)


@dataclass(frozen=True)
class ExtremeRuntimeSnapshot:
    """One deterministic runtime history evaluated at one exact snapshot.

    ``runtime_history`` is the authoritative E1 input when supplied. It carries
    ordinary effect attempts, optional bar-provenance effect attempts, explicit
    bar transitions, potion activations, and explicitly evidenced external group-
    buff applications on one ordered timeline. The older positional fields remain
    in their original order as a compatibility bridge for existing callers, but
    they cannot be supplied alongside ``runtime_history`` so two competing versions
    of runtime truth cannot enter one evaluation.

    Bar provenance is deliberately carried by ``ExtremeRuntimeBarEffectAttempt``
    and ``ExtremeRuntimeBarTransition`` rather than added to the generic Phase 7
    ``RuntimeEvent`` contract. ``bar_transition_history_complete`` is separate from
    the transition tuple because an empty tuple may mean either "no swaps occurred"
    or "swap history was never proven". Strict source-bound gear persistence may
    rely on transition absence only when this flag is true.
    """

    # Keep the original positional order intact while E1 callers migrate.
    attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
    snapshot_time_seconds: float = 0.0
    potion_elapsed_seconds: float | None = None
    runtime_history: tuple[ExtremeRuntimeHistoryEntry, ...] = ()
    recipient_actor_id: str | None = None
    group_member_ids: tuple[str, ...] = ()
    bar_transition_history_complete: bool = False

    def __post_init__(self) -> None:
        snapshot = float(self.snapshot_time_seconds)
        if not math.isfinite(snapshot) or snapshot < 0.0:
            raise ValueError("runtime snapshot time must be a finite non-negative number")
        object.__setattr__(self, "snapshot_time_seconds", snapshot)

        history = tuple(self.runtime_history)
        attempts = tuple(self.attempts)
        supplied_potion_elapsed = self.potion_elapsed_seconds
        recipient = str(self.recipient_actor_id or "").strip() or None
        members = tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in self.group_member_ids
                if str(value or "").strip()
            )
        )
        object.__setattr__(self, "runtime_history", history)
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "recipient_actor_id", recipient)
        object.__setattr__(self, "group_member_ids", members)
        object.__setattr__(
            self,
            "bar_transition_history_complete",
            bool(self.bar_transition_history_complete),
        )

        if history and (attempts or supplied_potion_elapsed is not None):
            raise ValueError(
                "runtime_history cannot be combined with legacy attempts or potion_elapsed_seconds"
            )

        for entry in history:
            if not isinstance(
                entry,
                (
                    RuntimeEffectEventAttempt,
                    ExtremeRuntimeBarEffectAttempt,
                    ExtremeRuntimeBarTransition,
                    ExtremeRuntimePotionUse,
                    ExternalGroupBuffApplication,
                ),
            ):
                raise TypeError(
                    "runtime_history entries must be RuntimeEffectEventAttempt, "
                    "ExtremeRuntimeBarEffectAttempt, ExtremeRuntimeBarTransition, "
                    "ExtremeRuntimePotionUse, or ExternalGroupBuffApplication"
                )

        if history:
            ordered = tuple(sorted(history, key=self._entry_order))
            projected_attempts = tuple(
                entry.attempt
                if isinstance(entry, ExtremeRuntimeBarEffectAttempt)
                else entry
                for entry in ordered
                if isinstance(entry, (RuntimeEffectEventAttempt, ExtremeRuntimeBarEffectAttempt))
            )
            potion_uses = tuple(
                entry
                for entry in ordered
                if isinstance(entry, ExtremeRuntimePotionUse)
                and entry.time_seconds <= snapshot + 1e-12
            )
            projected_potion_elapsed = (
                None
                if not potion_uses
                else snapshot - potion_uses[-1].time_seconds
            )
            object.__setattr__(self, "attempts", projected_attempts)
            object.__setattr__(
                self,
                "potion_elapsed_seconds",
                projected_potion_elapsed,
            )
            return

        if supplied_potion_elapsed is None:
            return
        potion_elapsed = float(supplied_potion_elapsed)
        if not math.isfinite(potion_elapsed) or potion_elapsed < 0.0:
            raise ValueError(
                "runtime snapshot potion elapsed time must be finite and non-negative"
            )
        object.__setattr__(self, "potion_elapsed_seconds", potion_elapsed)

    @staticmethod
    def _entry_order(entry: ExtremeRuntimeHistoryEntry) -> tuple[float, int]:
        if isinstance(entry, RuntimeEffectEventAttempt):
            return (float(entry.event.time_seconds), int(entry.event.sequence))
        if isinstance(entry, ExtremeRuntimeBarEffectAttempt):
            return (entry.time_seconds, entry.sequence)
        if isinstance(entry, ExtremeRuntimeBarTransition):
            return (entry.time_seconds, entry.sequence)
        if isinstance(entry, ExtremeRuntimePotionUse):
            return (float(entry.time_seconds), int(entry.sequence))
        return (float(entry.applied_at_seconds), int(entry.sequence))

    @property
    def ordered_runtime_history(self) -> tuple[ExtremeRuntimeHistoryEntry, ...]:
        return tuple(sorted(self.runtime_history, key=self._entry_order))

    def snapshot_at(
        self,
        time_seconds: float,
        *,
        sequence: int | None = None,
    ) -> ExtremeRuntimeSnapshot:
        instant = float(time_seconds)
        if not math.isfinite(instant) or instant < 0.0:
            raise ValueError("runtime snapshot lookup time must be finite and non-negative")
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError("runtime snapshot lookup sequence cannot be negative")

        if not self.runtime_history:
            if (
                abs(instant - self.snapshot_time_seconds) <= 1e-12
                and boundary_sequence is None
            ):
                return self
            raise ValueError(
                "legacy runtime snapshot evidence cannot be projected to another ordered instant"
            )

        epsilon = 1e-12
        history: list[ExtremeRuntimeHistoryEntry] = []
        for entry in self.ordered_runtime_history:
            entry_time, entry_sequence = self._entry_order(entry)
            if entry_time > instant + epsilon:
                break
            if (
                boundary_sequence is not None
                and abs(entry_time - instant) <= epsilon
                and entry_sequence > boundary_sequence
            ):
                break
            history.append(entry)

        return ExtremeRuntimeSnapshot(
            runtime_history=tuple(history),
            snapshot_time_seconds=instant,
            recipient_actor_id=self.recipient_actor_id,
            group_member_ids=self.group_member_ids,
            bar_transition_history_complete=self.bar_transition_history_complete,
        )

    @property
    def effect_attempts(self) -> tuple[RuntimeEffectEventAttempt, ...]:
        if not self.runtime_history:
            return self.attempts
        return tuple(
            entry.attempt
            if isinstance(entry, ExtremeRuntimeBarEffectAttempt)
            else entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, (RuntimeEffectEventAttempt, ExtremeRuntimeBarEffectAttempt))
        )

    @property
    def bar_effect_attempts(self) -> tuple[ExtremeRuntimeBarEffectAttempt, ...]:
        if not self.runtime_history:
            return ()
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExtremeRuntimeBarEffectAttempt)
        )

    @property
    def bar_transitions(self) -> tuple[ExtremeRuntimeBarTransition, ...]:
        if not self.runtime_history:
            return ()
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExtremeRuntimeBarTransition)
        )

    @property
    def unbarred_effect_attempts(self) -> tuple[RuntimeEffectEventAttempt, ...]:
        if not self.runtime_history:
            return self.attempts
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, RuntimeEffectEventAttempt)
        )

    @property
    def external_group_buff_applications(self) -> tuple[ExternalGroupBuffApplication, ...]:
        if not self.runtime_history:
            return ()
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExternalGroupBuffApplication)
        )

    @property
    def effective_potion_elapsed_seconds(self) -> float | None:
        if not self.runtime_history:
            return self.potion_elapsed_seconds
        potion_uses = tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExtremeRuntimePotionUse)
            and entry.time_seconds <= self.snapshot_time_seconds + 1e-12
        )
        if not potion_uses:
            return None
        latest = potion_uses[-1]
        return self.snapshot_time_seconds - latest.time_seconds

    @property
    def has_runtime_history_at_snapshot(self) -> bool:
        if not self.runtime_history:
            return bool(self.attempts)
        return any(
            self._entry_order(entry)[0] <= self.snapshot_time_seconds + 1e-12
            for entry in self.ordered_runtime_history
        )
