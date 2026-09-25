from __future__ import annotations

"""Canonical production wiring for Objective #32 candidate runtime-state authority."""

from pathlib import Path

from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import WeaponEnchantmentEffectService
from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository
from services.extreme_sustained_dps_candidate_runtime_state_frontier_resolver_service import (
    ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService,
)
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingService,
)
from services.extreme_sustained_dps_runtime_effect_universe_service import (
    ExtremeSustainedDPSRuntimeEffectUniverseService,
)
from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationEventService,
)
from services.extreme_sustained_dps_weapon_enchantment_cadence_family_service import (
    ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService,
)
from services.extreme_sustained_dps_weapon_enchantment_cooldown_policy_resolver import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_variant_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService,
)
from services.extreme_sustained_dps_weapon_poison_activation_event_service import (
    ExtremeSustainedDPSWeaponPoisonActivationEventService,
)
from services.extreme_sustained_dps_weapon_poison_consequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_authority_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService,
)


class ExtremeSustainedDPSCandidateRuntimeStateFactoryService:
    """Build the canonical Objective #32 candidate runtime-state service graph.

    Exact pre-runtime damage-occurrence evidence stays caller-owned on purpose:
    deriving activation opportunities from the final damage evaluator would be
    circular because final damage evaluation itself consumes runtime_state.

    Exact crafted-poison formula/dilution consequence authority is also caller-owned.
    Callers may provide either a complete consequence-frontier resolver or explicit
    per-poison dilution-selection authority; the latter is wrapped through the
    canonical named-effect consequence path. The factory never infers a poison's
    effect set from its saved item label.
    """

    @staticmethod
    def build(
        *,
        database_path: str | Path,
        capability_service: object,
        occurrence_provider_resolver,
        supplemental_event_resolver=None,
        supplemental_event_denominator_proven: bool,
        supplemental_history_resolver=None,
        supplemental_history_denominator_proven: bool,
        weapon_poison_consequence_resolver: object | None = None,
        weapon_poison_dilution_selection_resolver: object | None = None,
        source: str = "Objective #32 candidate runtime scenario",
    ) -> ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService:
        if capability_service is None:
            raise ValueError(
                "candidate runtime-state factory requires canonical saved-build capability service"
            )
        if occurrence_provider_resolver is None:
            raise ValueError(
                "candidate runtime-state factory requires pre-runtime exact damage-occurrence authority"
            )
        if (
            weapon_poison_consequence_resolver is not None
            and weapon_poison_dilution_selection_resolver is not None
        ):
            raise ValueError(
                "candidate runtime-state factory cannot combine explicit weapon-poison "
                "consequence resolver with dilution-selection authority"
            )

        if (
            weapon_poison_consequence_resolver is None
            and weapon_poison_dilution_selection_resolver is not None
        ):
            weapon_poison_consequence_resolver = (
                ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
                    consequence_resolver=(
                        ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService(
                            dilution_selection_resolver=(
                                weapon_poison_dilution_selection_resolver
                            )
                        )
                    )
                )
            )

        database_path = Path(database_path)
        enchantment_repository = WeaponEnchantmentRepository(database_path)
        rule_repository = RuleRepository(database_path)
        enchantment_effect_service = WeaponEnchantmentEffectService(
            enchantment_repository,
            rule_repository,
        )
        enchantment_source_service = (
            ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService(
                repository=enchantment_repository,
                effect_service=enchantment_effect_service,
            )
        )
        enchantment_variant_service = (
            ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService()
        )
        runtime_effect_universe = ExtremeSustainedDPSRuntimeEffectUniverseService(
            capability_service=capability_service,
            weapon_enchantment_runtime_source_service=enchantment_source_service,
            weapon_enchantment_runtime_variant_service=enchantment_variant_service,
        )
        cadence_family_service = (
            ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService()
        )
        cooldown_policy_resolver = (
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicyResolver(
                runtime_source_service=enchantment_source_service,
                cadence_family_service=cadence_family_service,
                cooldown_rule_resolver=enchantment_effect_service,
            )
        )
        scenario_frontier = ExtremeSustainedDPSRuntimeScenarioFrontierService(
            runtime_effect_universe=runtime_effect_universe,
            runtime_effect_scaling=(
                ExtremeSustainedDPSRuntimeEffectScalingService.from_database(
                    database_path
                )
            ),
            weapon_enchantment_activation_service=(
                ExtremeSustainedDPSWeaponEnchantmentActivationEventService.from_database(
                    database_path
                )
            ),
            weapon_enchantment_cooldown_policy_resolver=cooldown_policy_resolver,
            weapon_poison_activation_service=(
                ExtremeSustainedDPSWeaponPoisonActivationEventService.from_database(
                    database_path
                )
            ),
            weapon_poison_consequence_resolver=weapon_poison_consequence_resolver,
        )
        return ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
            scenario_frontier=scenario_frontier,
            occurrence_provider_resolver=occurrence_provider_resolver,
            supplemental_event_resolver=supplemental_event_resolver,
            supplemental_event_denominator_proven=bool(
                supplemental_event_denominator_proven
            ),
            supplemental_history_resolver=supplemental_history_resolver,
            supplemental_history_denominator_proven=bool(
                supplemental_history_denominator_proven
            ),
            source=source,
        )


__all__ = ["ExtremeSustainedDPSCandidateRuntimeStateFactoryService"]
