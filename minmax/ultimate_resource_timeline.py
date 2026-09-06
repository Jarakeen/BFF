from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class UltimateGenerationEvent:
    """One explicit Ultimate gain event supplied by a caller.

    Phase 13 does not infer these events from attacks, Heroism, passives, traits,
    sets, or encounter state. Callers must provide the evidence directly until
    those generation systems are modeled canonically.
    """

    time_seconds: float
    amount: float
    source: str

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        amount = float(self.amount)
        source = str(self.source or "").strip()
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("ultimate generation event time must be finite and non-negative")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("ultimate generation event amount must be finite and greater than zero")
        if not source:
            raise ValueError("ultimate generation event requires a source")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class UltimateSpendRule:
    """Cost and identity for one schedulable ultimate."""

    skill_name: str
    cost: float

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        cost = float(self.cost)
        if not name:
            raise ValueError("ultimate spend rule requires a skill name")
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("ultimate spend cost must be finite and greater than zero")
        object.__setattr__(self, "skill_name", name)
        object.__setattr__(self, "cost", cost)


@dataclass(frozen=True)
class UltimateResourcePoint:
    time_seconds: float
    amount: float
    source: str


@dataclass(frozen=True)
class UltimateResourceProjection:
    starting_amount: float
    ending_amount: float
    points: tuple[UltimateResourcePoint, ...]
    availability_times: tuple[float, ...]
    unresolved: tuple[str, ...] = ()


class UltimateResourceTimeline:
    """Project explicit Ultimate gains and deterministic affordability windows.

    Availability is emitted when the current balance reaches the supplied ultimate
    cost. When affordability is emitted, the cost is immediately reserved/spent so
    subsequent availability requires enough additional explicit generation.
    """

    def project(
        self,
        *,
        starting_amount: float,
        events: tuple[UltimateGenerationEvent, ...],
        spend_rule: UltimateSpendRule,
        duration_seconds: float,
    ) -> UltimateResourceProjection:
        starting = float(starting_amount)
        duration = float(duration_seconds)
        if not math.isfinite(starting) or starting < 0:
            raise ValueError("starting Ultimate must be finite and non-negative")
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("ultimate timeline duration must be finite and non-negative")

        ordered = tuple(sorted(events, key=lambda event: (event.time_seconds, event.source.casefold())))
        if any(event.time_seconds > duration for event in ordered):
            raise ValueError("ultimate generation event cannot occur after timeline duration")

        balance = starting
        points: list[UltimateResourcePoint] = [
            UltimateResourcePoint(0.0, balance, "starting Ultimate")
        ]
        availability: list[float] = []

        def spend_available(at_time: float) -> None:
            nonlocal balance
            while balance >= spend_rule.cost:
                availability.append(at_time)
                balance -= spend_rule.cost
                points.append(
                    UltimateResourcePoint(
                        at_time,
                        balance,
                        f"reserve {spend_rule.skill_name} cost",
                    )
                )

        spend_available(0.0)
        for event in ordered:
            balance += event.amount
            points.append(
                UltimateResourcePoint(event.time_seconds, balance, event.source)
            )
            spend_available(event.time_seconds)

        return UltimateResourceProjection(
            starting_amount=starting,
            ending_amount=balance,
            points=tuple(points),
            availability_times=tuple(availability),
        )
