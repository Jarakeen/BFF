from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt


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


ExtremeRuntimeHistoryEntry = RuntimeEffectEventAttempt | ExtremeRuntimePotionUse


@dataclass(frozen=True)
class ExtremeRuntimeSnapshot:
    """One deterministic runtime history evaluated at one exact snapshot.

    ``runtime_history`` is the authoritative E1 input when supplied. It carries
    ordinary effect attempts and explicit potion activations on the same
    timestamp / sequence ordered timeline. The older positional fields remain
    in their original order as a compatibility bridge for existing callers,
    but they cannot be supplied alongside ``runtime_history`` so two competing
    versions of runtime truth cannot enter one evaluation.

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

    def __post_init__(self) -> None:
        snapshot = float(self.snapshot_time_seconds)
        if not math.isfinite(snapshot) or snapshot < 0.0:
            raise ValueError("runtime snapshot time must be a finite non-negative number")
        object.__setattr__(self, "snapshot_time_seconds", snapshot)

        history = tuple(self.runtime_history)
        attempts = tuple(self.attempts)
        supplied_potion_elapsed = self.potion_elapsed_seconds
        object.__setattr__(self, "runtime_history", history)
        object.__setattr__(self, "attempts", attempts)

        if history and (attempts or supplied_potion_elapsed is not None):
            raise ValueError(
                "runtime_history cannot be combined with legacy attempts or potion_elapsed_seconds"
            )

        for entry in history:
            if not isinstance(entry, (RuntimeEffectEventAttempt, ExtremeRuntimePotionUse)):
                raise TypeError(
                    "runtime_history entries must be RuntimeEffectEventAttempt or ExtremeRuntimePotionUse"
                )

        if history:
            ordered = tuple(sorted(history, key=self._entry_order))
            projected_attempts = tuple(
                entry
                for entry in ordered
                if isinstance(entry, RuntimeEffectEventAttempt)
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
        return (float(entry.time_seconds), int(entry.sequence))

    @property
    def ordered_runtime_history(self) -> tuple[ExtremeRuntimeHistoryEntry, ...]:
        """Return the authoritative history in deterministic runtime order."""

        return tuple(sorted(self.runtime_history, key=self._entry_order))

    @property
    def effect_attempts(self) -> tuple[RuntimeEffectEventAttempt, ...]:
        """Return effect attempts for existing Phase 7 history consumers."""

        if not self.runtime_history:
            return self.attempts
        return tuple(
            entry
            for entry in self.ordered_runtime_history
            if isinstance(entry, RuntimeEffectEventAttempt)
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
