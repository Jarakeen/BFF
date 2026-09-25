from __future__ import annotations

"""Resolve only dilution facts that are literally preserved on an Alchemy formula."""

from dataclasses import dataclass

from minmax.alchemy_formula_catalog import AlchemyFormula
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: object) -> str:
    return _clean(value).casefold()


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitness:
    poison_id: str
    formula_id: str
    effect_modes: tuple[
        tuple[str, ExtremeSustainedDPSWeaponPoisonDilutionMode],
        ...,
    ]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.effect_modes) and not self.unresolved


class ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService:
    """Promote literal per-trait triple annotations, never inferred base duration."""

    @classmethod
    def resolve(
        cls,
        *,
        poison_id: str,
        formula: AlchemyFormula,
        occurrence: object | None = None,
    ) -> ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitness:
        del occurrence

        selected_poison_id = _clean(poison_id)
        formula_id = _clean(getattr(formula, "canonical_id", ""))
        traits = tuple(
            _clean(value)
            for value in tuple(getattr(formula, "traits", ()) or ())
            if _clean(value)
        )
        triple = {
            _norm(value)
            for value in tuple(getattr(formula, "source_triple_traits", ()) or ())
            if _clean(value)
        }
        unmarked = {
            _norm(value)
            for value in tuple(getattr(formula, "source_unmarked_traits", ()) or ())
            if _clean(value)
        }

        unresolved: list[str] = []
        if not selected_poison_id:
            unresolved.append("formula dilution witness requires poison identity")
        if not formula_id:
            unresolved.append("formula dilution witness requires canonical formula identity")
        elif selected_poison_id and selected_poison_id != formula_id:
            unresolved.append(
                f"{selected_poison_id}: formula dilution witness identity does not match "
                f"formula canonical ID {formula_id}"
            )
        if not traits:
            unresolved.append("formula dilution witness has no canonical traits")

        conflicts = sorted(triple.intersection(unmarked))
        if conflicts:
            unresolved.append(
                "formula dilution provenance conflicts between literal triple and "
                "unmarked source cells: " + ", ".join(conflicts)
            )

        effect_modes: list[
            tuple[str, ExtremeSustainedDPSWeaponPoisonDilutionMode]
        ] = []
        unsupported: list[str] = []
        explicitly_unmarked: list[str] = []
        for trait in traits:
            key = _norm(trait)
            if key in triple and key not in unmarked:
                effect_modes.append(
                    (trait, ExtremeSustainedDPSWeaponPoisonDilutionMode.TRIPLE)
                )
                continue
            if key in unmarked:
                explicitly_unmarked.append(trait)
            else:
                unsupported.append(trait)

        if explicitly_unmarked:
            unresolved.append(
                "unmarked formula source cells do not prove base dilution: "
                + ", ".join(explicitly_unmarked)
            )
        if unsupported:
            unresolved.append(
                "formula traits have no literal dilution annotation: "
                + ", ".join(unsupported)
            )

        return ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitness(
            poison_id=selected_poison_id,
            formula_id=formula_id,
            effect_modes=tuple(effect_modes),
            evidence=(
                f"Formula literal triple annotations: {tuple(getattr(formula, 'source_triple_traits', ()) or ())}",
                f"Formula explicit unmarked cells retained as provenance only: {tuple(getattr(formula, 'source_unmarked_traits', ()) or ())}",
                f"Formula source sections retained as provenance only: {tuple(getattr(formula, 'source_sections', ()) or ())}",
                "Only literal per-trait '(triple)' annotations are promoted to dilution mechanics.",
                "Unmarked cells, implicit primary-page effects, section headings, and effect count never prove base duration.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitness",
    "ExtremeSustainedDPSWeaponPoisonFormulaDilutionWitnessService",
]
