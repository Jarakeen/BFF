from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from .effect_instance import EffectVariant


class EffectRelationshipType(str, Enum):
    """
    The kinds of relationship one named effect can have to another.

    This is deliberately generic - it is what lets Jorvuld's Guidance,
    Serpent's Disdain, Aggressive Horn, and Master's Architect all be
    expressed as data using the same handful of relationship types,
    rather than each becoming its own hard-coded rule in the engine.
    """

    PROVIDES = "provides"
    MODIFIES = "modifies"
    TRIGGERS = "triggers"
    REQUIRES = "requires"
    EXTENDS_DURATION = "extends_duration"
    INCREASES_PROC_CHANCE = "increases_proc_chance"


@dataclass(frozen=True)
class EffectRelationship:
    """
    A generic relationship between two named effect identities.

    `source_effect` and `target_effect` are stable snake_case identities
    (matching EffectVariant.name), never magnitudes. `magnitude_delta`
    holds whatever numeric adjustment the relationship applies (an added
    duration, a percentage-point chance increase, etc.) - the relationship
    type says what that number means.
    """

    relationship_type: EffectRelationshipType
    source_effect: str
    target_effect: str

    magnitude_delta: float | None = None
    condition: str | None = None

    duration: float | None = None
    """
    For TRIGGERS: the initial duration of the newly-produced effect
    (preserved separately from magnitude_delta, per the rule that an
    effect's numeric attributes are never collapsed into one generic
    value). Unused by other relationship types.
    """


def apply_relationships(
    effects: Iterable[EffectVariant],
    relationships: Iterable[EffectRelationship],
) -> tuple[EffectVariant, ...]:
    """
    Apply a set of generic effect relationships against an already-resolved
    set of EffectVariant instances.

    - MODIFIES / EXTENDS_DURATION / INCREASES_PROC_CHANCE: when the
      relationship's `source_effect` is present among `effects`, adjust
      every matching `target_effect` instance's duration/chance/magnitude
      by `magnitude_delta`.
    - TRIGGERS: when `source_effect` is present, and no instance of
      `target_effect` already exists, synthesize one sourced from the
      relationship (this is what lets Aggressive Horn "trigger" a support
      effect that isn't otherwise on the bar).
    - PROVIDES / REQUIRES: informational only here; a future evaluator
      decides eligibility, this function does not filter effects out.

    This is intentionally generic: no set/skill name is referenced by the
    function itself, only by the relationship *data* a caller supplies.
    """
    resolved = list(effects)
    present_names = {effect.name for effect in resolved}

    for relationship in relationships:
        if relationship.source_effect not in present_names:
            continue

        if relationship.relationship_type == EffectRelationshipType.EXTENDS_DURATION:
            resolved = [
                replace(
                    effect,
                    duration=(effect.duration or 0.0)
                    + (relationship.magnitude_delta or 0.0),
                )
                if effect.name == relationship.target_effect
                else effect
                for effect in resolved
            ]

        elif (
            relationship.relationship_type
            == EffectRelationshipType.INCREASES_PROC_CHANCE
        ):
            resolved = [
                replace(
                    effect,
                    chance=min(
                        1.0,
                        (effect.chance or 0.0)
                        + (relationship.magnitude_delta or 0.0),
                    ),
                )
                if effect.name == relationship.target_effect
                else effect
                for effect in resolved
            ]

        elif relationship.relationship_type == EffectRelationshipType.MODIFIES:
            resolved = [
                replace(
                    effect,
                    magnitude=(effect.magnitude or 0.0)
                    + (relationship.magnitude_delta or 0.0),
                )
                if effect.name == relationship.target_effect
                else effect
                for effect in resolved
            ]

        elif relationship.relationship_type == EffectRelationshipType.TRIGGERS:
            already_present = any(
                effect.name == relationship.target_effect for effect in resolved
            )
            if not already_present:
                from .effect_layer import EffectLayer

                resolved.append(
                    EffectVariant(
                        name=relationship.target_effect,
                        layer=EffectLayer.PROC,
                        source=relationship.source_effect,
                        magnitude=relationship.magnitude_delta,
                        duration=relationship.duration,
                        condition=relationship.condition,
                        trigger=relationship.source_effect,
                    )
                )
                present_names.add(relationship.target_effect)

    return tuple(resolved)
