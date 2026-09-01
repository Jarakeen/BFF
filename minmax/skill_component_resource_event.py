from __future__ import annotations

"""Canonical Phase 6 non-Health resource events for skill components.

Phase 6 records only the explicit resource identity and amount basis.
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


class SkillComponentResourceAmountBasis(str, Enum):
    COEFFICIENT = "coefficient"
    PERCENT_MISSING = "percent_missing"


@dataclass(frozen=True)
class SkillComponentResourceEvent:
    skill_rank_id: int
    coefficient_number: int
    event_type: SkillComponentResourceEventType
    resource_type: SkillComponentResourceType
    amount_basis: SkillComponentResourceAmountBasis
    evidence: str
    amount_fraction: float | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if self.amount_basis is SkillComponentResourceAmountBasis.PERCENT_MISSING:
            if self.amount_fraction is None or not (0.0 < self.amount_fraction <= 1.0):
                raise ValueError("percent-missing resource events require amount_fraction in (0, 1]")
        elif self.amount_fraction is not None:
            raise ValueError("coefficient resource events do not carry amount_fraction")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


_COEFFICIENT_RESOURCE_EVENT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,70}?\$(?P<number>\d+)(?!\d)\s+"
    r"(?P<resource>magicka|stamina|ultimate)\b",
    flags=re.IGNORECASE,
)
_PERCENT_MISSING_RESOURCE_EVENT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,45}?(?P<percent>\d+(?:\.\d+)?)\s*%\s+of\s+(?:your|their|the\s+target(?:'s)?)?\s*missing\s+"
    r"(?P<resources>magicka|stamina|ultimate)(?:\s+and\s+(?P<resource2>magicka|stamina|ultimate))?\b",
    flags=re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\$(\d+)(?!\d)")


def _resource_type(value: str) -> SkillComponentResourceType:
    return SkillComponentResourceType(value.casefold())


def extract_explicit_component_resource_events(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentResourceEvent, ...]:
    """Extract explicit coefficient-local Magicka/Stamina/Ultimate gains.

    Two amount shapes are canonical in Phase 6:
    - ``$N Magicka`` / Stamina / Ultimate, where the coefficient is the amount;
    - ``15% of your missing Magicka``, where the percentage is explicit source
      data co-located with the current coefficient-bearing component.

    Health is deliberately excluded because Health restoration belongs to
    healing semantics. Percentage events require the current ``$N`` placeholder
    somewhere in the supplied local fragment so unrelated ability prose is not
    attached to an arbitrary component.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    results: list[SkillComponentResourceEvent] = []
    for match in _COEFFICIENT_RESOURCE_EVENT_RE.finditer(text):
        if int(match.group("number")) != int(coefficient_number):
            continue
        results.append(
            SkillComponentResourceEvent(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                event_type=SkillComponentResourceEventType.GAINS_RESOURCE,
                resource_type=_resource_type(match.group("resource")),
                amount_basis=SkillComponentResourceAmountBasis.COEFFICIENT,
                evidence=match.group(0),
            )
        )

    placeholder_numbers = {int(match.group(1)) for match in _PLACEHOLDER_RE.finditer(text)}
    if int(coefficient_number) not in placeholder_numbers:
        return tuple(results)

    for match in _PERCENT_MISSING_RESOURCE_EVENT_RE.finditer(text):
        percent = float(match.group("percent"))
        if not (0.0 < percent <= 100.0):
            continue
        resources = [match.group("resources")]
        if match.group("resource2"):
            resources.append(match.group("resource2"))
        for resource in resources:
            results.append(
                SkillComponentResourceEvent(
                    skill_rank_id=int(skill_rank_id),
                    coefficient_number=int(coefficient_number),
                    event_type=SkillComponentResourceEventType.GAINS_RESOURCE,
                    resource_type=_resource_type(resource),
                    amount_basis=SkillComponentResourceAmountBasis.PERCENT_MISSING,
                    amount_fraction=percent / 100.0,
                    evidence=match.group(0),
                )
            )

    return tuple(results)
