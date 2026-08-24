"""
minmax/gear_set_known_effects.py

Data-only registry mapping specific, identified gear-set bonuses to the
canonical named support effect they grant.

This is NOT a text parser and does not attempt to interpret bonus
description strings. The existing GearSetEffectResolver already declines
to interpret triggered/conditional/scaling bonus text (see its own
docstring: "Triggered, conditional, proc, cooldown, scaling, and
trade-off bonuses return an empty list rather than being guessed at.").
This registry follows the same discipline one layer up: every entry here
is a hand-verified mapping from one exact GearSetBonus row - identified
by that bonus's own database id, the strongest identity available, since
a bonus id can never collide across sets or piece-count tiers - to the
already-canonical EffectVariant fields that bonus is known to grant.

Adding support for another gear set's triggered/group bonus means adding
one more entry here, not writing a new resolver or a new effect model.
This registry is the generic part of the bridge; GearSetEffectVariantResolver
(gear_set_effect_variant_resolver.py) contains no set-specific branching
at all. Master Architect is exercised only as the first row below (the
acceptance test for this bridge), never as special-cased code.
"""

from __future__ import annotations

from dataclasses import dataclass

from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class GearSetKnownEffect:
    """
    The already-known EffectVariant shape one specific gear-set bonus
    grants, keyed to that bonus's own database id.

    Every field here maps 1:1 onto an EffectVariant constructor argument
    (see GearSetEffectVariantResolver._to_effect_variant). This does not
    preserve or reinterpret the bonus's description text - it preserves
    the CANONICAL EFFECT IDENTITY (`name`) and structural fields that were
    already true of that effect (e.g. "major_slayer") before this gear set
    was ever considered. This registry never invents a new effect identity
    and never creates a duplicate of an existing one - `name` must always
    be the existing canonical identity string.
    """

    bonus_id: int
    """The gear_set_bonus.id row this entry describes. The real identity key."""

    set_id: int
    piece_count: int

    name: str
    """Canonical effect identity this bonus grants, e.g. "major_slayer". Never new."""

    layer: EffectLayer = EffectLayer.PROC
    """
    Gear-set bonuses are produced by an item under a trigger condition,
    which is exactly what EffectLayer.PROC exists to represent.
    """

    magnitude: float | None = None
    duration: float | None = None
    target_count: int | None = None
    range: float | None = None
    scaling: str | None = None
    """
    Structural description of how this effect's magnitude/duration scale,
    preserved as data - e.g. "1 second per 10 Ultimate spent". This
    registry never evaluates a scaling formula; it only carries the
    formula's description through unchanged.
    """
    condition: str | None = None
    trigger: str | None = None
    target_type: SupportTargetType | None = None
    category: SupportEffectCategory | None = None
    stacking: StackingBehavior | None = None
    exclusivity_group: str | None = None


# ============================================================
# Known bonuses
# ============================================================
#
# Each entry documents its real-world source so a reviewer can verify it
# against the current in-game tooltip without touching code.

MASTER_ARCHITECT_SET_ID = 332
MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID = 1493

_KNOWN_EFFECTS: dict[int, GearSetKnownEffect] = {
    # Master Architect, 5 items:
    # "When you use an Ultimate ability while in combat, you and the
    # closest 5 group members within 28 meters of you gain Major Slayer
    # for 1 second per 10 Ultimate spent, increasing your damage done to
    # Dungeon, Trial, and Arena Monsters by 10%."
    MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID: GearSetKnownEffect(
        bonus_id=MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID,
        set_id=MASTER_ARCHITECT_SET_ID,
        piece_count=5,
        name="major_slayer",
        magnitude=10.0,
        duration=1.0,
        target_count=5,
        range=28.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
        category=SupportEffectCategory.BUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="major_slayer",
    ),
}


def known_effect_for_bonus(bonus_id: int) -> GearSetKnownEffect | None:
    """
    Look up the canonical known-effect spec for one gear-set bonus id, if
    this codebase already has one. Returns None for any bonus without a
    registered mapping - callers must treat that as "not yet interpreted",
    never as "grants nothing".
    """
    return _KNOWN_EFFECTS.get(bonus_id)
