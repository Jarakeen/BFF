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
from .effect_layer import BarId, EffectLayer
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
        cooldown=effect.cooldown,
        range=effect.range,
        scaling=effect.scaling,
        stacking=effect.stacking or StackingBehavior.UNIQUE,
        exclusivity_group=effect.exclusivity_group,
        conditions=conditions,
        trigger=trigger,
        role_relevance=role_relevance,
    )


def _weapon_set_piece_count(weapon_type: WeaponType) -> int:
    return 2 if weapon_type in _TWO_PIECE_WEAPON_TYPES else 1


def equipped_gear_set_counts(
    build: CharacterBuild,
    active_bar: BarId | None = None,
) -> dict[str, int]:
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
    """Resolve a legal CharacterBuild into its available SupportEffects."""

    def __init__(
        self,
        weapon_enchantment_support_service: BuildSupportEffectService | None = None,
        gear_set_effect_variant_resolver: GearSetEffectVariantResolver | None = None,
    ) -> None:
        self.weapon_enchantment_support_service = weapon_enchantment_support_service
        self.gear_set_effect_variant_resolver = gear_set_effect_variant_resolver

    @staticmethod
    def _safe_consumables(effects: Iterable[EffectVariant]) -> tuple[EffectVariant, ...]:
        """Admit only self-target consumable availability into capability data.

        This is deliberately strict. A selected potion is something the player
        can use; it is not evidence of standing uptime and must never become a
        GROUP/ALLY/ENEMY support provider merely because a malformed variant was
        supplied by a caller.
        """
        return tuple(
            effect
            for effect in effects
            if effect.eligible
            and effect.layer is EffectLayer.CONSUMABLE
            and effect.target_type is SupportTargetType.SELF
            and str(effect.trigger or "").strip().casefold() == "potion_use"
        )

    def resolve(
        self,
        build: CharacterBuild,
        active_bar: BarId,
        *,
        passives: Iterable[PassiveGrant] = (),
        relationships: Iterable[EffectRelationship] = (),
        consumable_effects: Iterable[EffectVariant] = (),
        condition_context: ConditionContext | None = None,
        ultimate_trigger: str | None = None,
        role_relevance: frozenset[Role] = frozenset(),
    ) -> SupportEffectRegistry:
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

        effect_variants = [effect for effect in effect_variants if effect.eligible]

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

        # Consumable availability joins the same EffectVariant pipeline only at
        # this final capability boundary. The trigger/condition/SELF target are
        # preserved, so no standing stat or raid-support uptime is inferred.
        effect_variants.extend(self._safe_consumables(consumable_effects))

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
            enchantment_registry = self.weapon_enchantment_support_service.resolve(
                legacy_build
            )
            for support_effect in enchantment_registry.all():
                registry.add(support_effect)

        return registry
