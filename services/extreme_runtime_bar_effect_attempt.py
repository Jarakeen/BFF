from __future__ import annotations

"""Preserve active-bar provenance for one Extreme runtime effect attempt.

``RuntimeEffectEventAttempt`` remains the role-neutral Phase 7 event/evidence
primitive.  Extreme gear legality needs one additional fact: which weapon bar was
active when that attempt occurred.  This wrapper carries only that provenance and
never changes trigger, chance, condition, ordering, cooldown, or effect semantics.
"""

from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt


@dataclass(frozen=True)
class ExtremeRuntimeBarEffectAttempt:
    attempt: RuntimeEffectEventAttempt
    active_bar: str

    def __post_init__(self) -> None:
        bar = str(self.active_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError(
                f"unsupported Extreme runtime effect bar: {self.active_bar!r}"
            )
        object.__setattr__(self, "active_bar", bar)

    @property
    def time_seconds(self) -> float:
        return float(self.attempt.event.time_seconds)

    @property
    def sequence(self) -> int:
        return int(self.attempt.event.sequence)
