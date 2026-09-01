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
MAGMA_INCARNATE_SET_ID = 609
MAGMA_INCARNATE_TWO_PIECE_BONUS_ID = 1680
SPAULDER_OF_RUIN_SET_ID = 627
SPAULDER_OF_RUIN_ONE_PIECE_BONUS_ID = 1602
SERPENTS_DISDAIN_SET_ID = 641
SERPENTS_DISDAIN_FIVE_PIECE_BONUS_ID = 1700


_KNOWN_EFFECTS: dict[int, tuple[GearSetKnownEffect, ...]] = {
    MASTER_ARCHITECT_FIVE_PIECE_BONUS_ID: (
        GearSetKnownEffect(
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
    ),
    MAGMA_INCARNATE_TWO_PIECE_BONUS_ID: (
        GearSetKnownEffect(
            bonus_id=MAGMA_INCARNATE_TWO_PIECE_BONUS_ID,
            set_id=MAGMA_INCARNATE_SET_ID,
            piece_count=2,
            name="minor_courage",
            magnitude=215.0,
            duration=10.0,
            target_count=4,
            range=28.0,
            scaling="initial target plus up to 3 nearby group-member bounces within 8 meters",
            trigger="single_target_heal_self_or_group_member",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            stacking=StackingBehavior.UNIQUE,
            exclusivity_group="minor_courage",
        ),
        GearSetKnownEffect(
            bonus_id=MAGMA_INCARNATE_TWO_PIECE_BONUS_ID,
            set_id=MAGMA_INCARNATE_SET_ID,
            piece_count=2,
            name="minor_resolve",
            magnitude=2974.0,
            duration=10.0,
            target_count=4,
            range=28.0,
            scaling="initial target plus up to 3 nearby group-member bounces within 8 meters",
            trigger="single_target_heal_self_or_group_member",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            stacking=StackingBehavior.UNIQUE,
            exclusivity_group="minor_resolve",
        ),
    ),
    SPAULDER_OF_RUIN_ONE_PIECE_BONUS_ID: (
        GearSetKnownEffect(
            bonus_id=SPAULDER_OF_RUIN_ONE_PIECE_BONUS_ID,
            set_id=SPAULDER_OF_RUIN_SET_ID,
            piece_count=1,
            name="weapon_spell_damage",
            magnitude=260.0,
            target_count=6,
            range=12.0,
            condition="aura_of_pride_active",
            trigger="crouch_or_prowl_toggle",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            stacking=StackingBehavior.UNIQUE,
            exclusivity_group="spauld er_of_ruin_aura_of_pride".replace(" ", ""),
        ),
    ),
    SERPENTS_DISDAIN_FIVE_PIECE_BONUS_ID: (
        GearSetKnownEffect(
            bonus_id=SERPENTS_DISDAIN_FIVE_PIECE_BONUS_ID,
            set_id=SERPENTS_DISDAIN_SET_ID,
            piece_count=5,
            name="status_effect_duration_increase",
            layer=EffectLayer.PASSIVE,
            magnitude=16.0,
            scaling="adds 16 seconds to Status Effects applied by the wearer",
            target_type=SupportTargetType.SELF,
            category=SupportEffectCategory.OTHER,
            stacking=StackingBehavior.UNIQUE,
            exclusivity_group="serpents_disdain_status_duration",
        ),
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
    matches = _KNOWN_EFFECTS.get(bonus_id, ())
    return matches[0] if matches else None


def known_effects_for_bonus_row(
    bonus_id: int,
    set_id: int,
    set_name: str,
    piece_count: int,
) -> tuple[GearSetKnownEffect, ...]:
    """Resolve every verified effect for one bonus row without tooltip guessing."""
    exact = _KNOWN_EFFECTS.get(bonus_id, ())
    if exact:
        if all(
            effect.set_id == set_id and effect.piece_count == piece_count
            for effect in exact
        ):
            return exact
        return ()

    normalized_name = set_name.strip().casefold()
    return tuple(
        known
        for known in _KNOWN_EFFECTS_BY_SET
        if (
            known.set_name is not None
            and known.set_name.strip().casefold() == normalized_name
            and known.piece_count == piece_count
        )
    )


def known_effect_for_bonus_row(
    bonus_id: int,
    set_id: int,
    set_name: str,
    piece_count: int,
) -> GearSetKnownEffect | None:
    """Backward-compatible singular lookup for older callers."""
    matches = known_effects_for_bonus_row(
        bonus_id,
        set_id,
        set_name,
        piece_count,
    )
    return matches[0] if matches else None
