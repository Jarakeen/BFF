from __future__ import annotations

from collections.abc import Iterable

from ..build_support_effect_service import BuildSupportEffectService
from ..role import Role
from ..support_effect_registry import SupportEffectRegistry
from .bar import Bar
from .character_build import CharacterBuild
from .effect_layer import BarId
from .effect_relationship import EffectRelationship
from .passive_grant import PassiveGrant
from .support_effect_resolver import CharacterBuildSupportEffectResolver


class CharacterCapabilityResolver:
    """
    Public entry point for resolving everything a CharacterBuild can provide.

    This is intentionally a thin orchestration layer. It does not create a
    second capability model and does not reinterpret effects.

    CharacterBuildSupportEffectResolver remains responsible for resolving
    the actual sources:
        - cast/slotted/passive/proc/ultimate effects
        - gear-set effects
        - weapon-enchantment effects

    The returned SupportEffectRegistry preserves the existing distinctions
    between SELF, ALLY, GROUP, and ENEMY effects.
    """

    def __init__(
        self,
        *,
        weapon_enchantment_support_service: BuildSupportEffectService | None = None,
        gear_set_effect_variant_resolver=None,
    ) -> None:
        self._resolver = CharacterBuildSupportEffectResolver(
            weapon_enchantment_support_service=weapon_enchantment_support_service,
            gear_set_effect_variant_resolver=gear_set_effect_variant_resolver,
        )

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
        Resolve the complete capability set available to `build` while
        `active_bar` is active.

        No capability is merged, evaluated, or scored here. The registry
        contains the effects the build can provide, with their original
        source, target, trigger, duration, range, scaling, and other
        mechanical metadata intact.
        """
        return self._resolver.resolve(
            build,
            active_bar,
            passives=passives,
            relationships=relationships,
            ultimate_trigger=ultimate_trigger,
            role_relevance=role_relevance,
        )