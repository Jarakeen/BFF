from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ..build import Build as LegacyBuild
from ..build_support_effect_service import BuildSupportEffectService
from ..gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from ..role import Role
from ..support_effect import SupportEffect
from ..support_effect_category import SupportEffectCategory
from ..support_effect_registry import SupportEffectRegistry
from ..support_effect_trigger import SupportEffectTrigger
from ..support_stacking import StackingBehavior
from ..support_target_type import SupportTargetType
from .bar import Bar
from .character_build import CharacterBuild, IllegalBuildError
from .effect_availability import (
    resolve_available_effects,
    resolve_ultimate_cast_effects,
)
from .effect_instance import EffectVariant
from .effect_layer import BarId
from .effect_relationship import (
    ConditionContext,
    EffectRelationship,
    apply_relationships,
)
from .passive_grant import PassiveGrant
from .weapon_type import WeaponType


_TWO_PIECE_WEAPON_TYPES = frozenset(
    {
        WeaponType.GREATSWORD,
        WeaponType.BATTLEAXE,
        WeaponType.MAUL,
        WeaponType.BOW,
        WeaponType.RESTORATION_STAFF,
        WeaponType.FROST_STAFF,
        WeaponType.FLAME_STAFF,
        WeaponType.LIGHTNING_STAFF,
    }
)


def effect_variant_to_support_effect(
    effect: EffectVariant,
    *,
    role_relevance: frozenset[Role] = frozenset(),
) -> SupportEffect:
    """
    Convert one resolved EffectVariant into a SupportEffect, preserving
    every field SupportEffect can represent instead of collapsing it.

    An EffectVariant with no `target_type` set is treated as SELF, never
    guessed to be group support.
    """
    trigger: SupportEffectTrigger | None = None

    if effect.trigger is not None:
        trigger = SupportEffectTrigger(
            trigger=effect.trigger,
            chance=effect.chance if effect.chance is not None else 1.0,
            condition=effect.condition,
            resulting_effect=effect.name,
        )

    conditions: tuple[str, ...] = ()

    if effect.condition is not None and trigger is None:
        # Only surface `condition` via SupportEffect.conditions when it
        # isn't already carried by a SupportEffectTrigger, to avoid
        # representing the same piece of data twice.
        conditions = (effect.condition,)

    return SupportEffect(
        source=effect.source,
        name=effect.name,
        category=effect.category or SupportEffectCategory.OTHER,
        effect_type=effect.name,
        target_type=effect.target_type or SupportTargetType.SELF,
        magnitude=effect.magnitude or 0.0,
        target_count=effect.target_count,
        duration=effect.duration,
        range=effect.range,
        scaling=effect.scaling,
        stacking=effect.stacking or StackingBehavior.UNIQUE,
        exclusivity_group=effect.exclusivity_group,
        conditions=conditions,
        trigger=trigger,
        role_relevance=role_relevance,
    )


def _weapon_set_piece_count(weapon_type: WeaponType) -> int:
    """Return the ESO set-piece contribution of one equipped weapon."""
    return 2 if weapon_type in _TWO_PIECE_WEAPON_TYPES else 1


def equipped_gear_set_counts(
    build: CharacterBuild,
    active_bar: BarId | None = None,
) -> dict[str, int]:
    """
    Count equipped set pieces by stable set identity.

    When `active_bar` is supplied, weapon pieces follow ESO's actual bar
    rules: only the active bar contributes, and bows/two-handed weapons/
    staves count as two set pieces. The no-bar form preserves the legacy
    aggregate behavior for callers that are not performing active-bar
    capability resolution.
    """
    counts: Counter[str] = Counter()

    for piece in build.all_armor_pieces():
        if piece.set_id is not None:
            counts[piece.set_id] += 1

    if active_bar is None:
        for bar in build.bars():
            for weapon in (bar.main_hand, bar.off_hand):
                if weapon is not None and weapon.set_id is not None:
                    counts[weapon.set_id] += 1
        return dict(counts)

    bar = build.front_bar if active_bar == BarId.FRONT else build.back_bar
    if bar is None:
        return dict(counts)

    for weapon in (bar.main_hand, bar.off_hand):
        if weapon is not None and weapon.set_id is not None:
            counts[weapon.set_id] += _weapon_set_piece_count(weapon.weapon_type)

    return dict(counts)


