from __future__ import annotations

import math
from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt


@dataclass(frozen=True)
class ExtremeRuntimeSnapshot:
    """One deterministic runtime history evaluated at one exact snapshot.

    The shared contract stays role-neutral. Ordered effect attempts carry
    their own chance and condition evidence; potion timing is retained here
    until potion use is represented by the same canonical runtime stream.
    """

    attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
    snapshot_time_seconds: float = 0.0
    potion_elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        snapshot = float(self.snapshot_time_seconds)
        if not math.isfinite(snapshot) or snapshot < 0.0:
            raise ValueError("runtime snapshot time must be a finite non-negative number")
        object.__setattr__(self, "snapshot_time_seconds", snapshot)
        object.__setattr__(self, "attempts", tuple(self.attempts))
        if self.potion_elapsed_seconds is None:
            return
        potion_elapsed = float(self.potion_elapsed_seconds)
        if not math.isfinite(potion_elapsed) or potion_elapsed < 0.0:
            raise ValueError(
                "runtime snapshot potion elapsed time must be finite and non-negative"
            )
        object.__setattr__(self, "potion_elapsed_seconds", potion_elapsed)
