from __future__ import annotations

"""Build candidate-scoped generated weapon-poison consequence authority.

This service composes retained generated formula provenance with the selected generated
tier loadout and caller-owned dilution-mode proof, then wraps the result through the
reviewed named-effect and finite consequence-frontier services used by Objective #32
runtime. An explicit item/tier resolver remains available for non-pipeline callers.
When no stronger dilution resolver is supplied, literal per-trait source annotations are
used through the fail-closed formula dilution witness service.
"""

from services.extreme_sustained_dps_generated_weapon_poison_dilution_authority_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService,
)
from services.extreme_sustained_dps_weapon_poison_formula_dilution_witness_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService,
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
        item_evidence_resolver: object | None = None,
        dilution_mode_resolver: object | None = None,
    ) -> None:
        self.item_evidence_resolver = item_evidence_resolver
        self.dilution_mode_resolver = (
            dilution_mode_resolver
            if dilution_mode_resolver is not None
            else ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService
        )

    @staticmethod
    def _retained_tier_evidence(
        state: object,
        *,
        poison_id: str,
        formula: object,
        occurrence: object,
    ):
        late = getattr(state, "late", None)
        assembled = getattr(late, "assembled", None)
        tier_loadout = (
            None
            if assembled is None
            else getattr(assembled, "poison_tier_loadout", None)
        )
        if tier_loadout is None:
            tier_loadout = getattr(late, "poison_tier_loadout", None)
        if tier_loadout is None:
            raise ValueError(
                "generated poison consequence authority requires retained poison tier loadout"
            )

        event = getattr(occurrence, "event", None)
        source_bar = str(getattr(event, "source_bar", "") or "").strip().casefold()
        if source_bar not in {"front", "back"}:
            raise ValueError(
                "generated poison tier evidence requires proc occurrence source bar"
            )
        bar_selection = getattr(tier_loadout, source_bar, None)
        if bar_selection is None:
            raise ValueError(
                f"generated poison tier loadout has no {source_bar} selection"
            )

        selected_id = str(
            getattr(bar_selection, "poison_id", "") or ""
        ).strip()
        requested_id = str(poison_id or "").strip()
        if selected_id != requested_id:
            raise ValueError(
                f"{source_bar} poison tier evidence belongs to "
                f"{selected_id or '(none)'} but proc selected {requested_id or '(none)'}"
            )

        tier = getattr(bar_selection, "tier", None)
        if tier is None:
            raise ValueError(
                f"{source_bar} poison proc selected {requested_id} without tier evidence"
            )
        item_evidence = getattr(tier, "item_evidence", None)
        if item_evidence is None:
            raise ValueError(
                f"{source_bar} generated poison tier has no item/effect evidence"
            )

        formula_id = str(getattr(formula, "canonical_id", "") or "").strip()
        if formula_id != requested_id:
            raise ValueError(
                f"{source_bar} generated poison formula identity does not match proc identity"
            )
        return item_evidence

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

        item_evidence_resolver = self.item_evidence_resolver
        if item_evidence_resolver is None:
            def item_evidence_resolver(*, poison_id, formula, occurrence):
                return self._retained_tier_evidence(
                    state,
                    poison_id=poison_id,
                    formula=formula,
                    occurrence=occurrence,
                )

        dilution_authority = (
            ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService(
                formula_authority=formula_authority,
                item_evidence_resolver=item_evidence_resolver,
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
