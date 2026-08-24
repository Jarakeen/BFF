from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from ..support_stacking import StackingBehavior
from .effect_instance import EffectVariant

ConditionContext = frozenset[str]
"""
The set of named conditions currently known to hold (e.g.
"ice_staff_active_weapon", "target_is_chilled").

This is deliberately just a frozenset of strings rather than a bespoke
class: conditions are opaque names to the engine (it never interprets
what they mean), so the smallest generic container that can grow later
is the right size for this. `None` (as opposed to an empty frozenset)
means "no context was supplied at all" - every condition/prerequisite
check is a pass-through in that case, which is what keeps every
existing caller that never evaluates conditions unaffected.
"""


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

    For REQUIRES, the direction is: `source_effect` requires
    `target_effect` (and/or `condition`) to be eligible. e.g. a
    relationship of REQUIRES(source_effect="minor_brittle",
    target_effect="ice_staff_active_weapon") reads as "minor_brittle
    requires ice_staff_active_weapon". Multiple REQUIRES relationships
    sharing the same `source_effect` are combined with AND - every one of
    them must be satisfied for that effect to remain eligible.
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

    stacking: StackingBehavior | None = None
    """
    For TRIGGERS: the stacking behavior of the newly-produced effect.
    Preserved separately so duplicate-trigger prevention can tell a
    STACKS effect (where multiple independently-triggered instances are
    legitimate) apart from a UNIQUE/HIGHEST_ONLY one (where a second
    trigger is a true duplicate). Unused by other relationship types.
    """


def _condition_satisfied(
    condition: str | None, context: ConditionContext | None
) -> bool:
    """
    Requirement-level condition check shared by every gate in this
    module:

    1. No condition at all -> always satisfied.
    2. A condition is present, but no context was supplied to evaluate
       it against -> treated as satisfied (nothing has been asked to
       evaluate it; every existing caller that never passes a context
       keeps working exactly as before).
    3. A condition is present and a context WAS supplied -> satisfied
       only if that condition is actually in the context.
    """
    if condition is None:
        return True
    if context is None:
        return True
    return condition in context


def resolve_condition_eligibility(
    effects: Iterable[EffectVariant],
    context: ConditionContext | None,
) -> tuple[EffectVariant, ...]:
    """
    Evaluate each effect's own `condition` against `context`, setting
    `eligible` accordingly:

    - No condition -> eligible.
    - Condition present and satisfied by `context` -> eligible.
    - Condition present and not satisfied by `context` -> not eligible.

    The effect is always preserved in the result (as evidence), only its
    `eligible` flag changes. An effect already marked ineligible stays
    ineligible regardless of its own condition (this lets REQUIRES-driven
    ineligibility, applied later in the pipeline, survive a second pass
    over this function without being reset back to True).
    """
    resolved = []
    for effect in effects:
        if not effect.eligible:
            resolved.append(effect)
            continue

        satisfied = _condition_satisfied(effect.condition, context)
        if satisfied == effect.eligible:
            resolved.append(effect)
        else:
            resolved.append(replace(effect, eligible=satisfied))

    return tuple(resolved)


def _resolve_trigger_closure(
    effects: list[EffectVariant],
    relationships: list[EffectRelationship],
    context: ConditionContext | None,
) -> list[EffectVariant]:
    """
    Repeatedly synthesize TRIGGERS-produced effects until a fixed point
    is reached, so proc chains (A triggers B triggers C) resolve without
    depending on relationship ordering.

    Duplicate-trigger prevention is stacking-aware: a target effect that
    already has an eligible instance is only skipped if that existing
    instance (or this relationship's own declared stacking) is NOT
    STACKS. A STACKS effect can legitimately have multiple simultaneous
    instances from different sources.
    """
    resolved = list(effects)

    triggers = [
        relationship
        for relationship in relationships
        if relationship.relationship_type == EffectRelationshipType.TRIGGERS
    ]

    # Bounded by relationship count: each pass either adds at least one
    # new effect or nothing changes, so there can never be more useful
    # passes than there are TRIGGERS relationships.
    for _ in range(len(triggers) + 1):
        changed = False
        eligible_names = {effect.name for effect in resolved if effect.eligible}

        for relationship in triggers:
            if relationship.source_effect not in eligible_names:
                continue

            if not _condition_satisfied(relationship.condition, context):
                continue

            existing_instances = [
                effect
                for effect in resolved
                if effect.name == relationship.target_effect
            ]

            if existing_instances:
                stacks = relationship.stacking == StackingBehavior.STACKS or any(
                    effect.stacking == StackingBehavior.STACKS
                    for effect in existing_instances
                )
                if not stacks:
                    continue

                already_from_this_source = any(
                    effect.source == relationship.source_effect
                    and effect.trigger == relationship.source_effect
                    for effect in existing_instances
                )
                if already_from_this_source:
                    continue

            resolved.append(
                EffectVariant(
                    name=relationship.target_effect,
                    layer=_proc_layer(),
                    source=relationship.source_effect,
                    magnitude=relationship.magnitude_delta,
                    duration=relationship.duration,
                    condition=relationship.condition,
                    trigger=relationship.source_effect,
                    stacking=relationship.stacking,
                )
            )
            changed = True

        if not changed:
            break

    return resolved


