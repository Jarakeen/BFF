from __future__ import annotations

"""Shared status-application opportunity projection.

This layer does not decide that a stochastic status effect actually procs.  It turns
explicit damage-component events into canonical status opportunities using the shared
ESO status-effect chance table.  Callers may then use the all-procs ceiling for an
Extreme theoretical maximum while keeping deterministic and expected-value claims
separate.
"""

from dataclasses import dataclass
import math

from minmax.status_effect_chance import (
    StatusEffectChanceSource,
    calculate_status_effect_chance,
    status_effect_name_for_damage_type,
)


@dataclass(frozen=True)
class StatusApplicationOpportunity:
    time_seconds: float
    source: str
    damage_type: str
    status_name: str
    chance: float

    @property
    def deterministic(self) -> bool:
        return self.chance >= 1.0 - 1e-12


@dataclass(frozen=True)
class StatusApplicationOpportunityCatalog:
    opportunities: tuple[StatusApplicationOpportunity, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def all_procs_application_ceiling(self) -> int:
        return len(self.opportunities)

    @property
    def deterministic_application_count(self) -> int:
        return sum(1 for row in self.opportunities if row.deterministic)

    @property
    def expected_application_count(self) -> float:
        return sum(float(row.chance) for row in self.opportunities)

    @property
    def all_procs_is_stochastic(self) -> bool:
        return any(not row.deterministic for row in self.opportunities)

    @property
    def denominator_proven(self) -> bool:
        return bool(self.opportunities) and not self.unresolved


class StatusApplicationOpportunityService:
    """Project status opportunities from explicit damage-component cast events."""

    @classmethod
    def from_damage_casts(
        cls,
        *,
        cast_times: tuple[float, ...],
        damage_types: tuple[str, ...],
        source_family: StatusEffectChanceSource,
        increase_percent: float = 0.0,
        source_name: str,
        score_seconds: float,
    ) -> StatusApplicationOpportunityCatalog:
        source = str(source_name or "").strip()
        score = float(score_seconds)
        if not source:
            raise ValueError("status opportunity source name is required")
        if not math.isfinite(score) or score <= 0.0:
            raise ValueError("score time must be finite and greater than zero")
        if not damage_types:
            raise ValueError("at least one damage type is required")

        unresolved: list[str] = []
        typed: list[tuple[str, str]] = []
        for raw_damage_type in damage_types:
            damage_type = str(raw_damage_type or "").strip().casefold()
            status_name = status_effect_name_for_damage_type(damage_type)
            if status_name is None:
                unresolved.append(
                    f"unreviewed status mapping for damage type: {raw_damage_type!r}"
                )
                continue
            typed.append((damage_type, status_name))

        chance = calculate_status_effect_chance(
            source_family,
            increase_percent=float(increase_percent),
        ).final_chance

        opportunities: list[StatusApplicationOpportunity] = []
        ordered_times = tuple(sorted(float(value) for value in cast_times))
        for time_seconds in ordered_times:
            if not math.isfinite(time_seconds) or time_seconds < 0.0:
                unresolved.append(f"invalid cast time: {time_seconds!r}")
                continue
            if time_seconds > score + 1e-9:
                unresolved.append(
                    f"cast at {time_seconds:.3f}s exceeds score window {score:.3f}s"
                )
                continue
            for damage_type, status_name in typed:
                opportunities.append(
                    StatusApplicationOpportunity(
                        time_seconds=time_seconds,
                        source=source,
                        damage_type=damage_type,
                        status_name=status_name,
                        chance=float(chance),
                    )
                )

        return StatusApplicationOpportunityCatalog(
            opportunities=tuple(
                sorted(
                    opportunities,
                    key=lambda row: (
                        row.time_seconds,
                        row.status_name.casefold(),
                        row.damage_type,
                    ),
                )
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "StatusApplicationOpportunity",
    "StatusApplicationOpportunityCatalog",
    "StatusApplicationOpportunityService",
]
