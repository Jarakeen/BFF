from __future__ import annotations

"""Canonical evidence discovery for target-health execute behavior.

This service is intentionally read-only and scheduler-neutral.  It resolves one
saved/slotted skill name through the canonical coefficient repository, then exposes
only explicit target-health threshold consequences already modeled by Phase 6.

Absence of returned execute evidence is *not* proof that a skill has no execute
behavior.  Unknown or unsupported source semantics remain unresolved rather than
being converted into a negative gameplay claim.
"""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_condition import SkillComponentConditionType
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from minmax.skill_component_conditional_consequence_repository import (
    SkillComponentConditionalConsequenceRepository,
)


@dataclass(frozen=True)
class RotationExecuteComponentEvidence:
    skill_name: str
    entity_id: str
    skill_rank_id: int
    coefficient_number: int
    threshold: float
    consequence_type: SkillComponentConditionalConsequenceType
    maximum_bonus_fraction: float | None
    condition_evidence: str
    consequence_evidence: str


@dataclass(frozen=True)
class RotationExecuteCandidateEvidence:
    requested_skill_name: str
    resolved_skill_name: str | None
    entity_id: str | None
    components: tuple[RotationExecuteComponentEvidence, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def has_threshold_execute_evidence(self) -> bool:
        return bool(self.components)


class RotationExecuteCandidateEvidenceService:
    """Expose explicit target-health execute evidence without inventing policy."""

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE,
        *,
        coefficients: SkillCoefficientRepository | None = None,
        consequences: SkillComponentConditionalConsequenceRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficients or SkillCoefficientRepository(self.database_path)
        self.consequences = consequences or SkillComponentConditionalConsequenceRepository(
            self.database_path
        )

    def resolve(self, skill_name: str) -> RotationExecuteCandidateEvidence:
        requested = str(skill_name or "").strip()
        if not requested:
            return RotationExecuteCandidateEvidence(
                requested_skill_name="",
                resolved_skill_name=None,
                entity_id=None,
                unresolved=("skill name is required for execute evidence",),
            )

        resolution = self.coefficients.resolve_name(requested)
        rank = resolution.rank
        if rank is None:
            return RotationExecuteCandidateEvidence(
                requested_skill_name=requested,
                resolved_skill_name=None,
                entity_id=None,
                unresolved=tuple(resolution.unresolved)
                or (f"canonical skill identity is unresolved for {requested!r}",),
            )

        components: list[RotationExecuteComponentEvidence] = []
        for coefficient in rank.coefficients:
            number = int(coefficient.coefficient_number)
            for consequence in self.consequences.resolve(rank.skill_rank_id, number):
                condition = consequence.condition
                if condition.condition_type is not SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT:
                    continue
                if consequence.consequence_type not in {
                    SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
                    SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                }:
                    continue
                components.append(
                    RotationExecuteComponentEvidence(
                        skill_name=rank.name,
                        entity_id=rank.entity_id,
                        skill_rank_id=rank.skill_rank_id,
                        coefficient_number=number,
                        threshold=float(condition.threshold),
                        consequence_type=consequence.consequence_type,
                        maximum_bonus_fraction=consequence.maximum_bonus_fraction,
                        condition_evidence=condition.evidence,
                        consequence_evidence=consequence.evidence,
                    )
                )

        components.sort(
            key=lambda row: (
                row.threshold,
                row.coefficient_number,
                row.consequence_type.value,
            )
        )
        return RotationExecuteCandidateEvidence(
            requested_skill_name=requested,
            resolved_skill_name=rank.name,
            entity_id=rank.entity_id,
            components=tuple(components),
            unresolved=tuple(resolution.unresolved),
        )


__all__ = [
    "RotationExecuteCandidateEvidence",
    "RotationExecuteCandidateEvidenceService",
    "RotationExecuteComponentEvidence",
]
