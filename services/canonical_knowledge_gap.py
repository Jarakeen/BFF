from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CanonicalKnowledgeDomain(str, Enum):
    """Broad evidence domains shared by Comp Maker, Rotation Maker, and Optimizer."""

    ASSIGNMENT_POLICY = "assignment_policy"
    EFFECT_DURATION = "effect_duration"
    EFFECT_UPTIME = "effect_uptime"
    ENCOUNTER_DEMAND = "encounter_demand"
    RESOURCE_RECOVERY = "resource_recovery"
    RESERVE_POLICY = "reserve_policy"
    PASSIVE = "passive"
    GEAR_EFFECT = "gear_effect"
    SKILL_MECHANIC = "skill_mechanic"
    PROC_CONDITION = "proc_condition"
    COOLDOWN = "cooldown"
    TARGETING = "targeting"
    MOVEMENT = "movement"
    OTHER = "other"


@dataclass(frozen=True)
class CanonicalKnowledgeGap:
    """One explicit research gap that can improve multiple optimization surfaces.

    A gap is intentionally descriptive rather than speculative. `needed_evidence`
    tells a researcher what fact must be brought back; `consumers` states which
    systems become smarter when that fact is resolved.
    """

    domain: CanonicalKnowledgeDomain
    key: str
    summary: str
    needed_evidence: str
    consumers: tuple[str, ...]
    source_context: str

    def __post_init__(self) -> None:
        for field_name in ("key", "summary", "needed_evidence", "source_context"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"canonical knowledge gap {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        normalized_consumers: list[str] = []
        seen: set[str] = set()
        for consumer in self.consumers:
            value = str(consumer or "").strip().casefold()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_consumers.append(value)
        if not normalized_consumers:
            raise ValueError("canonical knowledge gap requires at least one consumer")
        object.__setattr__(self, "consumers", tuple(normalized_consumers))


__all__ = [
    "CanonicalKnowledgeDomain",
    "CanonicalKnowledgeGap",
]
