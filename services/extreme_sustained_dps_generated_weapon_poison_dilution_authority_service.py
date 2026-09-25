from __future__ import annotations

"""Compose generated poison formula provenance with explicit tier and dilution proof."""

from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionSelectionService,
)
from services.extreme_sustained_dps_weapon_poison_formula_selection_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaSelectionService,
)


class ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService:
    """Resolve exact generated poison durations without conflating authority layers."""

    def __init__(
        self,
        *,
        formula_authority: object,
        item_evidence_resolver: object,
        dilution_mode_resolver: object,
    ) -> None:
        if formula_authority is None:
            raise ValueError("generated poison dilution authority requires formula authority")
        if item_evidence_resolver is None:
            raise ValueError("generated poison dilution authority requires poison tier/item evidence")
        if dilution_mode_resolver is None:
            raise ValueError("generated poison dilution authority requires dilution-mode evidence")
        self.formula_authority = formula_authority
        self.item_evidence_resolver = item_evidence_resolver
        self.dilution_mode_resolver = dilution_mode_resolver

    @staticmethod
    def _invoke(
        resolver: object,
        *,
        poison_id: str,
        formula: object,
        occurrence: object,
        label: str,
    ):
        method = getattr(resolver, "resolve", None)
        if callable(method):
            return method(
                poison_id=poison_id,
                formula=formula,
                occurrence=occurrence,
            )
        if callable(resolver):
            return resolver(
                poison_id=poison_id,
                formula=formula,
                occurrence=occurrence,
            )
        raise TypeError(
            f"generated poison {label} resolver must be callable or expose callable resolve()"
        )

    def resolve(self, *, poison_id: str, occurrence: object):
        selected = str(poison_id or "").strip()
        if not selected:
            raise ValueError("generated poison dilution authority requires poison identity")

        formula_for = getattr(self.formula_authority, "formula_for", None)
        if formula_for is None:
            raise TypeError(
                "generated poison formula authority must expose formula_for(poison_id)"
            )
        formula = formula_for(selected)
        if formula is None:
            raise ValueError(
                f"{selected}: generated poison formula authority has no unique formula witness"
            )

        item_evidence = self._invoke(
            self.item_evidence_resolver,
            poison_id=selected,
            formula=formula,
            occurrence=occurrence,
            label="tier/item-evidence",
        )
        if item_evidence is None:
            raise ValueError(
                f"{selected}: generated poison tier/item evidence resolver returned no witness"
            )

        formula_selection = (
            ExtremeSustainedDPSWeaponPoisonFormulaSelectionService.resolve(
                item_evidence=item_evidence,
                formula=formula,
            )
        )
        mode_witness = self._invoke(
            self.dilution_mode_resolver,
            poison_id=selected,
            formula=formula,
            occurrence=occurrence,
            label="dilution-mode",
        )
        if mode_witness is None:
            raise ValueError(
                f"{selected}: generated poison dilution-mode resolver returned no witness"
            )

        effect_modes = getattr(mode_witness, "effect_modes", None)
        if effect_modes is None and isinstance(mode_witness, (tuple, list)):
            rows = tuple(mode_witness)
            if rows and all(
                isinstance(row, (tuple, list)) and len(row) == 2
                for row in rows
            ):
                effect_modes = rows

        if effect_modes is not None:
            return (
                ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve_per_effect(
                    formula_selection=formula_selection,
                    effect_modes=tuple(effect_modes),
                    poison_id_override=selected,
                )
            )

        return ExtremeSustainedDPSWeaponPoisonDilutionSelectionService.resolve(
            formula_selection=formula_selection,
            mode=mode_witness,
            poison_id_override=selected,
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedWeaponPoisonDilutionAuthorityService",
]
