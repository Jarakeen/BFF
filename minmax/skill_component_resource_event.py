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
    PERCENT_RESOURCE = "percent_resource"


class SkillComponentResourceScalingDriver(str, Enum):
    CURRENT_HEALTH = "current_health"


@dataclass(frozen=True)
class SkillComponentResourceEvent:
    skill_rank_id: int
    coefficient_number: int
    event_type: SkillComponentResourceEventType
    resource_type: SkillComponentResourceType
    amount_basis: SkillComponentResourceAmountBasis
    evidence: str
    amount_fraction: float | None = None
    max_bonus_fraction: float | None = None
    scaling_driver: SkillComponentResourceScalingDriver | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if self.amount_basis in (
            SkillComponentResourceAmountBasis.PERCENT_MISSING,
            SkillComponentResourceAmountBasis.PERCENT_RESOURCE,
        ):
            if self.amount_fraction is None or not (0.0 < self.amount_fraction <= 1.0):
                raise ValueError("percentage resource events require amount_fraction in (0, 1]")
        elif self.amount_fraction is not None:
            raise ValueError("coefficient resource events do not carry amount_fraction")
        if self.max_bonus_fraction is not None and not (0.0 < self.max_bonus_fraction <= 1.0):
            raise ValueError("max_bonus_fraction must be in (0, 1]")
        if (self.max_bonus_fraction is None) != (self.scaling_driver is None):
            raise ValueError("resource scaling requires both max_bonus_fraction and scaling_driver")
        if self.amount_basis is not SkillComponentResourceAmountBasis.PERCENT_RESOURCE and (
            self.max_bonus_fraction is not None or self.scaling_driver is not None
        ):
            raise ValueError("only percent-resource events carry dynamic scaling metadata")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


_RESOURCE_VERB_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b",
    flags=re.IGNORECASE,
)
_COEFFICIENT_RESOURCE_PAIR_RE = re.compile(
    r"\$(?P<number>\d+)(?!\d)\s*(?P<resource>magicka|stamina|ultimate)\b",
    flags=re.IGNORECASE,
)
_PERCENT_MISSING_RESOURCE_EVENT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,45}?(?P<percent>\d+(?:\.\d+)?)\s*%\s+of\s+(?:your|their|the\s+target(?:'s)?)?\s*missing\s+"
    r"(?P<resources>magicka|stamina|ultimate)(?:\s+and\s+(?P<resource2>magicka|stamina|ultimate))?\b",
    flags=re.IGNORECASE,
)
_PERCENT_RESOURCE_EVENT_RE = re.compile(
    r"\b(?:restore|restores|restored|restoring|gain|gains|gained|gaining)\b"
    r"[^.;]{0,45}?(?P<percent>\d+(?:\.\d+)?)\s*%\s+"
    r"(?P<resource>magicka|stamina|ultimate)\b",
    flags=re.IGNORECASE,
)
_CURRENT_HEALTH_SCALING_RE = re.compile(
    r"\bincreas(?:e|es|ed|ing)\s+by\s+up\s+to\s+(?P<percent>\d+(?:\.\d+)?)\s*%"
    r"[^.;]{0,80}?\bbased\s+on\s+how\s+high\s+(?:your|their)\s+current\s+health\s+is\b",
    flags=re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\$(\d+)(?!\d)")


def _resource_type(value: str) -> SkillComponentResourceType:
    return SkillComponentResourceType(value.casefold())


def _coefficient_resource_pairs_after_verb(text: str) -> tuple[re.Match[str], ...]:
    """Return coefficient/resource pairs from explicit gain/restore clauses.

    A single verb may govern more than one coordinated pair, for example
    ``restores $1 Magicka and $2 Stamina``. Pairs are only collected from the
    clause following an explicit resource-gain verb, never from arbitrary text.
    """

    matches: list[re.Match[str]] = []
    for verb in _RESOURCE_VERB_RE.finditer(text):
        clause_end_candidates = [
            index
            for index in (text.find(".", verb.end()), text.find(";", verb.end()))
            if index != -1
        ]
        clause_end = min(clause_end_candidates) if clause_end_candidates else len(text)
        clause = text[verb.end():clause_end]
        matches.extend(_COEFFICIENT_RESOURCE_PAIR_RE.finditer(clause))
    return tuple(matches)


def extract_explicit_component_resource_events(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentResourceEvent, ...]:
    """Extract explicit coefficient-local Magicka/Stamina/Ultimate gains.

    Canonical Phase 6 amount shapes:
    - ``$N Magicka`` / Stamina / Ultimate, where the coefficient is the amount;
    - ``15% of your missing Magicka``, where the percentage is of the missing resource;
    - ``12% Stamina``, where the source explicitly states a percentage resource gain.

    Percentage-of-resource events may also preserve an explicit maximum bonus and
    scaling driver such as ``increasing by up to 100% based on how high your
    current Health is``. Phase 6 records that relationship but does not evaluate
    the current-state multiplier.

    Health is deliberately excluded because Health restoration belongs to
    healing semantics. Percentage events require the current ``$N`` placeholder
    somewhere in the supplied local fragment so unrelated ability prose is not
    attached to an arbitrary component.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    results: list[SkillComponentResourceEvent] = []
    for match in _coefficient_resource_pairs_after_verb(text):
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

    current_health_scaling = _CURRENT_HEALTH_SCALING_RE.search(text)
    max_bonus_fraction: float | None = None
    scaling_driver: SkillComponentResourceScalingDriver | None = None
    if current_health_scaling is not None:
        bonus_percent = float(current_health_scaling.group("percent"))
        if 0.0 < bonus_percent <= 100.0:
            max_bonus_fraction = bonus_percent / 100.0
            scaling_driver = SkillComponentResourceScalingDriver.CURRENT_HEALTH

    for match in _PERCENT_RESOURCE_EVENT_RE.finditer(text):
        # ``15% of your missing Stamina`` belongs to the more specific basis above.
        prefix = text[max(0, match.start() - 20):match.end()].casefold()
        if "missing" in prefix:
            continue
        percent = float(match.group("percent"))
        if not (0.0 < percent <= 100.0):
            continue
        evidence = match.group(0)
        if current_health_scaling is not None:
            evidence = f"{evidence}; {current_health_scaling.group(0)}"
        results.append(
            SkillComponentResourceEvent(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                event_type=SkillComponentResourceEventType.GAINS_RESOURCE,
                resource_type=_resource_type(match.group("resource")),
                amount_basis=SkillComponentResourceAmountBasis.PERCENT_RESOURCE,
                amount_fraction=percent / 100.0,
                max_bonus_fraction=max_bonus_fraction,
                scaling_driver=scaling_driver,
                evidence=evidence,
            )
        )

    return tuple(results)
