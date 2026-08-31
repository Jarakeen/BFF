from __future__ import annotations

"""Runtime evidence for per-component critical eligibility.

Static tooltip/coefficient text does not prove whether an ESO damage or healing
component can critically strike/heal.  Runtime combat sources do expose critical
results, however.  This module normalizes those observations and resolves only
unambiguous positive eligibility evidence.

Important rule: absence of an observed critical result never proves ``can_crit =
False``.  A negative value requires a separate authoritative explicit source.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.skill_component_classification import SkillEffectKind


class CriticalEventFamily(str, Enum):
    DAMAGE_DIRECT = "damage_direct"
    DAMAGE_PERIODIC = "damage_periodic"
    HEAL_DIRECT = "heal_direct"
    HEAL_PERIODIC = "heal_periodic"


@dataclass(frozen=True)
class RuntimeCriticalObservation:
    """One or more observed critical combat results for an ability/family."""

    ability_id: int
    event_family: CriticalEventFamily
    source: str
    observed_count: int = 1

    def __post_init__(self) -> None:
        if self.ability_id <= 0:
            raise ValueError("ability_id must be positive")
        if self.observed_count <= 0:
            raise ValueError("observed_count must be positive")
        if not self.source.strip():
            raise ValueError("source is required")


@dataclass(frozen=True)
class CriticalComponentCandidate:
    """Static component identity needed to map a runtime crit observation."""

    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    effect_kind: SkillEffectKind
    is_dot: bool | None
    can_crit: bool | None = None

    @property
    def event_family(self) -> CriticalEventFamily | None:
        if self.is_dot is None:
            return None
        if self.effect_kind is SkillEffectKind.DAMAGE:
            return (
                CriticalEventFamily.DAMAGE_PERIODIC
                if self.is_dot
                else CriticalEventFamily.DAMAGE_DIRECT
            )
        if self.effect_kind is SkillEffectKind.HEAL:
            return (
                CriticalEventFamily.HEAL_PERIODIC
                if self.is_dot
                else CriticalEventFamily.HEAL_DIRECT
            )
        return None

    @property
    def key(self) -> tuple[int, int]:
        return (self.skill_rank_id, self.coefficient_number)


@dataclass(frozen=True)
class ResolvedCriticalEligibility:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    can_crit: bool
    event_family: CriticalEventFamily
    source: str
    observed_count: int


@dataclass(frozen=True)
class CriticalResolutionSummary:
    observations: int
    observation_events: int
    resolved_components: int
    ambiguous_observations: int
    unmatched_observations: int
    already_classified_observations: int


def resolve_observed_critical_eligibility(
    candidates: tuple[CriticalComponentCandidate, ...],
    observations: tuple[RuntimeCriticalObservation, ...],
) -> tuple[tuple[ResolvedCriticalEligibility, ...], CriticalResolutionSummary]:
    """Resolve positive ``can_crit`` evidence only when mapping is unambiguous.

    Runtime sources identify an ability and whether the event is direct/periodic
    damage/healing, but they do not identify BFF's coefficient number.  Therefore
    an observation is applied only when exactly one unresolved component for the
    same ability and event family exists.

    Components whose ``can_crit`` is already known are never overwritten here.
    """

    by_family: dict[tuple[int, CriticalEventFamily], list[CriticalComponentCandidate]] = {}
    classified_by_family: dict[tuple[int, CriticalEventFamily], int] = {}

    for candidate in candidates:
        family = candidate.event_family
        if family is None:
            continue
        key = (candidate.ability_id, family)
        if candidate.can_crit is None:
            by_family.setdefault(key, []).append(candidate)
        else:
            classified_by_family[key] = classified_by_family.get(key, 0) + 1

    grouped_observations: dict[tuple[int, CriticalEventFamily], list[RuntimeCriticalObservation]] = {}
    for observation in observations:
        grouped_observations.setdefault(
            (observation.ability_id, observation.event_family), []
        ).append(observation)

    resolved: list[ResolvedCriticalEligibility] = []
    ambiguous = 0
    unmatched = 0
    already_classified = 0

    for key, group in sorted(
        grouped_observations.items(),
        key=lambda item: (item[0][0], item[0][1].value),
    ):
        eligible = by_family.get(key, [])
        if len(eligible) == 1:
            candidate = eligible[0]
            sources = sorted({item.source.strip() for item in group})
            resolved.append(
                ResolvedCriticalEligibility(
                    skill_rank_id=candidate.skill_rank_id,
                    coefficient_number=candidate.coefficient_number,
                    ability_id=candidate.ability_id,
                    can_crit=True,
                    event_family=key[1],
                    source="; ".join(sources),
                    observed_count=sum(item.observed_count for item in group),
                )
            )
        elif len(eligible) > 1:
            ambiguous += 1
        elif classified_by_family.get(key, 0) > 0:
            already_classified += 1
        else:
            unmatched += 1

    return tuple(resolved), CriticalResolutionSummary(
        observations=len(grouped_observations),
        observation_events=sum(item.observed_count for item in observations),
        resolved_components=len(resolved),
        ambiguous_observations=ambiguous,
        unmatched_observations=unmatched,
        already_classified_observations=already_classified,
    )
