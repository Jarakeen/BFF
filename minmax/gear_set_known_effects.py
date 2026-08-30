"""
minmax/gear_set_known_effects.py

Data-only registry mapping identified gear-set bonuses to canonical
support-effect identities.

Mappings are keyed by exact bonus id when that identity is stable in the
imported database. For additional verified sets, the registry may also use
the exact set name + piece count. The resolver still refuses to parse or
invent effects from arbitrary tooltip text.
"""

from __future__ import annotations

from dataclasses import dataclass

from .character_build.effect_layer import EffectLayer
from .support_effect_category import SupportEffectCategory
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class GearSetKnownEffect:
    """Canonical effect granted by one identified gear-set bonus."""

    bonus_id: int | None
    set_id: int | None
    piece_count: int
    name: str
    set_name: str | None = None
    layer: EffectLayer = EffectLayer.PROC
    magnitude: float | None = None
    duration: float | None = None
    target_count: int | None = None
    range: float | None = None
    scaling: str | None = None
    condition: str | None = None
    trigger: str | None = None
    target_type: SupportTargetType | None = None
    category: SupportEffectCategory | None = None
    stacking: StackingBehavior | None = None
    exclusivity_group: str | None = None


MASTER_ARCHITECT_SET_ID = 332
MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID = 1493

_KNOWN_EFFECTS: dict[int, GearSetKnownEffect] = {
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

# These mappings are intentionally keyed by set name + piece count rather
# than guessed database ids. The current ESO database may be rebuilt/imported
# and assign different row ids, while the canonical set names remain stable.
_KNOWN_EFFECTS_BY_SET: tuple[GearSetKnownEffect, ...] = (
    GearSetKnownEffect(
        bonus_id=None,
        set_id=None,
        set_name="Spell Power Cure",
        piece_count=5,
        name="major_courage",
        layer=EffectLayer.PROC,
        magnitude=430.0,
        duration=5.0,
        trigger="overheal_self_or_ally",
        target_type=SupportTargetType.ALLY,
        category=SupportEffectCategory.BUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="major_courage",
    ),
    GearSetKnownEffect(
        bonus_id=None,
        set_id=None,
        set_name="Corpseburster",
        piece_count=5,
        name="minor_breach",
        layer=EffectLayer.PROC,
        magnitude=2974.0,
        duration=5.0,
        trigger="corpse_consumption",
        target_type=SupportTargetType.ENEMY,
        category=SupportEffectCategory.DEBUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="minor_breach",
    ),
    GearSetKnownEffect(
        bonus_id=None,
        set_id=None,
        set_name="Roar of Alkosh",
        piece_count=5,
        name="roar_of_alkosh",
        layer=EffectLayer.PROC,
        magnitude=6000.0,
        duration=10.0,
        scaling="Weapon Damage, up to 6000 resistance reduction",
        trigger="synergy_activation",
        target_type=SupportTargetType.ENEMY,
        category=SupportEffectCategory.DEBUFF,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="roar_of_alkosh",
    ),
)


def known_effect_for_bonus(bonus_id: int) -> GearSetKnownEffect | None:
    """Legacy exact-bonus-id lookup retained for existing callers/tests."""
    return _KNOWN_EFFECTS.get(bonus_id)


def known_effect_for_bonus_row(
    bonus_id: int,
    set_id: int,
    set_name: str,
    piece_count: int,
) -> GearSetKnownEffect | None:
    """Resolve a verified mapping without guessing from tooltip prose."""
    exact = _KNOWN_EFFECTS.get(bonus_id)
    if exact is not None:
        if exact.set_id == set_id and exact.piece_count == piece_count:
            return exact
        return None

    normalized_name = set_name.strip().casefold()
    for known in _KNOWN_EFFECTS_BY_SET:
        if (
            known.set_name is not None
            and known.set_name.strip().casefold() == normalized_name
            and known.piece_count == piece_count
        ):
            return known

    return None
