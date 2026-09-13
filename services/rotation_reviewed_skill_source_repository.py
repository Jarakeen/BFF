from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.skill_coefficient_repository import ability_entity_id


class RotationSkillRuntimeSourceKind(str, Enum):
    PLAYER = "player"
    PET = "pet"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RotationReviewedSkillSource:
    skill_entity_id: str
    source_kind: RotationSkillRuntimeSourceKind
    evidence: tuple[str, ...]


class RotationReviewedSkillSourceRepository:
    """Canonical reviewed source ownership for rotation skills.

    This repository answers *what kind of runtime source owns the skill's repeated
    effect*. It does not identify one ESO Logs actor, infer a pet owner, or define
    timing/damage semantics. Numeric ESO ids remain evidence handles only.
    """

    _REVIEWED = {
        "skeletal_archer": RotationReviewedSkillSource(
            skill_entity_id="skeletal_archer",
            source_kind=RotationSkillRuntimeSourceKind.PET,
            evidence=(
                "Reviewed ESO gameplay classification: Skeletal Archer is considered a pet.",
                "Player-facing skill behavior summons an archer that fights for 20 seconds and attacks independently every 2 seconds.",
            ),
        ),
    }

    def resolve(self, skill_entity_id: str) -> RotationReviewedSkillSource | None:
        identity = ability_entity_id(skill_entity_id)
        if not identity:
            return None
        return self._REVIEWED.get(identity)


__all__ = [
    "RotationReviewedSkillSource",
    "RotationReviewedSkillSourceRepository",
    "RotationSkillRuntimeSourceKind",
]
