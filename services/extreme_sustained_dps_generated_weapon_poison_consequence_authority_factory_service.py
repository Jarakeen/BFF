from __future__ import annotations

"""Build candidate-scoped generated weapon-poison consequence authority.

This service composes retained generated formula provenance with caller-owned crafted
item/tier evidence and dilution-mode proof, then wraps the result through the reviewed
named-effect and finite consequence-frontier services used by Objective #32 runtime.
"""

from services.extreme_sustained_dps_generated_weapon_poison_dilution_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService,
)
from services.extreme_sustained_dps_generated_weapon_poison_formula_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService,
)
from services.extreme_sustained_dps_weapon_poison_consequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_authority_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService,
)


class ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService:
    """Resolve one complete poison consequence-frontier authority for a generated state."""

    def __init__(
        self,
        *,
        item_evidence_resolver: object,
        dilution_mode_resolver: object,
    ) -> None:
        if item_evidence_resolver is None:
            raise ValueError(
                "generated poison consequence authority requires tier/item evidence resolver"
            )
        if dilution_mode_resolver is None:
            raise ValueError(
                "generated poison consequence authority requires dilution-mode resolver"
            )
        self.item_evidence_resolver = item_evidence_resolver
        self.dilution_mode_resolver = dilution_mode_resolver

    def resolve(self, state: object):
        formula_authority = (
            ExtremeSustainedDPSGeneratedWeaponPoisonFormulaAuthorityService.resolve(
                state
            )
        )
        if not formula_authority.resolved:
            detail = "; ".join(formula_authority.unresolved)
            raise ValueError(
                "generated poison formula authority is unresolved"
                + (f": {detail}" if detail else "")
            )

        if not formula_authority.entries:
            return None

        dilution_authority = (
            ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
                formula_authority=formula_authority,
                item_evidence_resolver=self.item_evidence_resolver,
                dilution_mode_resolver=self.dilution_mode_resolver,
            )
        )
        named_effect_authority = (
            ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService(
                dilution_selection_resolver=dilution_authority,
            )
        )
        return ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
            consequence_resolver=named_effect_authority,
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedWeaponPoisonConsequenceAuthorityFactoryService",
]
