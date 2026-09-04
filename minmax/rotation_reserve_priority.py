from __future__ import annotations

from dataclasses import dataclass

from .rotation_reserve_protection import (
    ReserveProtectionCandidate,
    RotationReserveProtectionAnalysis,
)


@dataclass(frozen=True)
class ReserveProtectionPriority:
    """Explicit policy order for withholding one discretionary action.

    Lower ``delay_order`` values are withheld first. The order is supplied by
    encounter/role policy; this resource layer does not infer relative healing,
    damage, support, or mitigation value from action names or resource cost.
    """

    time_seconds: float
    source: str
    delay_order: int

    def __post_init__(self) -> None:
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("reserve protection priority source is required")
        object.__setattr__(self, "source", source)

        order = int(self.delay_order)
        if order < 0:
            raise ValueError("reserve protection delay order cannot be negative")
        object.__setattr__(self, "delay_order", order)


@dataclass(frozen=True)
class RankedReserveProtectionCandidate:
    candidate: ReserveProtectionCandidate
    delay_order: int


@dataclass(frozen=True)
class RotationReserveProtectionPlan:
    """Smallest policy-ordered withholding prefix needed to repair a reserve gap."""

    analysis: RotationReserveProtectionAnalysis
    ranked_candidates: tuple[RankedReserveProtectionCandidate, ...]
    selected_to_withhold: tuple[RankedReserveProtectionCandidate, ...]
    projected_available_after_selected: int

    @property
    def projected_shortfall_after_selected(self) -> int:
        required = self.analysis.reserve_assessment.requirement.minimum_amount
        return max(0, required - self.projected_available_after_selected)

    @property
    def reserve_repaired(self) -> bool:
        return self.projected_shortfall_after_selected == 0


def plan_rotation_reserve_protection(
    *,
    analysis: RotationReserveProtectionAnalysis,
    priorities: tuple[ReserveProtectionPriority, ...],
) -> RotationReserveProtectionPlan:
    """Apply explicit policy order and select only as much withholding as needed.

    Every candidate must receive exactly one priority declaration. Duplicate
    candidate identities or duplicate delay-order values are rejected rather
    than resolved with an undocumented heuristic.
    """

    priority_by_key: dict[tuple[float, str], ReserveProtectionPriority] = {}
    seen_orders: set[int] = set()
    for priority in priorities:
        key = (float(priority.time_seconds), priority.source)
        if key in priority_by_key:
            raise ValueError(
                f"duplicate reserve protection priority: {priority.source} at {priority.time_seconds:g}s"
            )
        if priority.delay_order in seen_orders:
            raise ValueError(
                f"duplicate reserve protection delay order: {priority.delay_order}"
            )
        priority_by_key[key] = priority
        seen_orders.add(priority.delay_order)

    ranked: list[RankedReserveProtectionCandidate] = []
    candidate_keys = {
        (float(candidate.time_seconds), candidate.source)
        for candidate in analysis.candidates
    }

    extra_keys = set(priority_by_key) - candidate_keys
    if extra_keys:
        time_seconds, source = sorted(extra_keys)[0]
        raise ValueError(
            "reserve protection priority does not match a candidate: "
            f"{source} at {time_seconds:g}s"
        )

    for candidate in analysis.candidates:
        key = (float(candidate.time_seconds), candidate.source)
        priority = priority_by_key.get(key)
        if priority is None:
            raise ValueError(
                "reserve protection candidate is missing explicit priority: "
                f"{candidate.source} at {candidate.time_seconds:g}s"
            )
        ranked.append(
            RankedReserveProtectionCandidate(
                candidate=candidate,
                delay_order=priority.delay_order,
            )
        )

    ordered = tuple(sorted(ranked, key=lambda item: item.delay_order))

    selected: list[RankedReserveProtectionCandidate] = []
    projected = analysis.reserve_assessment.available_before_start
    required = analysis.reserve_assessment.requirement.minimum_amount

    for item in ordered:
        if projected >= required:
            break
        selected.append(item)
        projected += item.candidate.amount

    return RotationReserveProtectionPlan(
        analysis=analysis,
        ranked_candidates=ordered,
        selected_to_withhold=tuple(selected),
        projected_available_after_selected=projected,
    )
