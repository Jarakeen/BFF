from __future__ import annotations

from dataclasses import dataclass

from .rotation_demand_window import RotationDemandWindow
from .rotation_plan import RotationActionKind, RotationPlan


_SUPPORTED_ACTION_KINDS = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.ULTIMATE,
        RotationActionKind.LIGHT_ATTACK,
        RotationActionKind.HEAVY_ATTACK,
    }
)
_NAMED_ACTION_KINDS = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.ULTIMATE,
    }
)


@dataclass(frozen=True)
class RotationTargetCapacityRequirement:
    """Explicit finite target-cap evidence for one action during one demand.

    ``maximum_targets`` is caller/canonical evidence. This contract deliberately
    does not infer geometry, positioning, selection order, ally/enemy identity, or
    whether all potentially coverable targets are actually eligible at runtime.
    """

    demand_name: str
    maximum_targets: int
    action_name: str | None = None
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        if not demand:
            raise ValueError("rotation target capacity requirement needs demand_name")
        object.__setattr__(self, "demand_name", demand)

        maximum = int(self.maximum_targets)
        if maximum <= 0:
            raise ValueError("rotation target capacity maximum_targets must be positive")
        object.__setattr__(self, "maximum_targets", maximum)

        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation target capacity action kind: {self.action_kind!r}"
            ) from exc
        if kind not in _SUPPORTED_ACTION_KINDS:
            raise ValueError(
                "rotation target capacity supports skill, ultimate, light attack, or heavy attack actions"
            )
        object.__setattr__(self, "action_kind", kind)

        name = str(self.action_name or "").strip()
        if kind in _NAMED_ACTION_KINDS:
            if not name:
                raise ValueError(
                    "rotation target capacity requirement needs action_name for skill or ultimate"
                )
            object.__setattr__(self, "action_name", name)
        else:
            if name:
                raise ValueError(
                    "rotation weapon-attack target capacity requirements are kind-identified and must not set action_name"
                )
            object.__setattr__(self, "action_name", None)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation target capacity requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTargetCapacityViolation:
    requirement: RotationTargetCapacityRequirement
    demand: RotationDemandWindow
    time_seconds: float

    @property
    def shortfall(self) -> int:
        return max(0, int(self.demand.target_count) - int(self.requirement.maximum_targets))

    @property
    def reason(self) -> str:
        return (
            f"canonical target cap {self.requirement.maximum_targets} is below "
            f"demand target count {self.demand.target_count}"
        )


@dataclass(frozen=True)
class RotationTargetCapacityAssessment:
    violations: tuple[RotationTargetCapacityViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationTargetCapacityAssessor:
    """Audit explicit per-action target caps against named encounter demands."""

    def assess(
        self,
        plan: RotationPlan,
        demands: tuple[RotationDemandWindow, ...],
        requirements: tuple[RotationTargetCapacityRequirement, ...],
    ) -> RotationTargetCapacityAssessment:
        demand_by_name: dict[str, RotationDemandWindow] = {}
        for demand in demands:
            if demand.name in demand_by_name:
                raise ValueError(f"duplicate rotation demand name: {demand.name!r}")
            demand_by_name[demand.name] = demand

        self._validate_unique(requirements)
        violations: list[RotationTargetCapacityViolation] = []

        for requirement in requirements:
            demand = demand_by_name.get(requirement.demand_name)
            if demand is None:
                raise ValueError(
                    "rotation target capacity requirement references unknown demand "
                    f"{requirement.demand_name!r}"
                )
            if requirement.maximum_targets >= demand.target_count:
                continue

            wanted_name = (
                requirement.action_name.casefold()
                if requirement.action_name is not None
                else None
            )
            for action in plan.actions:
                if action.kind is not requirement.action_kind:
                    continue
                if wanted_name is not None:
                    if not action.name or str(action.name).casefold() != wanted_name:
                        continue
                if requirement.bar is not None and action.bar != requirement.bar:
                    continue
                if not (
                    demand.start_seconds
                    <= float(action.time_seconds)
                    < demand.end_seconds
                ):
                    continue
                violations.append(
                    RotationTargetCapacityViolation(
                        requirement=requirement,
                        demand=demand,
                        time_seconds=float(action.time_seconds),
                    )
                )

        return RotationTargetCapacityAssessment(tuple(violations))

    @staticmethod
    def _validate_unique(
        requirements: tuple[RotationTargetCapacityRequirement, ...],
    ) -> None:
        seen: set[tuple[str, RotationActionKind, str | None, str | None]] = set()
        for requirement in requirements:
            key = (
                requirement.demand_name.casefold(),
                requirement.action_kind,
                (
                    requirement.action_name.casefold()
                    if requirement.action_name is not None
                    else None
                ),
                requirement.bar,
            )
            if key in seen:
                label = requirement.action_name or requirement.action_kind.value
                raise ValueError(
                    "duplicate rotation target capacity requirement for "
                    f"{label!r} in demand {requirement.demand_name!r}"
                )
            seen.add(key)


__all__ = [
    "RotationTargetCapacityAssessment",
    "RotationTargetCapacityAssessor",
    "RotationTargetCapacityRequirement",
    "RotationTargetCapacityViolation",
]
