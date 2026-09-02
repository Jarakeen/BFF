from __future__ import annotations

"""Canonical Phase 6 dynamic stat-scaling rules for skill components.

Phase 6 records the affected stat, scaling driver, and explicit maximum bonus.
It does not evaluate current combat state or compute the displayed current amount.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentScaledStat(str, Enum):
    HEALTH_RECOVERY = "health_recovery"


class SkillComponentStatScalingDriver(str, Enum):
    MISSING_HEALTH = "missing_health"


@dataclass(frozen=True)
class SkillComponentStatScaling:
    skill_rank_id: int
    coefficient_number: int
    stat: SkillComponentScaledStat
    scaling_driver: SkillComponentStatScalingDriver
    maximum_bonus: float
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if int(self.skill_rank_id) <= 0:
            raise ValueError("skill_rank_id must be positive")
        if int(self.coefficient_number) <= 0:
            raise ValueError("coefficient_number must be positive")
        if float(self.maximum_bonus) <= 0.0:
            raise ValueError("maximum_bonus must be positive")
        if not str(self.evidence).strip():
            raise ValueError("evidence must be non-empty")


_HEALTH_RECOVERY_MISSING_HEALTH_RE = re.compile(
    r"\bincreases?\s+(?:your\s+)?health\s+recovery\s+by\s+up\s+to\s+"
    r"(?P<maximum>\d+(?:\.\d+)?)"
    r"[^.;]{0,80}?\bbased\s+on\s+(?:your\s+)?missing\s+health\b",
    re.IGNORECASE,
)
_CURRENT_AMOUNT_RE = re.compile(
    r"\bcurrent\s+amount\s*:\s*\$(?P<number>\d+)(?!\d)",
    re.IGNORECASE,
)


def extract_explicit_component_stat_scaling(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentStatScaling, ...]:
    """Extract explicit dynamic stat scaling attached to a current-value coefficient.

    Elder Dragon is the initial canonical shape: ``Increases your Health Recovery
    by up to 350, based on your missing Health. Current amount: $1``. The
    coefficient is only the runtime display slot; the static Phase 6 rule is the
    maximum flat Health Recovery bonus and missing-Health driver.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    current = _CURRENT_AMOUNT_RE.search(text)
    scaling = _HEALTH_RECOVERY_MISSING_HEALTH_RE.search(text)
    if current is None or scaling is None:
        return ()
    if int(current.group("number")) != int(coefficient_number):
        return ()

    maximum = float(scaling.group("maximum"))
    if maximum <= 0.0:
        return ()

    return (
        SkillComponentStatScaling(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            stat=SkillComponentScaledStat.HEALTH_RECOVERY,
            scaling_driver=SkillComponentStatScalingDriver.MISSING_HEALTH,
            maximum_bonus=maximum,
            evidence=f"{scaling.group(0)}; {current.group(0)}",
        ),
    )
