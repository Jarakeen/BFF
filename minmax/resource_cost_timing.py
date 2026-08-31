from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CostTimingKind(str, Enum):
    ON_ACTIVATION = "on_activation"
    RECURRING = "recurring"


@dataclass(frozen=True)
class ActionCostTiming:
    """Canonical timing for when an ESO action charges its resource cost."""

    kind: CostTimingKind
    interval_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.kind is CostTimingKind.ON_ACTIVATION:
            if self.interval_seconds is not None:
                raise ValueError("Activation costs cannot define a recurring interval")
            return

        if self.kind is CostTimingKind.RECURRING:
            if self.interval_seconds is None or self.interval_seconds <= 0:
                raise ValueError("Recurring costs require a positive interval")
            return

        raise ValueError(f"Unsupported cost timing kind: {self.kind!r}")


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().casefold() in {"1", "true", "yes"}


def _parse_charge_frequency_ms(value: object) -> float:
    """Parse ESO raw chargeFreq, which may contain repeated comma values.

    Banner Bearer currently supplies values such as ``"2000,2000"``. Those
    represent the same recurring interval for each charged resource. Divergent
    values are rejected because Phase 4 does not guess how to map separate
    intervals onto resource pools.
    """

    if value is None:
        raise ValueError("Recurring cost is missing chargeFreq")

    parts = [part.strip() for part in str(value).split(",") if part.strip()]
    if not parts:
        raise ValueError("Recurring cost is missing chargeFreq")

    try:
        frequencies = tuple(float(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Invalid chargeFreq: {value!r}") from exc

    if any(frequency <= 0 for frequency in frequencies):
        raise ValueError(f"Recurring chargeFreq must be positive: {value!r}")

    first = frequencies[0]
    if any(frequency != first for frequency in frequencies[1:]):
        raise ValueError(
            f"Recurring chargeFreq contains divergent intervals: {value!r}"
        )
    return first


def resolve_action_cost_timing(
    *,
    base_is_cost_time: object,
    charge_freq: object = None,
) -> ActionCostTiming:
    """Resolve cost timing from canonical raw ESO ability fields.

    ``baseIsCostTime`` identifies costs that are charged repeatedly rather than
    once on activation. ``chargeFreq`` is stored by the raw source in
    milliseconds and is converted here to seconds.
    """

    if not _parse_bool(base_is_cost_time):
        return ActionCostTiming(CostTimingKind.ON_ACTIVATION)

    interval_ms = _parse_charge_frequency_ms(charge_freq)
    return ActionCostTiming(
        CostTimingKind.RECURRING,
        interval_seconds=interval_ms / 1000.0,
    )
