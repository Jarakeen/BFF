"""
minmax/gear_set_effect_variant_resolver.py

The generic GearSet -> EffectVariant bridge.

Current gear-set resolution path, before this module
---------------------------------------------------------
    GearSetRepository (DB access: gear_set / gear_set_bonus, unchanged)
        |
    GearSetEffectResolver (regex-based; simple, unconditional, single-
        clause stat text only - "Adds X Max Magicka" and similar. Its own
        docstring: "Triggered, conditional, proc, cooldown, scaling, and
        trade-off bonuses return an empty list rather than being guessed
        at.")
        |
    GearSetEffectService -> list[minmax.effects.Effect]   (legacy,
        flat-stat StatEngine model - NOT the character-build-native
        EffectVariant model)

That path deliberately never produces a group-support effect like Major
Slayer, because Major Slayer is exactly the kind of triggered/conditional/
scaling bonus GearSetEffectResolver declines to interpret, and because
`Effect` has no target/trigger/scaling concept at all - see
support_effect_resolver.py's own docstring:

    "Gear sets: the existing GearSetEffectResolver only produces generic
    self-stat Effects with no target information ... so a set's
    group-relevant bonus (e.g. Major Courage) cannot yet be told apart
    from an ordinary personal stat bonus via the database. CharacterBuild's
    own ArmorPiece.effects can still carry hand-authored EffectVariants
    for sets whose group effect is already known."

This module is that missing bridge, generalized: instead of every caller
hand-authoring an EffectVariant inline, GearSetEffectVariantResolver
looks up whichever of a set's active bonuses already has a registered,
canonical EffectVariant mapping (minmax/gear_set_known_effects.py) and
produces it. The resulting EffectVariant is attached to an ArmorPiece
exactly the way the docstring above already describes - nothing in
effect_availability.py or support_effect_resolver.py needs to change,
because both already read EffectVariants straight off ArmorPiece.effects.

This resolver does not parse bonus description text and does not invent
effect identities. It reuses GearSetRepository unchanged, reuses
EffectVariant unchanged, and contains no set-specific branching -
"Master Architect" and "major_slayer" never appear in this file. Adding
another gear set's known group bonus is a new row in
gear_set_known_effects.py, not a new resolver.
"""

from __future__ import annotations

from .character_build.effect_instance import EffectVariant
from .gear_set_known_effects import GearSetKnownEffect, known_effect_for_bonus
from .gear_set_repository import GearSetRepository


class GearSetEffectVariantResolver:
    """
    Resolve the EffectVariant(s) a gear set's active bonuses grant, for
    every bonus this codebase already has a canonical mapping for.

    This mirrors GearSetEffectService's shape (same
    resolve(set_id, equipped_piece_count) call, same "bonuses requiring
    more pieces than are equipped are ignored" rule) but targets
    EffectVariant instead of the legacy Effect model, and defers to a
    known-effect registry instead of a text-pattern resolver.
    """

    def __init__(self, repository: GearSetRepository) -> None:
        self.repository = repository

    def resolve(
        self,
        set_id: int,
        equipped_piece_count: int,
    ) -> list[EffectVariant]:
        """
        Resolve every EffectVariant `set_id` grants at
        `equipped_piece_count` pieces equipped, for bonuses this codebase
        has a known mapping for.

        Bonuses requiring more pieces than are equipped are ignored, same
        as GearSetEffectService. Bonuses with no known-effect mapping
        contribute nothing - this never guesses at a bonus's meaning, and
        never fabricates a new effect identity.
        """
        if equipped_piece_count <= 0:
            return []

        gear_set = self.repository.get_set_by_id(set_id)
        source_name = gear_set.name if gear_set is not None else f"Set {set_id}"

        bonuses = self.repository.get_bonuses(set_id)

        variants: list[EffectVariant] = []

        for bonus in bonuses:
            if bonus.piece_count > equipped_piece_count:
                continue

            known = known_effect_for_bonus(bonus.id)
            if known is None:
                continue

            # A known-effect entry must actually describe THIS bonus row,
            # not merely share a bonus_id coincidence - defends against a
            # registry entry ever drifting out of sync with the database
            # (e.g. an id being reused after data was rebuilt).
            if known.set_id != bonus.set_id or known.piece_count != bonus.piece_count:
                continue

            variants.append(
                self._to_effect_variant(known, source_name, bonus.piece_count)
            )

        return variants

    @staticmethod
    def _to_effect_variant(
        known: GearSetKnownEffect,
        source_name: str,
        piece_count: int,
    ) -> EffectVariant:
        """
        Build the EffectVariant this bonus grants. `name` always comes
        from the known-effect registry's already-canonical identity - this
        method has no path that can produce a new or different effect
        identity than the one already registered.
        """
        return EffectVariant(
            name=known.name,
            layer=known.layer,
            source=f"{source_name} ({piece_count})",
            magnitude=known.magnitude,
            duration=known.duration,
            target_count=known.target_count,
            range=known.range,
            scaling=known.scaling,
            condition=known.condition,
            trigger=known.trigger,
            target_type=known.target_type,
            category=known.category,
            stacking=known.stacking,
            exclusivity_group=known.exclusivity_group,
        )
