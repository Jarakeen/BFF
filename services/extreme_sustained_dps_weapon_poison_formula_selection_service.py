from __future__ import annotations

"""Validate explicit crafted-poison formula provenance against item-label evidence."""

from dataclasses import dataclass

from minmax.alchemy_formula_catalog import AlchemyFormula
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonFormulaSelection:
    poison_id: str
    formula_id: str
    selected_effects: tuple[ExtremeSustainedDPSWeaponPoisonPossibleEffect, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def exact_effect_set_proven(self) -> bool:
        return bool(self.selected_effects) and not self.unresolved


class ExtremeSustainedDPSWeaponPoisonFormulaSelectionService:
    """Prove one explicit formula's effect set without choosing dilution duration."""

    @staticmethod
    def _norm(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def resolve(
        cls,
        *,
        item_evidence: ExtremeSustainedDPSWeaponPoisonItemEvidence,
        formula: AlchemyFormula,
    ) -> ExtremeSustainedDPSWeaponPoisonFormulaSelection:
        unresolved: list[str] = []
        evidence: list[str] = list(tuple(item_evidence.evidence))

        if not item_evidence.source_evidence_complete:
            unresolved.extend(tuple(item_evidence.unresolved))
            unresolved.append(
                "weapon-poison formula selection requires complete item-label source evidence"
            )

        possible = {
            cls._norm(row.effect_name): row
            for row in tuple(item_evidence.possible_effects)
        }
        traits = tuple(
            str(value or "").strip()
            for value in tuple(formula.traits)
            if str(value or "").strip()
        )
        if not traits:
            unresolved.append("weapon-poison formula witness has no canonical traits")

        selected: list[ExtremeSustainedDPSWeaponPoisonPossibleEffect] = []
        missing: list[str] = []
        for trait in traits:
            row = possible.get(cls._norm(trait))
            if row is None:
                missing.append(trait)
                continue
            selected.append(row)

        if missing:
            unresolved.append(
                f"{item_evidence.poison_id}: explicit formula contains trait(s) not "
                f"supported by the item-label Poison tier evidence: {', '.join(missing)}"
            )

        if selected and len(selected) != len(traits):
            unresolved.append(
                f"{item_evidence.poison_id}: formula effect-set proof is incomplete"
            )

        formula_id = str(formula.canonical_id or "").strip()
        if not formula_id:
            unresolved.append("weapon-poison formula witness has no canonical identity")

        deduped = tuple(dict.fromkeys(row for row in unresolved if row))
        return ExtremeSustainedDPSWeaponPoisonFormulaSelection(
            poison_id=str(item_evidence.poison_id or "").strip(),
            formula_id=formula_id,
            selected_effects=tuple(selected),
            evidence=(
                *tuple(evidence),
                f"Explicit poison formula witness: {formula_id or '(missing)'}",
                f"Explicit poison formula traits: {traits}",
                f"Formula source sections: {tuple(getattr(formula, 'source_sections', ()) or ())}",
                f"Formula traits matched to item-label possibility evidence: {len(selected)}/{len(traits)}",
                "Formula source sections are retained as provenance only; they do not independently prove base-versus-triple dilution.",
                "Exact effect-set proof does not choose base-versus-triple duration; dilution remains separately owned.",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonFormulaSelection",
    "ExtremeSustainedDPSWeaponPoisonFormulaSelectionService",
]
