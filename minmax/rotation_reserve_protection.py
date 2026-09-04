from __future__ import annotations

from dataclasses import dataclass
import math

from .resource_costs import ResourceType
from .resource_timeline import ResourceTimelineEventKind, ResourceTimelineResult
from .rotation_demand_window import RotationDemandWindow
from .rotation_resource_reserve import RotationResourceReserveAssessment


@dataclass(frozen=True)
class DiscretionaryRotationSpend:
    """One explicitly policy-classified spend that may be delayed or skipped.

    Classification is supplied by encounter/role policy. This layer does not
    infer that a skill is optional merely from its name, role, or action kind.
    """

    time_seconds: float
    source: str

    def __post_init__(self) -> None:
        time_value = float(self.time_seconds)
        if not math.isfinite(time_value) or time_value < 0:
            raise ValueError("discretionary spend time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_value)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("discretionary spend source is required")
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class ReserveProtectionCandidate:
    time_seconds: float
    source: str
    resource: ResourceType
    amount: int


@dataclass(frozen=True)
class RotationReserveProtectionAnalysis:
    """Evidence for how discretionary pre-window spending affects a reserve gap."""

    demand: RotationDemandWindow
    reserve_assessment: RotationResourceReserveAssessment
    candidates: tuple[ReserveProtectionCandidate, ...]
    recoverable_amount: int
    projected_available_if_all_withheld: int

    @property
    def projected_shortfall_if_all_withheld(self) -> int:
        required = self.reserve_assessment.requirement.minimum_amount
        return max(0, required - self.projected_available_if_all_withheld)

    @property
    def can_repair_shortfall(self) -> bool:
        return self.projected_shortfall_if_all_withheld == 0


def analyze_rotation_reserve_protection(
    *,
    timeline: ResourceTimelineResult,
    reserve_assessment: RotationResourceReserveAssessment,
    discretionary_spends: tuple[DiscretionaryRotationSpend, ...],
) -> RotationReserveProtectionAnalysis:
    """Quantify explicitly discretionary spending before one demand window.

    Only matching action-cost events strictly before the demand start qualify.
    Events at the demand start belong to the response itself. Each declared
    discretionary spend must match exactly one timeline action-cost event so
    ambiguity cannot silently select the wrong cast.
    """

    requirement = reserve_assessment.requirement
    demand = reserve_assessment.demand
    if timeline.resource is not requirement.resource:
        raise ValueError(
            "reserve protection timeline resource does not match requirement: "
            f"{timeline.resource.value} != {requirement.resource.value}"
        )

    timeline_candidates = tuple(
        event
        for event in timeline.events
        if event.kind is ResourceTimelineEventKind.ACTION_COST
        and event.time_seconds < demand.start_seconds
    )

    candidates: list[ReserveProtectionCandidate] = []
    seen: set[tuple[float, str]] = set()
    for discretionary in discretionary_spends:
        key = (discretionary.time_seconds, discretionary.source)
        if key in seen:
            raise ValueError(
                f"duplicate discretionary spend declaration: {discretionary.source} at {discretionary.time_seconds:g}s"
            )
        seen.add(key)

        matches = tuple(
            event
            for event in timeline_candidates
            if event.time_seconds == discretionary.time_seconds
            and event.source == discretionary.source
        )
        if not matches:
            raise ValueError(
                "discretionary spend does not match a pre-demand action cost: "
                f"{discretionary.source} at {discretionary.time_seconds:g}s"
            )
        if len(matches) > 1:
            raise ValueError(
                "discretionary spend is ambiguous on the resource timeline: "
                f"{discretionary.source} at {discretionary.time_seconds:g}s"
            )

        event = matches[0]
        amount = max(0, -int(event.applied_change))
        candidates.append(
            ReserveProtectionCandidate(
                time_seconds=event.time_seconds,
                source=event.source,
                resource=timeline.resource,
                amount=amount,
            )
        )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda candidate: (candidate.time_seconds, candidate.source.casefold()),
        )
    )
    recoverable = sum(candidate.amount for candidate in ordered)
    projected = reserve_assessment.available_before_start + recoverable

    return RotationReserveProtectionAnalysis(
        demand=demand,
        reserve_assessment=reserve_assessment,
        candidates=ordered,
        recoverable_amount=recoverable,
        projected_available_if_all_withheld=projected,
    )
