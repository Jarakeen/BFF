from __future__ import annotations

"""Collapse sustained-DPS structural active-bar duplicates into one canonical family.

The generated structural frontier inherits an active-bar coordinate from the generic
Extreme universe. Sustained-DPS starting-bar semantics are owned later by the rotation
family. This adapter therefore exposes one race/class-route/attribute choice per exact
front/back pair, but only after validating that the pair differs solely by active_bar.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSGeneratedCandidateService,
    ExtremeSustainedDPSGeneratedFrontier,
    ExtremeSustainedDPSStructuralCandidate,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralFamilyChoice:
    structural_family_index: int
    candidate: ExtremeSustainedDPSStructuralCandidate
    source_front_index: int
    source_back_index: int


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralFamilyFrontier:
    choice_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSStructuralFamilyAdapterService:
    """Expose unique race/class-route/attribute structural families."""

    def __init__(
        self,
        *,
        generated_candidates: ExtremeSustainedDPSGeneratedCandidateService,
    ) -> None:
        self.generated_candidates = generated_candidates

    @staticmethod
    def _same_family(
        left: ExtremeSustainedDPSStructuralCandidate,
        right: ExtremeSustainedDPSStructuralCandidate,
    ) -> bool:
        return bool(
            left.race == right.race
            and left.class_route == right.class_route
            and left.attributes == right.attributes
        )

    def frontier(self) -> ExtremeSustainedDPSStructuralFamilyFrontier:
        source = self.generated_candidates.frontier()
        unresolved = list(source.unresolved)
        count = int(source.structural_candidate_count)

        if not source.structural_denominator_proven:
            unresolved.append(
                "Source sustained-DPS structural denominator is not proven complete"
            )
        if count <= 0:
            unresolved.append("Source sustained-DPS structural frontier is empty")
        if count % 2:
            unresolved.append(
                "Source structural candidate count is not divisible into front/back pairs"
            )

        choice_count = count // 2 if count > 0 and count % 2 == 0 else 0
        complete = bool(
            source.structural_denominator_proven
            and choice_count > 0
            and not unresolved
        )

        return ExtremeSustainedDPSStructuralFamilyFrontier(
            choice_count=choice_count,
            denominator_proven=complete,
            evidence=(
                f"Source structural coordinates: {count}",
                f"Race/class-route/attribute families after active-bar pair collapse: {choice_count}",
                "Each family is materialized from the front coordinate only after exact front/back identity validation",
                "Starting-bar behavior remains owned by the later rotation family",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def choice_at(self, index: int) -> ExtremeSustainedDPSStructuralFamilyChoice:
        frontier = self.frontier()
        if not frontier.denominator_proven:
            raise ValueError(
                "sustained-DPS structural family denominator is unresolved"
            )

        target = int(index)
        if target < 0 or target >= frontier.choice_count:
            raise IndexError("sustained-DPS structural family index out of range")

        front_index = target * 2
        back_index = front_index + 1
        front = self.generated_candidates.candidate_at(front_index)
        back = self.generated_candidates.candidate_at(back_index)

        if str(front.active_bar).strip().casefold() != "front":
            raise ValueError(
                f"structural family {target} expected front coordinate first"
            )
        if str(back.active_bar).strip().casefold() != "back":
            raise ValueError(
                f"structural family {target} expected back coordinate second"
            )
        if not self._same_family(front, back):
            raise ValueError(
                f"structural family {target} front/back coordinates do not describe the same race/class/attribute family"
            )

        return ExtremeSustainedDPSStructuralFamilyChoice(
            structural_family_index=target,
            candidate=front,
            source_front_index=front_index,
            source_back_index=back_index,
        )

    def validate_denominator(self) -> ExtremeSustainedDPSStructuralFamilyFrontier:
        frontier = self.frontier()
        if not frontier.denominator_proven:
            return frontier

        unresolved: list[str] = []
        for index in range(frontier.choice_count):
            try:
                self.choice_at(index)
            except (IndexError, ValueError) as exc:
                unresolved.append(str(exc))

        complete = not unresolved
        return ExtremeSustainedDPSStructuralFamilyFrontier(
            choice_count=frontier.choice_count,
            denominator_proven=complete,
            evidence=(
                *frontier.evidence,
                f"Validated structural front/back family pairs: {frontier.choice_count if complete else frontier.choice_count - len(unresolved)}",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def coverage(self) -> ExtremeSustainedDPSAxisCoverageProof:
        validated = self.validate_denominator()
        return ExtremeSustainedDPSAxisCoverageProof(
            source="validated sustained-DPS structural family denominator",
            dominated_axes=(
                ("race", "class_route", "attributes")
                if validated.denominator_proven
                else ()
            ),
            unresolved=validated.unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSStructuralFamilyAdapterService",
    "ExtremeSustainedDPSStructuralFamilyChoice",
    "ExtremeSustainedDPSStructuralFamilyFrontier",
]
