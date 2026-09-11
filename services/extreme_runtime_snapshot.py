from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt


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
    | ExtremeRuntimePotionUse
    | ExternalGroupBuffApplication
)


@dataclass(frozen=True)
class ExtremeRuntimeSnapshot:
    """One deterministic runtime history evaluated at one exact snapshot.

    ``runtime_history`` is the authoritative E1 input when supplied. It carries
    ordinary effect attempts, optional bar-provenance effect attempts, explicit
    potion activations, and explicitly evidenced external group-buff applications
    on one ordered timeline. The older positional fields remain in their original
    order as a compatibility bridge for existing callers, but they cannot be
    supplied alongside ``runtime_history`` so two competing versions of runtime
    truth cannot enter one evaluation.

    Bar provenance is deliberately carried by ``ExtremeRuntimeBarEffectAttempt``
    rather than added to the generic Phase 7 ``RuntimeEvent`` contract. Existing
    effect-history consumers continue to receive ordinary attempts through
    ``effect_attempts`` while dual-bar gear legality can use
    ``bar_effect_attempts`` without reconstructing a bar from guesswork.

    ``recipient_actor_id`` and ``group_member_ids`` provide the roster identity
    evidence required to project external applications. They are ignored when
    no external application exists in the runtime history.

    When unified history is supplied, ``attempts`` and
    ``potion_elapsed_seconds`` are populated as derived compatibility views.
    This keeps older downstream consumers on the same authoritative runtime
    truth while E1 call sites finish migrating to the explicit projection
    properties.
    """

    # Keep the original positional order intact while E1 callers migrate.
    attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
    snapshot_time_seconds: float = 0.0
    potion_elapsed_seconds: float | None = None
    runtime_history: tuple[ExtremeRuntimeHistoryEntry, ...] = ()
    recipient_actor_id: str | None = None
    group_member_ids: tuple[str, ...] = ()

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
                    ExtremeRuntimePotionUse,
                    ExternalGroupBuffApplication,
                ),
            ):
                raise TypeError(
                    "runtime_history entries must be RuntimeEffectEventAttempt, "
                    "ExtremeRuntimeBarEffectAttempt, ExtremeRuntimePotionUse, or "
                    "ExternalGroupBuffApplication"
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
        if isinstance(entry, ExtremeRuntimePotionUse):
            return (float(entry.time_seconds), int(entry.sequence))
        return (float(entry.applied_at_seconds), int(entry.sequence))

    @property
    def ordered_runtime_history(self) -> tuple[ExtremeRuntimeHistoryEntry, ...]:
        """Return the authoritative history in deterministic runtime order."""

        return tuple(sorted(self.runtime_history, key=self._entry_order))

    def snapshot_at(
        self,
        time_seconds: float,
        *,
        sequence: int | None = None,
    ) -> ExtremeRuntimeSnapshot:
        """Project authoritative unified history through one exact ordered instant.

        Unified ``runtime_history`` contains enough event provenance to move the
        observation point forward or backward without inventing state. Legacy
        ``attempts`` / ``potion_elapsed_seconds`` snapshots do not: they describe one
        already-resolved instant and therefore cannot be time-shifted.

        When ``sequence`` is supplied, same-timestamp history entries after that
        sequence are excluded. Without it, all entries at the timestamp are included.
        """

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
        )

    @property
    def effect_attempts(self) -> tuple[RuntimeEffectEventAttempt, ...]:
        """Return ordinary effect attempts for existing Phase 7 history consumers."""

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
        """Return effect attempts whose active-bar provenance is explicitly proven."""

        if not self.runtime_history:
            return ()
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExtremeRuntimeBarEffectAttempt)
        )

    @property
    def unbarred_effect_attempts(self) -> tuple[RuntimeEffectEventAttempt, ...]:
        """Return unified-history attempts that still lack active-bar provenance."""

        if not self.runtime_history:
            return self.attempts
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, RuntimeEffectEventAttempt)
        )

    @property
    def external_group_buff_applications(self) -> tuple[ExternalGroupBuffApplication, ...]:
        """Return explicitly evidenced external applications on the shared timeline."""

        if not self.runtime_history:
            return ()
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, ExternalGroupBuffApplication)
        )

    @property
    def effective_potion_elapsed_seconds(self) -> float | None:
        """Resolve the latest explicit potion use at or before the snapshot."""

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
        """Whether explicit runtime evidence exists at or before the snapshot."""

        if not self.runtime_history:
            return bool(self.attempts)
        return any(
            self._entry_order(entry)[0] <= self.snapshot_time_seconds + 1e-12
            for entry in self.ordered_runtime_history
        )