def _proc_layer():
    from .effect_layer import EffectLayer

    return EffectLayer.PROC


def _apply_one_shot_adjustments(
    resolved: list[EffectVariant],
    relationships: list[EffectRelationship],
) -> list[EffectVariant]:
    """
    Apply MODIFIES / EXTENDS_DURATION / INCREASES_PROC_CHANCE exactly
    once each, against the fully trigger-resolved effect set, so these
    adjustments can also see effects that only exist because a TRIGGERS
    relationship produced them.
    """
    eligible_names = {effect.name for effect in resolved if effect.eligible}

    for relationship in relationships:
        if relationship.source_effect not in eligible_names:
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

    return resolved


def _apply_requires(
    resolved: list[EffectVariant],
    relationships: list[EffectRelationship],
    context: ConditionContext | None,
) -> list[EffectVariant]:
    """
    Evaluate every REQUIRES relationship against the fully resolved
    effect set and mark unmet requirements ineligible.

    A REQUIRES relationship can name a prerequisite effect
    (`target_effect`), a prerequisite condition (`condition`), or both -
    all parts that are set must hold. Multiple REQUIRES relationships
    sharing the same `source_effect` are combined with AND: any one of
    them failing makes every instance of that effect ineligible.

    Effects are never removed - only their `eligible` flag changes -
    so their original evidence remains inspectable.
    """
    requires = [
        relationship
        for relationship in relationships
        if relationship.relationship_type == EffectRelationshipType.REQUIRES
    ]
    if not requires:
        return resolved

    unmet_sources: set[str] = set()

    for relationship in requires:
        prerequisite_met = True

        if relationship.target_effect:
            prerequisite_met = any(
                effect.name == relationship.target_effect and effect.eligible
                for effect in resolved
            )

        if prerequisite_met and relationship.condition is not None:
            prerequisite_met = _condition_satisfied(relationship.condition, context)

        if not prerequisite_met:
            unmet_sources.add(relationship.source_effect)

    if not unmet_sources:
        return resolved

    return [
        replace(effect, eligible=False)
        if effect.name in unmet_sources
        else effect
        for effect in resolved
    ]


def apply_relationships(
    effects: Iterable[EffectVariant],
    relationships: Iterable[EffectRelationship],
    context: ConditionContext | None = None,
) -> tuple[EffectVariant, ...]:
    """
    Apply a set of generic effect relationships and conditions against an
    already-resolved set of EffectVariant instances.

    Pipeline (see the individual helper functions for detail):

    1. Each effect's own `condition` is evaluated against `context`,
       setting `eligible`.
    2. TRIGGERS relationships are resolved to a fixed point, so proc
       chains (A -> B -> C) work regardless of relationship order.
       Newly-synthesized effects carry the triggering relationship's
       `condition` and `stacking`, and duplicate-trigger prevention
       respects STACKS.
    3. MODIFIES / EXTENDS_DURATION / INCREASES_PROC_CHANCE are each
       applied exactly once against the fully-expanded effect set.
    4. Every synthesized effect's own `condition` is (re-)evaluated
       (step 1's rule set again) so triggered effects that carry a
       gating condition are correctly flagged too.
    5. REQUIRES relationships are evaluated against the fully-expanded
       set and mark unmet prerequisites ineligible - REQUIRES affects
       eligibility, it is not merely informational.

    `context=None` (the default) means "no condition context was
    supplied" - in that mode no condition or REQUIRES prerequisite
    blocks anything, matching this function's original, unconditional
    behavior. PROVIDES remains purely informational; it does not affect
    eligibility.

    This is intentionally generic: no set/skill name is referenced by the
    function itself, only by the relationship *data* a caller supplies.
    """
    relationships = list(relationships)

    resolved = list(resolve_condition_eligibility(effects, context))
    resolved = _resolve_trigger_closure(resolved, relationships, context)
    resolved = _apply_one_shot_adjustments(resolved, relationships)
    resolved = list(resolve_condition_eligibility(resolved, context))
    resolved = _apply_requires(resolved, relationships, context)

    return tuple(resolved)
