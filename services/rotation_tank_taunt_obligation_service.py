from __future__ import annotations

"""Source-backed tank taunt application obligations for Rotation Builder.

This service deliberately proves only scheduled taunt *applications*. Canonical
Phase 6 utility semantics identify whether the requested source skill actually
taunts. Taunt duration, refresh cadence, overtaunt/immunity behavior, target
ownership, and encounter-specific maintenance policy remain separate evidence.
"""

from dataclasses import dataclass
import math
from pathlib import Path

from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_utility_effect import SkillComponentUtilityEffectType
from minmax.skill_component_utility_effect_repository import (
    SkillComponentUtilityEffectRepository,
)


@dataclass(frozen=True)
class RotationTankTauntApplicationRequirement:
    requirement_id: str
    source_skill_name: str
    window_start_seconds: float
    window_end_seconds: float
    minimum_applications: int = 1
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        requirement_id = str(self.requirement_id or "").strip()
        source_skill_name = str(self.source_skill_name or "").strip()
        if not requirement_id:
            raise ValueError("tank taunt requirement requires requirement_id")
        if not source_skill_name:
            raise ValueError("tank taunt requirement requires source_skill_name")
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "source_skill_name", source_skill_name)

        start = float(self.window_start_seconds)
        end = float(self.window_end_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("tank taunt window start must be finite and non-negative")
        if not math.isfinite(end) or end < start:
            raise ValueError("tank taunt window end must be finite and >= start")
        object.__setattr__(self, "window_start_seconds", start)
        object.__setattr__(self, "window_end_seconds", end)

        minimum = int(self.minimum_applications)
        if minimum <= 0:
            raise ValueError("tank taunt minimum_applications must be positive")
        object.__setattr__(self, "minimum_applications", minimum)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank taunt requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)

        provenance = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.provenance if str(item).strip()
            )
        )
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True)
class RotationTankTauntApplication:
    time_seconds: float
    sequence: int
    source_skill_name: str
    bar: str | None


@dataclass(frozen=True)
class RotationTankTauntApplicationAssessment:
    requirement: RotationTankTauntApplicationRequirement
    applications: tuple[RotationTankTauntApplication, ...]
    taunt_component_numbers: tuple[int, ...]
    resolved: bool
    satisfied: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationTankTauntObligationService:
    """Assess an explicit taunt-application requirement against one rotation plan.

    The requirement names the exact source skill and timing window. The service
    verifies that skill's canonical rank contains an explicit TAUNT utility component,
    then counts only exact matching scheduled casts in the requested window and bar.

    No taunt duration or continuous-uptime claim is made here.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | object | None = None,
        utility_repository: SkillComponentUtilityEffectRepository | object | None = None,
    ) -> None:
        path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(path)
        self.utility = utility_repository or SkillComponentUtilityEffectRepository(path)

    def assess(
        self,
        *,
        plan: RotationPlan,
        requirement: RotationTankTauntApplicationRequirement,
    ) -> RotationTankTauntApplicationAssessment:
        resolution = self.coefficients.resolve_name(requirement.source_skill_name)
        rank = getattr(resolution, "rank", None)
        if rank is None:
            messages = tuple(getattr(resolution, "unresolved", ())) or (
                "canonical skill rank is unresolved",
            )
            return RotationTankTauntApplicationAssessment(
                requirement=requirement,
                applications=(),
                taunt_component_numbers=(),
                resolved=False,
                satisfied=False,
                unresolved=tuple(
                    f"{requirement.requirement_id}: {message}" for message in messages
                ),
            )

        taunt_components: list[int] = []
        evidence: list[str] = []
        coefficients = tuple(getattr(rank, "coefficients", ()))
        for coefficient in coefficients:
            number = int(getattr(coefficient, "coefficient_number"))
            for utility in self.utility.resolve(rank.skill_rank_id, number):
                if utility.effect_type is not SkillComponentUtilityEffectType.TAUNT:
                    continue
                taunt_components.append(number)
                evidence.append(
                    f"{requirement.source_skill_name} coefficient {number}: {utility.evidence}"
                )

        taunt_components = list(dict.fromkeys(taunt_components))
        evidence = list(dict.fromkeys(evidence))
        if not taunt_components:
            return RotationTankTauntApplicationAssessment(
                requirement=requirement,
                applications=(),
                taunt_component_numbers=(),
                resolved=False,
                satisfied=False,
                unresolved=(
                    f"{requirement.requirement_id}: {requirement.source_skill_name} has no "
                    "source-backed canonical taunt utility component",
                ),
            )

        applications: list[RotationTankTauntApplication] = []
        requested_name = requirement.source_skill_name.casefold()
        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            if str(action.name or "").strip().casefold() != requested_name:
                continue
            time_seconds = float(action.time_seconds)
            if time_seconds < requirement.window_start_seconds:
                continue
            if time_seconds > requirement.window_end_seconds:
                continue
            action_bar = str(action.bar or "").strip().casefold() or None
            if requirement.bar is not None and action_bar != requirement.bar:
                continue
            applications.append(
                RotationTankTauntApplication(
                    time_seconds=time_seconds,
                    sequence=int(action.sequence),
                    source_skill_name=requirement.source_skill_name,
                    bar=action_bar,
                )
            )

        ordered = tuple(
            sorted(
                applications,
                key=lambda item: (item.time_seconds, item.sequence, item.bar or ""),
            )
        )
        satisfied = len(ordered) >= requirement.minimum_applications
        return RotationTankTauntApplicationAssessment(
            requirement=requirement,
            applications=ordered,
            taunt_component_numbers=tuple(taunt_components),
            resolved=True,
            satisfied=satisfied,
            evidence=tuple(evidence),
        )


__all__ = [
    "RotationTankTauntApplication",
    "RotationTankTauntApplicationAssessment",
    "RotationTankTauntApplicationRequirement",
    "RotationTankTauntObligationService",
]
