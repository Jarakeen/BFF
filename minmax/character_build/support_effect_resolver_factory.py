from __future__ import annotations

from pathlib import Path

from ..build_combat_effect_service import BuildCombatEffectService
from ..build_support_effect_service import BuildSupportEffectService
from ..gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from ..gear_set_repository import GearSetRepository
from ..rule_repository import RuleRepository
from ..weapon_enchantment_effect_service import WeaponEnchantmentEffectService
from ..weapon_enchantment_repository import WeaponEnchantmentRepository
from .support_effect_resolver import CharacterBuildSupportEffectResolver


def build_db_backed_support_effect_resolver(
    database_path: str | Path,
) -> CharacterBuildSupportEffectResolver:
    """Build the production CharacterBuild support resolver for one ESO DB.

    Keep DB-backed subsystem assembly in one place so callers cannot
    accidentally resolve gear sets while silently omitting weapon
    enchantments, or vice versa.
    """
    enchantment_repository = WeaponEnchantmentRepository(database_path)
    rule_repository = RuleRepository(database_path)
    enchantment_effect_service = WeaponEnchantmentEffectService(
        enchantment_repository=enchantment_repository,
        rule_repository=rule_repository,
    )
    combat_effect_service = BuildCombatEffectService(
        weapon_enchantment_service=enchantment_effect_service,
    )
    enchantment_support_service = BuildSupportEffectService(
        build_combat_effect_service=combat_effect_service,
    )

    gear_repository = GearSetRepository(database_path)
    gear_effect_resolver = GearSetEffectVariantResolver(gear_repository)

    return CharacterBuildSupportEffectResolver(
        weapon_enchantment_support_service=enchantment_support_service,
        gear_set_effect_variant_resolver=gear_effect_resolver,
    )
