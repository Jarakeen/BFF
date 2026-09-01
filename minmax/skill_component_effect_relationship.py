from __future__ import annotations

"""Canonical Phase 6 relationships from coefficient components to named effects.

This module deliberately models a different relationship shape than
``character_build.effect_relationship``.  A skill coefficient component is not
itself a named EffectVariant identity, so it must never be smuggled into the
``source_effect`` field of an effect-to-effect relationship.

The extractor here is conservative: it only records an application when the
coefficient-local source text explicitly ties an application/infliction verb to
one of the known combat-effect names supplied by the caller.  It does not infer
proc chance, cooldown, duration, uptime, or combat state.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentEffectRelationshipType(str, Enum):
    APPLIES = "applies"


@dataclass(frozen=True)
class SkillComponentEffectRelationship:
    """One verified relationship between a coefficient component and an effect."""

    skill_rank_id: int
    coefficient_number: int
    relationship_type: SkillComponentEffectRelationshipType
    target_effect: str
    source_effect_name: str
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.target_effect:
            raise ValueError("target_effect must be a non-empty canonical identity")
        if not self.source_effect_name:
            raise ValueError("source_effect_name must preserve the named source effect")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


def canonical_effect_identity(name: str) -> str:
    """Normalize a named effect to the EffectVariant-compatible identity form."""

    text = str(name or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def extract_explicit_effect_applications(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    fragment: str,
    known_effect_names: tuple[str, ...] | list[str],
) -> tuple[SkillComponentEffectRelationship, ...]:
    """Extract explicit component-local named-effect applications.

    ``known_effect_names`` is expected to come from the canonical combat-effect
    corpus.  Merely mentioning an effect name is insufficient.  The same local
    fragment must explicitly say that the component applies or inflicts it.
    """

    text = " ".join(str(fragment or "").split())
    if not text:
        return ()

    relationships: list[SkillComponentEffectRelationship] = []
    seen: set[str] = set()

    for raw_name in known_effect_names:
        name = str(raw_name or "").strip()
        if not name:
            continue

        escaped = re.escape(name)
        patterns = (
            rf"\bappl(?:y|ies|ied|ying)\b[^.;]{{0,40}}?\b{escaped}\b(?:\s+status\s+effect)?",
            rf"\binflict(?:s|ed|ing)?\b[^.;]{{0,40}}?\b{escaped}\b(?:\s+status\s+effect)?",
        )
        match = next(
            (candidate for pattern in patterns if (candidate := re.search(pattern, text, flags=re.IGNORECASE))),
            None,
        )
        if match is None:
            continue

        identity = canonical_effect_identity(name)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        relationships.append(
            SkillComponentEffectRelationship(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                relationship_type=SkillComponentEffectRelationshipType.APPLIES,
                target_effect=identity,
                source_effect_name=name,
                evidence=match.group(0),
            )
        )

    return tuple(relationships)