def resolve_effect_variants(
    build: CharacterBuild,
    active_bar: BarId,
    *,
    passives: Iterable[PassiveGrant] = (),
    relationships: Iterable[EffectRelationship] = (),
    condition_context: ConditionContext | None = None,
    ultimate_trigger: str | None = None,
) -> tuple[EffectVariant, ...]:
    """
    Resolve every EffectVariant `build` actually provides while
    `active_bar` is active.

    This includes cast/slotted/passive/proc effects, the active bar's
    ultimate result, and generic relationship modifications/triggers.

    `condition_context` is threaded into relationship resolution so
    conditional effects and REQUIRES relationships can be evaluated
    before the resulting effects cross into capability resolution.

    Raises IllegalBuildError if `build` fails its own hard-constraint
    validation.
    """
    violations = build.validate()

    if violations:
        raise IllegalBuildError(violations)

    base_effects = resolve_available_effects(
        build,
        active_bar,
        passives,
    )

    ultimate_effects = resolve_ultimate_cast_effects(
        build,
        active_bar,
        trigger=ultimate_trigger,
    )

    return apply_relationships(
        base_effects + ultimate_effects,
        relationships,
        context=condition_context,
    )


def _legacy_build_for_bar_weapons(bar: Bar | None) -> LegacyBuild:
    """
    Build a throwaway legacy `minmax.build.Build` containing only the
    given bar's enchanted weapons, so the existing DB-backed
    BuildSupportEffectService pipeline can be reused as-is for weapon
    enchantments, without modifying that legacy path at all.
    """
    legacy_build = LegacyBuild(name="character-build-bar-bridge")

    if bar is None:
        return legacy_build

    for weapon in (bar.main_hand, bar.off_hand):
        if weapon is None or weapon.enchantment_item_id is None:
            continue

        legacy_build.add_weapon(
            enchantment_item_id=weapon.enchantment_item_id,
            trait=weapon.trait,
            quality=weapon.quality,
        )

    return legacy_build


class CharacterBuildSupportEffectResolver:
    """
    Resolves a legal CharacterBuild into the full SupportEffectRegistry of
    effects it can actually provide at a given moment.

    Character-build-native effects are resolved by effect_availability.py.
    DB-backed weapon enchantments reuse the existing
    BuildSupportEffectService. Known gear-set effects are resolved from
    equipped set-piece counts through GearSetEffectVariantResolver.

    This class is a bridge, not a new source of truth.
    """

    def __init__(
        self,
        weapon_enchantment_support_service: BuildSupportEffectService | None = None,
        gear_set_effect_variant_resolver: GearSetEffectVariantResolver | None = None,
    ) -> None:
        self.weapon_enchantment_support_service = (
            weapon_enchantment_support_service
        )
        self.gear_set_effect_variant_resolver = (
            gear_set_effect_variant_resolver
        )

    def resolve(
        self,
        build: CharacterBuild,
        active_bar: BarId,
        *,
        passives: Iterable[PassiveGrant] = (),
        relationships: Iterable[EffectRelationship] = (),
        condition_context: ConditionContext | None = None,
        ultimate_trigger: str | None = None,
        role_relevance: frozenset[Role] = frozenset(),
    ) -> SupportEffectRegistry:
        """
        Resolve `build` into a SupportEffectRegistry containing every
        effect it provides while `active_bar` is active.

        Multiple providers of the same named effect are preserved as
        separate SupportEffect entries. This resolver never merges or
        sums them.

        `condition_context` is optional and additive. When omitted,
        relationship resolution preserves the existing unconditional
        behavior.
        """
        effect_variants = list(
            resolve_effect_variants(
                build,
                active_bar,
                passives=passives,
                relationships=relationships,
                condition_context=condition_context,
                ultimate_trigger=ultimate_trigger,
            )
        )

        # Ineligible EffectVariants remain preserved during relationship
        # resolution as evidence, but must not become capabilities.
        effect_variants = [
            effect
            for effect in effect_variants
            if effect.eligible
        ]

        # Resolve known gear-set effects from the actual equipped set
        # counts. These are derived effects and are deliberately not
        # written back onto ArmorPiece.effects.
        if self.gear_set_effect_variant_resolver is not None:
            for set_id, piece_count in equipped_gear_set_counts(
                build,
                active_bar=active_bar,
            ).items():
                try:
                    numeric_set_id = int(set_id)
                except (TypeError, ValueError):
                    continue

                effect_variants.extend(
                    self.gear_set_effect_variant_resolver.resolve(
                        numeric_set_id,
                        piece_count,
                    )
                )

        registry = SupportEffectRegistry()

        for effect in effect_variants:
            registry.add(
                effect_variant_to_support_effect(
                    effect,
                    role_relevance=role_relevance,
                )
            )

        if self.weapon_enchantment_support_service is not None:
            active_bar_obj = (
                build.front_bar
                if active_bar == BarId.FRONT
                else build.back_bar
            )

            legacy_build = _legacy_build_for_bar_weapons(active_bar_obj)

            enchantment_registry = (
                self.weapon_enchantment_support_service.resolve(
                    legacy_build
                )
            )

            for support_effect in enchantment_registry.all():
                registry.add(support_effect)

        return registry