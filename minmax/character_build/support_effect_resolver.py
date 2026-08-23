from __future__ import annotations

from collections.abc import Iterable

from ..build import Build as LegacyBuild
from ..build_support_effect_service import BuildSupportEffectService
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
from .effect_relationship import EffectRelationship, apply_relationships
from .passive_grant import PassiveGrant


def effect_variant_to_support_effect(
    effect: EffectVariant,
    *,
    role_relevance: frozenset[Role] = frozenset(),
) -> SupportEffect:
    """
    Convert one resolved EffectVariant into a SupportEffect, preserving
    every field SupportEffect can represent instead of collapsing it.

    An EffectVariant with no `target_type` set is treated as SELF, never
    guessed to be group support - see requirement 7 (support vs personal).
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
        stacking=effect.stacking or StackingBehavior.UNIQUE,
        exclusivity_group=effect.exclusivity_group,
        conditions=conditions,
        trigger=trigger,
        role_relevance=role_relevance,
    )


def resolve_effect_variants(
    build: CharacterBuild,
    active_bar: BarId,
    *,
    passives: Iterable[PassiveGrant] = (),
    relationships: Iterable[EffectRelationship] = (),
    ultimate_trigger: str | None = None,
) -> tuple[EffectVariant, ...]:
    """
    Resolve every EffectVariant `build` actually provides while
    `active_bar` is active - cast/slotted/passive/proc effects, the
    active bar's ultimate result, and any generic relationship
    modifications/triggers layered on top.

    Raises IllegalBuildError if `build` fails its own hard-constraint
    validation - effect resolution must respect the character's actual
    build constraints, not resolve effects for an impossible build.
    """
    violations = build.validate()
    if violations:
        raise IllegalBuildError(violations)

    base_effects = resolve_available_effects(build, active_bar, passives)
    ultimate_effects = resolve_ultimate_cast_effects(
        build, active_bar, trigger=ultimate_trigger
    )

    return apply_relationships(base_effects + ultimate_effects, relationships)


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
    effects it can actually provide at a given moment (a specific active
    bar).

    This is a bridge, not a new source of truth: character-build-native
    effects (cast/slotted/passive/proc/ultimate, already attached directly
    to skills/weapons/gear/CP as EffectVariants) are resolved by
    effect_availability.py; DB-backed weapon-enchantment effects are
    resolved by reusing the existing BuildSupportEffectService pipeline
    unchanged. Nothing here re-implements either.

    Currently bridged DB-backed sources
    ------------------------------------
    - Weapon enchantments, via an injected BuildSupportEffectService,
      scoped to the currently active bar's weapons only.

    Not yet bridged (architecture ready, no source data/service to
    connect to)
    ------------------------------------------------------------------
    - Gear sets: the existing GearSetEffectResolver only produces
      generic self-stat Effects with no target information (documented
      on BuildSupportEffectService itself), so a set's group-relevant
      bonus (e.g. Major Courage) cannot yet be told apart from an
      ordinary personal stat bonus via the database. CharacterBuild's own
      ArmorPiece.effects can still carry hand-authored EffectVariants for
      sets whose group effect is already known.
    - Armor glyphs, race, Champion Points, mythic items: no repository or
      service in this codebase resolves these into target-aware combat
      effects yet. CharacterBuild.champion_points / .mythic /.armor can
      still carry EffectVariants directly for anything already known.
    """

    def __init__(
        self,
        weapon_enchantment_support_service: BuildSupportEffectService | None = None,
    ) -> None:
        self.weapon_enchantment_support_service = weapon_enchantment_support_service

    def resolve(
        self,
        build: CharacterBuild,
        active_bar: BarId,
        *,
        passives: Iterable[PassiveGrant] = (),
        relationships: Iterable[EffectRelationship] = (),
        ultimate_trigger: str | None = None,
        role_relevance: frozenset[Role] = frozenset(),
    ) -> SupportEffectRegistry:
        """
        Resolve `build` into a SupportEffectRegistry containing every
        effect it provides while `active_bar` is active - SELF, ALLY,
        GROUP, and ENEMY effects alike. This resolver does not decide
        what "counts" as group support; use SupportCoverage/
        SupportEffectRegistry on the returned registry for that (e.g.
        `.contributing_to_group()`).

        Multiple providers of the same named effect (e.g. two sources of
        "major_force") are preserved as separate SupportEffect entries -
        this never merges them or sums their magnitudes.
        """
        effect_variants = resolve_effect_variants(
            build,
            active_bar,
            passives=passives,
            relationships=relationships,
            ultimate_trigger=ultimate_trigger,
        )

        registry = SupportEffectRegistry()
        for effect in effect_variants:
            registry.add(
                effect_variant_to_support_effect(
                    effect, role_relevance=role_relevance
                )
            )

        if self.weapon_enchantment_support_service is not None:
            active_bar_obj = (
                build.front_bar if active_bar == BarId.FRONT else build.back_bar
            )
            legacy_build = _legacy_build_for_bar_weapons(active_bar_obj)
            enchantment_registry = self.weapon_enchantment_support_service.resolve(
                legacy_build
            )
            for support_effect in enchantment_registry.all():
                registry.add(support_effect)

        return registry
