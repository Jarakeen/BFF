from __future__ import annotations

from collections.abc import Iterable

from .character_build import CharacterBuild
from .effect_layer import BarId, EffectLayer
from .effect_instance import EffectVariant
from .passive_grant import PassiveGrant


def resolve_available_effects(
    build: CharacterBuild,
    active_bar: BarId,
    passives: Iterable[PassiveGrant] = (),
) -> tuple[EffectVariant, ...]:
    """
    Determine exactly what effects are actually available to `build` while
    `active_bar` is the currently active bar.

    This is the answer to the goal stated for the whole model: given a
    build and a moment (which bar is active), produce the concrete set of
    EffectVariant instances in play - cast effects only from the active
    bar's cast skills, slotted effects gated by whether they require bar
    representation, gear/CP effects gated by their own bar requirement,
    and passives gated by skill-line representation.

    This does NOT resolve trigger-dependent ultimate results (see
    `resolve_ultimate_cast_effects`) and does NOT apply effect
    relationships (see `effect_relationship.apply_relationships`) -
    callers compose those on top of this base set.
    """
    resolved: list[EffectVariant] = []

    for bar in build.bars():
        is_active_bar = bar.bar_id == active_bar

        for slot in bar.slots:
            for effect in slot.effects:
                if effect.layer == EffectLayer.CAST:
                    if is_active_bar and slot.is_cast and effect.is_available_on(
                        active_bar
                    ):
                        resolved.append(effect)

                elif effect.layer == EffectLayer.SLOTTED:
                    bar_ok = is_active_bar if slot.requires_active_bar else True
                    if bar_ok and effect.is_available_on(active_bar):
                        resolved.append(effect)

                elif effect.layer == EffectLayer.ULTIMATE:
                    # Ultimate-layer effects are only ever produced by an
                    # actual cast, resolved separately in
                    # resolve_ultimate_cast_effects - never picked up here,
                    # even if the same ultimate is slotted on both bars.
                    continue

                else:
                    # PASSIVE/PROC attached directly to a skill.
                    if effect.is_available_on(active_bar):
                        resolved.append(effect)

        if is_active_bar:
            for weapon in (bar.main_hand, bar.off_hand):
                if weapon is None:
                    continue
                for effect in weapon.effects:
                    if effect.is_available_on(active_bar):
                        resolved.append(effect)

    for piece in build.all_armor_pieces():
        for effect in piece.effects:
            if effect.is_available_on(active_bar):
                resolved.append(effect)

    for allocation in build.champion_points:
        for effect in allocation.effects:
            if effect.is_available_on(active_bar):
                resolved.append(effect)

    for grant in passives:
        if _skill_line_represented(build, grant, active_bar):
            if grant.effect.is_available_on(active_bar):
                resolved.append(grant.effect)

    return tuple(resolved)


def resolve_ultimate_cast_effects(
    build: CharacterBuild,
    cast_from_bar: BarId,
    trigger: str | None = None,
) -> tuple[EffectVariant, ...]:
    """
    Determine the effects produced by casting `build`'s ultimate from a
    specific bar, optionally under a named trigger condition.

    An ultimate's result depends on which bar it is cast from and what
    gear context is active on that bar - this never treats "ultimate" as
    a single static effect. Each candidate EffectVariant on the ultimate
    slot is included only if its own `active_bar`/`trigger` requirements
    match the cast context supplied here.
    """
    bar = next(
        (candidate for candidate in build.bars() if candidate.bar_id == cast_from_bar),
        None,
    )
    if bar is None:
        return ()

    ultimate_slot = bar.ultimate
    if ultimate_slot is None:
        return ()

    resolved: list[EffectVariant] = []
    for effect in ultimate_slot.effects:
        if not effect.is_available_on(cast_from_bar):
            continue
        if effect.trigger is not None and effect.trigger != trigger:
            continue
        resolved.append(effect)

    return tuple(resolved)


def _skill_line_represented(
    build: CharacterBuild,
    grant: PassiveGrant,
    active_bar: BarId,
) -> bool:
    for bar in build.bars():
        for slot in bar.slots:
            if slot.skill_line_id != grant.skill_line_id:
                continue

            if grant.requires_active_bar_representation:
                if bar.bar_id == active_bar:
                    return True
            else:
                return True

    return False
