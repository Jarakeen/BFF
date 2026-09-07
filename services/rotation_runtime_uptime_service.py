from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_recast import RotationRecastSummary
from services.rotation_duration_analysis_service import RotationDurationProjection


@dataclass(frozen=True)
class RotationRuntimeUptimeRequirement:
    """Caller-supplied minimum uptime for one scheduled duration skill.

    This is policy, not inferred ESO truth. Encounter strategy, a role assignment,
    a user objective, or another reviewed source must supply the threshold.
    """

    skill_name: str
    minimum_uptime: float
    bar: str | None = None

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("runtime uptime requirement needs skill_name")
        object.__setattr__(self, "skill_name", name)

        minimum = float(self.minimum_uptime)
        if not math.isfinite(minimum) or not 0.0 <= minimum <= 1.0:
            raise ValueError("runtime uptime minimum must be finite and between 0 and 1")
        object.__setattr__(self, "minimum_uptime", minimum)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("runtime uptime requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationRuntimeUptimeObjective:
    """One caller-selected duration-skill uptime target to maximize.

    Unlike a requirement, this has no pass/fail threshold. It is a soft objective
    considered only after hard rotation obligations have been ordered.
    """

    skill_name: str
    bar: str | None = None

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("runtime uptime objective needs skill_name")
        object.__setattr__(self, "skill_name", name)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("runtime uptime objective bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationRuntimeUptimeAssessment:
    requirement: RotationRuntimeUptimeRequirement
    summary: RotationRecastSummary | None
    unresolved: tuple[str, ...] = ()

    @property
    def observed_uptime(self) -> float | None:
        return None if self.summary is None else float(self.summary.uptime_fraction)

    @property
    def shortfall(self) -> float | None:
        if self.observed_uptime is None:
            return None
        return max(0.0, self.requirement.minimum_uptime - self.observed_uptime)

    @property
    def satisfied(self) -> bool:
        return self.shortfall == 0.0


@dataclass(frozen=True)
class RotationRuntimeUptimeObjectiveAssessment:
    objective: RotationRuntimeUptimeObjective
    summary: RotationRecastSummary | None
    unresolved: tuple[str, ...] = ()

    @property
    def observed_uptime(self) -> float | None:
        return None if self.summary is None else float(self.summary.uptime_fraction)


def assess_rotation_runtime_uptimes(
    *,
    projection: RotationDurationProjection,
    requirements: tuple[RotationRuntimeUptimeRequirement, ...],
) -> tuple[RotationRuntimeUptimeAssessment, ...]:
    """Assess explicit uptime floors against canonical duration/recast evidence."""

    seen: set[tuple[str, str | None]] = set()
    assessments: list[RotationRuntimeUptimeAssessment] = []
    for requirement in requirements:
        key = (requirement.skill_name.casefold(), requirement.bar)
        if key in seen:
            raise ValueError(
                "duplicate runtime uptime requirement for "
                f"{requirement.skill_name!r} on {requirement.bar or 'any'} bar"
            )
        seen.add(key)

        matches = tuple(
            summary
            for summary in projection.analysis.summaries
            if summary.skill_name.casefold() == requirement.skill_name.casefold()
            and (requirement.bar is None or summary.bar == requirement.bar)
        )
        if len(matches) > 1 and requirement.bar is None:
            raise ValueError(
                f"runtime uptime requirement for {requirement.skill_name!r} "
                "is ambiguous across bars"
            )
        if not matches:
            scope = f" on {requirement.bar} bar" if requirement.bar else ""
            assessments.append(
                RotationRuntimeUptimeAssessment(
                    requirement=requirement,
                    summary=None,
                    unresolved=(
                        f"runtime uptime evidence missing for "
                        f"{requirement.skill_name!r}{scope}",
                    ),
                )
            )
            continue

        assessments.append(
            RotationRuntimeUptimeAssessment(
                requirement=requirement,
                summary=matches[0],
            )
        )
    return tuple(assessments)


def assess_rotation_runtime_uptime_objective(
    *,
    projection: RotationDurationProjection,
    objective: RotationRuntimeUptimeObjective,
) -> RotationRuntimeUptimeObjectiveAssessment:
    """Resolve one soft uptime objective without converting unknown evidence to zero."""

    matches = tuple(
        summary
        for summary in projection.analysis.summaries
        if summary.skill_name.casefold() == objective.skill_name.casefold()
        and (objective.bar is None or summary.bar == objective.bar)
    )
    if len(matches) > 1 and objective.bar is None:
        raise ValueError(
            f"runtime uptime objective for {objective.skill_name!r} is ambiguous across bars"
        )
    if not matches:
        scope = f" on {objective.bar} bar" if objective.bar else ""
        return RotationRuntimeUptimeObjectiveAssessment(
            objective=objective,
            summary=None,
            unresolved=(
                f"runtime uptime objective evidence missing for "
                f"{objective.skill_name!r}{scope}",
            ),
        )
    return RotationRuntimeUptimeObjectiveAssessment(
        objective=objective,
        summary=matches[0],
    )
