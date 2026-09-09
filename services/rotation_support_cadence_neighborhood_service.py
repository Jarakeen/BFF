from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadencePlanCandidate,
)
from services.rotation_support_refresh_cadence_service import (
    RotationSupportRefreshCadenceResult,
)


class _CadenceMaterializer(Protocol):
    def materialize(
        self,
        *,
        seed_plan: RotationPlan,
        cadence_result: RotationSupportRefreshCadenceResult,
        priorities: AbilityPriorityList | None = None,
        source_bar: str | None = None,
    ) -> tuple[RotationSupportCadencePlanCandidate, ...]: ...


@dataclass(frozen=True)
class RotationSupportCadenceNeighborhoodObligation:
    """One explicit cadence family to vary against a complete seed rotation."""

    cadence_result: RotationSupportRefreshCadenceResult
    source_bar: str | None = None

    def __post_init__(self) -> None:
        if self.source_bar is None:
            return
        bar = str(self.source_bar).strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("support cadence neighborhood source_bar must be front or back")
        object.__setattr__(self, "source_bar", bar)


@dataclass(frozen=True)
class RotationSupportCadenceNeighborhood:
    """A bounded local search neighborhood around one complete seed rotation."""

    seed_plan: RotationPlan
    candidates: tuple[RotationSupportCadencePlanCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationSupportCadenceNeighborhoodService:
    """Generate local whole-rotation alternatives without Cartesian expansion.

    Each supplied support obligation is varied independently against the same seed
    plan. This intentionally creates a one-change neighborhood rather than combining
    every cadence choice across every effect. Downstream evaluation/ranking can pick
    a preferred neighbor; callers may then use that complete winner as a new seed for
    another iteration when progressive optimization is desired.

    Unresolved cadence families remain visible in the returned evidence instead of
    being silently skipped. Candidate mechanics, sustain, encounter eligibility, and
    recommendation remain owned by the existing evaluation/ranking layers.
    """

    def __init__(self, materializer: _CadenceMaterializer) -> None:
        self.materializer = materializer

    def generate(
        self,
        *,
        seed_plan: RotationPlan,
        obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...],
        priorities: AbilityPriorityList | None = None,
    ) -> RotationSupportCadenceNeighborhood:
        candidates: list[RotationSupportCadencePlanCandidate] = []
        unresolved: list[str] = []
        seen_ids: set[str] = set()

        for obligation in obligations:
            cadence_result = obligation.cadence_result
            for item in cadence_result.unresolved:
                text = str(item or "").strip()
                if text:
                    unresolved.append(
                        f"{cadence_result.effect_key}:{cadence_result.source_skill_id}: {text}"
                    )

            materialized = self.materializer.materialize(
                seed_plan=seed_plan,
                cadence_result=cadence_result,
                priorities=priorities,
                source_bar=obligation.source_bar,
            )
            for candidate in materialized:
                key = str(candidate.candidate_id or "").strip().casefold()
                if not key:
                    raise ValueError("support cadence neighborhood candidate_id must be non-empty")
                if key in seen_ids:
                    raise ValueError(
                        f"duplicate support cadence neighborhood candidate_id: {candidate.candidate_id!r}"
                    )
                seen_ids.add(key)
                candidates.append(candidate)

        return RotationSupportCadenceNeighborhood(
            seed_plan=seed_plan,
            candidates=tuple(candidates),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationSupportCadenceNeighborhood",
    "RotationSupportCadenceNeighborhoodObligation",
    "RotationSupportCadenceNeighborhoodService",
]
