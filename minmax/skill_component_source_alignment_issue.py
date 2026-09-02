from __future__ import annotations

"""Explicit unsupported source-alignment records for active coefficient slots.

This is not a mechanic model. It preserves cases where the coefficient source is
internally aligned at the raw-slot level but the tooltip placeholder numbering
cannot be trusted to assign a visible mechanic to that active slot.
"""

from dataclasses import dataclass
from enum import Enum


class SkillComponentSourceAlignmentIssueType(str, Enum):
    SPECIAL_COEFFICIENT_DISPLAY_MISMATCH = "special_coefficient_display_mismatch"


@dataclass(frozen=True)
class SkillComponentSourceAlignmentIssue:
    skill_rank_id: int
    coefficient_number: int
    coefficient_type: str
    issue_type: SkillComponentSourceAlignmentIssueType
    evidence: str
    source: str = "raw_slot+raw_description+coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.coefficient_type:
            raise ValueError("coefficient_type must be non-empty")
        if not self.evidence:
            raise ValueError("evidence must be non-empty")
