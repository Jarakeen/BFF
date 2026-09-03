from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeledDamagePotency:
    """One authoritative DD metric supplied to Phase 12 orchestration.

    The value may represent a verified single event or another explicitly named
    damage metric. It is not automatically raid DPS or a rotation ceiling.
    """

    value: float | None
    metric_name: str
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("Damage metric_name is required.")
        if self.value is not None and self.value < 0:
            raise ValueError("Damage metric value cannot be negative.")

    @property
    def resolved(self) -> bool:
        return self.value is not None and not self.unresolved
