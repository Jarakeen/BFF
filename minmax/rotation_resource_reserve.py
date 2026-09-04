from __future__ import annotations

from dataclasses import dataclass
import math

from .resource_costs import ResourceType
from .resource_timeline import ResourceTimelineResult
from .rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class RotationResourceReserveRequirement:
    """Explicit resource floor required immediately before one demand window.

    The minimum is policy/evidence supplied. This layer deliberately does not
    invent how much magicka/stamina a mechanic requires; later planners may
    derive it from verified required actions and encounter evidence.
    """

    demand_name: str
    resource: ResourceType
    minimum_amount: int

    def __post_init__(self) -> None:
        name = str(self.demand_name or "").strip()
        if not name:
            raise ValueError("resource reserve demand name is required")
        object.__setattr__(self, "demand_name", name)

        if not isinstance(self.resource, ResourceType):
            object.__setattr__(self, "resource", ResourceType(str(self.resource)))

        minimum = int(self.minimum_amount)
        if minimum < 0:
            raise ValueError("resource reserve minimum cannot be negative")
        object.__setattr__(self, "minimum_amount", minimum)


@dataclass(frozen=True)
class RotationResourceReserveAssessment:
    demand: RotationDemandWindow
    requirement: RotationResourceReserveRequirement
    available_before_start: int

    @property
    def shortfall(self) -> int:
        return max(0, self.requirement.minimum_amount - self.available_before_start)

    @property
    def satisfied(self) -> bool:
        return self.shortfall == 0


def resource_amount_before(
    timeline: ResourceTimelineResult,
    time_seconds: float,
) -> int:
    """Return pool state immediately before all events at ``time_seconds``.

    Demand-window entry checks intentionally use a strict-before boundary. An
    action placed exactly at the demand start belongs to the demand itself and
    must not reduce the reserve that was available on entry.
    """

    time_value = float(time_seconds)
    if not math.isfinite(time_value) or time_value < 0:
        raise ValueError("resource reserve time must be finite and non-negative")

    amount = timeline.starting_amount
    for event in timeline.events:
        if event.time_seconds >= time_value:
            break
        amount = event.after
    return amount


def assess_rotation_resource_reserve(
    *,
    timeline: ResourceTimelineResult,
    demand: RotationDemandWindow,
    requirement: RotationResourceReserveRequirement,
) -> RotationResourceReserveAssessment:
    """Check one explicit reserve requirement against a deterministic timeline."""

    if timeline.resource is not requirement.resource:
        raise ValueError(
            "resource reserve requirement does not match timeline: "
            f"{requirement.resource.value} != {timeline.resource.value}"
        )
    if demand.name != requirement.demand_name:
        raise ValueError(
            "resource reserve requirement does not match demand window: "
            f"{requirement.demand_name!r} != {demand.name!r}"
        )

    return RotationResourceReserveAssessment(
        demand=demand,
        requirement=requirement,
        available_before_start=resource_amount_before(
            timeline,
            demand.start_seconds,
        ),
    )


def assess_rotation_resource_reserves(
    *,
    timeline: ResourceTimelineResult,
    demands: tuple[RotationDemandWindow, ...],
    requirements: tuple[RotationResourceReserveRequirement, ...],
) -> tuple[RotationResourceReserveAssessment, ...]:
    """Assess matched demand requirements in demand order.

    Missing requirements stay absent rather than silently receiving a zero
    reserve policy. Duplicate requirement names are rejected because choosing
    between conflicting reserve floors would be an undocumented heuristic.
    """

    by_name: dict[str, RotationResourceReserveRequirement] = {}
    for requirement in requirements:
        if requirement.demand_name in by_name:
            raise ValueError(
                f"duplicate resource reserve requirement for {requirement.demand_name}"
            )
        by_name[requirement.demand_name] = requirement

    assessments: list[RotationResourceReserveAssessment] = []
    for demand in demands:
        requirement = by_name.get(demand.name)
        if requirement is None:
            continue
        assessments.append(
            assess_rotation_resource_reserve(
                timeline=timeline,
                demand=demand,
                requirement=requirement,
            )
        )
    return tuple(assessments)
