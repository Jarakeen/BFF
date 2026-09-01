from __future__ import annotations

from collections.abc import Iterable

from ..build_support_effect_service import BuildSupportEffectService
from ..role import Role
from ..support_effect_registry import SupportEffectRegistry
from .character_build import CharacterBuild
from .effect_instance import EffectVariant
from .effect_layer import BarId
from .effect_relationship import ConditionContext, EffectRelationship
from .passive_grant import PassiveGrant
from .support_effect_resolver import CharacterBuildSupportEffectResolver


class CharacterCapabilityResolver:
    """Public entry point for resolving everything a CharacterBuild can provide."""

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
        consumable_effects: Iterable[EffectVariant] = (),
        ultimate_trigger: str | None = None,
        role_relevance: frozenset[Role] = frozenset(),
        condition_context: ConditionContext | None = None,
    ) -> SupportEffectRegistry:
        """Resolve the complete capability set available to ``build``.

        Consumables are availability evidence only. Their original SELF target,
        ``potion_use`` trigger, and activation condition are preserved by the
        shared EffectVariant -> SupportEffect conversion; they are not promoted
        to standing or group support.
        """
        return self._resolver.resolve(
            build,
            active_bar,
            passives=passives,
            relationships=relationships,
            consumable_effects=consumable_effects,
            ultimate_trigger=ultimate_trigger,
            role_relevance=role_relevance,
            condition_context=condition_context,
        )
