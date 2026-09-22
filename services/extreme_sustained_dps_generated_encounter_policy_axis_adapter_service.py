from __future__ import annotations

"""Generated encounter-policy axis for sustained-DPS rotation search."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_encounter_policy_frontier_service import (
    ExtremeSustainedDPSEncounterPolicyChoice,
    ExtremeSustainedDPSEncounterPolicyFrontier,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedEncounterPolicyAxisState:
    assembled: object
    choice: ExtremeSustainedDPSEncounterPolicyChoice | None = None

    @property
    def complete(self) -> bool:
        return bool(self.choice is not None and not self.choice.unresolved)


class ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService:
    """Select one explicit encounter-demand family before rotation-plan generation."""

    def __init__(
        self,
        *,
        frontier: ExtremeSustainedDPSEncounterPolicyFrontier,
    ) -> None:
        self.frontier = frontier

    def _count(self, _state: object) -> int:
        if not self.frontier.denominator_proven:
            raise ValueError(
                "generated encounter-policy axis requires a proven finite denominator"
            )
        return int(self.frontier.candidate_count)

    def _at(
        self,
        state: ExtremeSustainedDPSGeneratedEncounterPolicyAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedEncounterPolicyAxisState:
        count = self._count(state)
        target = int(index)
        if target < 0 or target >= count:
            raise IndexError("generated encounter-policy choice index out of range")
        return ExtremeSustainedDPSGeneratedEncounterPolicyAxisState(
            assembled=state.assembled,
            choice=self.frontier.choices[target],
        )

    def root(self, assembled: object) -> ExtremeSustainedDPSGeneratedEncounterPolicyAxisState:
        return ExtremeSustainedDPSGeneratedEncounterPolicyAxisState(
            assembled=assembled
        )

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Encounter Policy",
                candidate_count=self._count,
                candidate_at=self._at,
                canonical_axes=("encounter_policy",),
            ),
        )

    def coverage(self) -> ExtremeSustainedDPSAxisCoverageProof:
        return ExtremeSustainedDPSAxisCoverageProof(
            source="generated explicit finite encounter-policy denominator",
            dominated_axes=(
                ("encounter_policy",)
                if self.frontier.denominator_proven
                else ()
            ),
            unresolved=tuple(self.frontier.unresolved),
            omitted_scope=tuple(self.frontier.omitted_scope),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService",
    "ExtremeSustainedDPSGeneratedEncounterPolicyAxisState",
]
