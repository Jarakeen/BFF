from __future__ import annotations

"""Canonical Phase 6 non-Health resource events for skill components.

Phase 6 records only the explicit resource identity and event relationship.
Timing, cadence, trigger evaluation, and sustain-rate math remain later concerns.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentResourceEventType(str, Enum):
    GAINS_RESOURCE = "gains_resource"


class SkillComponentResourceType(str, Enum):
    MAGICKA = "magicka"
    STAMINA = "stamina"
    ULTIMATE = "ultimate"


@dataclass(frozen=True)
class SkillComponentResourceEvent:
    skill_rank_id: int
    coefficient_number: int
    event_type: SkillComponentResourceEventType
    resource_type: SkillComponentResourceType
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


_RESOURCE_EVENT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,70}?\$(?P<number>\d+)(?!\d)\s+"
    r"(?P<resource>magicka|stamina|ultimate)\b",
    flags=re.IGNORECASE,
)


def extract_explicit_component_resource_events(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentResourceEvent, ...]:
    """Extract explicit coefficient-owned Magicka/Stamina/Ultimate gains.

    The caller supplies coefficient-local source text. Health is deliberately
    excluded because Health restoration belongs to healing semantics.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    results: list[SkillComponentResourceEvent] = []
    for match in _RESOURCE_EVENT_RE.finditer(text):
        if int(match.group("number")) != int(coefficient_number):
            continue
        resource = SkillComponentResourceType(match.group("resource").casefold())
        results.append(
            SkillComponentResourceEvent(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                event_type=SkillComponentResourceEventType.GAINS_RESOURCE,
                resource_type=resource,
                evidence=match.group(0),
            )
        )
    return tuple(results)
