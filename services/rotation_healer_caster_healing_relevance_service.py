from __future__ import annotations

"""Reviewed skill-level relevance for caster-owned healer output.

This layer answers a deliberately narrow question before tooltip/component healing
projection runs: does activating this canonical skill identity itself have a
caster-owned healing consequence that the action projector must inspect?

It does not classify support value, damage value, proc value, or encounter value.
A skill may be extremely important to a healer rotation while still having no
caster-owned healing event. Conversely, an externally triggered heal is not treated
as "no healing" merely because the cast itself emits no heal event.

Unknown identities remain unresolved by returning ``None``. The action projector
then follows its normal fail-closed component path.
"""

from dataclasses import dataclass
from enum import Enum


class RotationHealerCasterHealingRelevance(str, Enum):
    NO_CASTER_HEALING = "no_caster_healing"
    EXTERNAL_CONDITIONAL_HEALING = "external_conditional_healing"


@dataclass(frozen=True)
class RotationHealerCasterHealingRelevanceEvidence:
    skill_id: str
    relevance: RotationHealerCasterHealingRelevance
    provenance: tuple[str, ...]
    game_version: str

    def __post_init__(self) -> None:
        skill_id = str(self.skill_id or "").strip().casefold()
        if not skill_id:
            raise ValueError("caster-healing relevance evidence requires skill_id")
        object.__setattr__(self, "skill_id", skill_id)

        provenance = tuple(
            dict.fromkeys(
                str(item).strip() for item in self.provenance if str(item).strip()
            )
        )
        if not provenance:
            raise ValueError("caster-healing relevance evidence requires provenance")
        object.__setattr__(self, "provenance", provenance)

        version = str(self.game_version or "").strip()
        if not version:
            raise ValueError("caster-healing relevance evidence requires game_version")
        object.__setattr__(self, "game_version", version)


class RotationHealerCasterHealingRelevanceService:
    """Resolve reviewed skill-level caster-healing relevance by semantic identity."""

    _REVIEWED: dict[str, RotationHealerCasterHealingRelevanceEvidence] = {
        "elemental_susceptibility": RotationHealerCasterHealingRelevanceEvidence(
            skill_id="elemental_susceptibility",
            relevance=RotationHealerCasterHealingRelevance.NO_CASTER_HEALING,
            provenance=(
                "reviewed U50 tooltip: Major Breach plus periodic Burning, Chilled, and Concussion status effects; no caster-owned healing consequence",
            ),
            game_version="U50",
        ),
        "expansive_frost_cloak": RotationHealerCasterHealingRelevanceEvidence(
            skill_id="expansive_frost_cloak",
            relevance=RotationHealerCasterHealingRelevance.NO_CASTER_HEALING,
            provenance=(
                "reviewed U50 tooltip: grants Major Resolve to caster/grouped allies; no caster-owned healing consequence",
            ),
            game_version="U50",
        ),
        "winters_revenge": RotationHealerCasterHealingRelevanceEvidence(
            skill_id="winters_revenge",
            relevance=RotationHealerCasterHealingRelevance.NO_CASTER_HEALING,
            provenance=(
                "reviewed U50 tooltip: periodic Frost Damage, snare, and increased Chilled application chance; no caster-owned healing consequence",
            ),
            game_version="U50",
        ),
        "overflowing_altar": RotationHealerCasterHealingRelevanceEvidence(
            skill_id="overflowing_altar",
            relevance=RotationHealerCasterHealingRelevance.EXTERNAL_CONDITIONAL_HEALING,
            provenance=(
                "reviewed U50 tooltip: Minor Lifesteal healing is triggered when affected enemies are damaged; Blood Feast healing is ally synergy-owned",
            ),
            game_version="U50",
        ),
    }

    def resolve(
        self,
        skill_id: str,
    ) -> RotationHealerCasterHealingRelevanceEvidence | None:
        key = str(skill_id or "").strip().casefold()
        if not key:
            return None
        return self._REVIEWED.get(key)


__all__ = [
    "RotationHealerCasterHealingRelevance",
    "RotationHealerCasterHealingRelevanceEvidence",
    "RotationHealerCasterHealingRelevanceService",
]
