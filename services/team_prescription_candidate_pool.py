from __future__ import annotations

from dataclasses import dataclass

from minmax.build_candidate_comparison import BuildCandidateComparison

from .team_prescription import PrescribedRoster
from .team_prescription_candidate_ranking import PrescribedSlotCandidateEvidence
from .team_prescription_candidate_source import PrescribedOpenSlotCandidateEvidence


@dataclass(frozen=True)
class PrescribedCandidatePoolInput:
    slot_name: str
    comparison: BuildCandidateComparison | None = None
    open_slot: PrescribedOpenSlotCandidateEvidence | None = None
    provider_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        slot_name = str(self.slot_name).strip()
        if not slot_name:
            raise ValueError("Candidate pool slot_name is required")
        object.__setattr__(self, "slot_name", slot_name)
        if (self.comparison is None) == (self.open_slot is None):
            raise ValueError(
                "candidate pool input requires exactly one of comparison or open_slot"
            )

        provider_ids = tuple(
            str(requirement_id).strip()
            for requirement_id in self.provider_requirement_ids
            if str(requirement_id).strip()
        )
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError(
                f"Duplicate provider requirement evidence for slot {slot_name!r}"
            )
        object.__setattr__(self, "provider_requirement_ids", provider_ids)


@dataclass(frozen=True)
class PrescribedCandidatePoolResult:
    pools: dict[str, tuple[PrescribedSlotCandidateEvidence, ...]]
    unresolved: tuple[str, ...] = ()


def build_prescribed_candidate_pools(
    *,
    roster: PrescribedRoster,
    inputs: tuple[PrescribedCandidatePoolInput, ...],
) -> PrescribedCandidatePoolResult:
    """Group already-evaluated Phase 12 candidates by genuinely open prescribed slot.

    This adapter intentionally does not generate objective values or candidate builds.
    Those remain the responsibility of the existing Phase 12 evaluators/providers.
    It refuses evidence for saved-player anchors, complete prescribed build snapshots,
    or unknown slots so a later candidate source cannot silently replace a filled
    chair.
    """

    assignments = {
        assignment.slot_name.casefold(): assignment for assignment in roster.assignments
    }
    grouped: dict[str, list[PrescribedSlotCandidateEvidence]] = {}
    candidate_ids_by_slot: dict[str, set[str]] = {}

    for item in inputs:
        key = item.slot_name.casefold()
        assignment = assignments.get(key)
        if assignment is None:
            raise ValueError(
                f"Candidate pool input references unknown roster slot {item.slot_name!r}"
            )
        if assignment.player_name is not None or assignment.prescribed_build is not None:
            raise ValueError(
                f"Candidate pool input cannot replace filled slot {item.slot_name!r}"
            )

        candidate_id = (
            item.comparison.candidate.candidate_id
            if item.comparison is not None
            else item.open_slot.candidate.candidate_id
        )
        candidate_id = str(candidate_id).strip()
        seen = candidate_ids_by_slot.setdefault(key, set())
        if candidate_id in seen:
            raise ValueError(
                f"Duplicate candidate {candidate_id!r} for slot {item.slot_name!r}"
            )
        seen.add(candidate_id)

        grouped.setdefault(key, []).append(
            PrescribedSlotCandidateEvidence(
                comparison=item.comparison,
                open_slot=item.open_slot,
                provider_requirement_ids=(
                    item.provider_requirement_ids
                    or (
                        item.open_slot.provider_requirement_ids
                        if item.open_slot is not None
                        else ()
                    )
                ),
            )
        )

    pools: dict[str, tuple[PrescribedSlotCandidateEvidence, ...]] = {}
    unresolved: list[str] = []
    for assignment in roster.assignments:
        if assignment.player_name is not None or assignment.prescribed_build is not None:
            continue
        entries = tuple(grouped.get(assignment.slot_name.casefold(), ()))
        pools[assignment.slot_name] = entries
        if not entries:
            unresolved.append(
                f"{assignment.slot_name}: no evaluated Phase 12 candidate evidence is available"
            )

    return PrescribedCandidatePoolResult(
        pools=pools,
        unresolved=tuple(unresolved),
    )
