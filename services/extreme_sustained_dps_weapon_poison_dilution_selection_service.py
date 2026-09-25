from __future__ import annotations

"""Select exact poison effect durations from an explicit dilution witness."""

from dataclasses import dataclass
from enum import Enum

from services.extreme_sustained_dps_weapon_poison_formula_selection_service import (
    ExtremeSustainedDPSWeaponPoisonFormulaSelection,
)


class ExtremeSustainedDPSWeaponPoisonDilutionMode(str, Enum):
    BASE = "base"
    TRIPLE = "triple"


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonSelectedEffect:
    effect_name: str
    duration_seconds: float


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonDilutionSelection:
    poison_id: str
    formula_id: str
    mode: ExtremeSustainedDPSWeaponPoisonDilutionMode
    effects: tuple[ExtremeSustainedDPSWeaponPoisonSelectedEffect, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.effects) and not self.unresolved


class ExtremeSustainedDPSWeaponPoisonDilutionSelectionService:
    """Apply a caller-proven base/triple duration mode to a proven formula effect set."""

    @classmethod
    def resolve(
        cls,
        *,
        formula_selection: ExtremeSustainedDPSWeaponPoisonFormulaSelection,
        mode: ExtremeSustainedDPSWeaponPoisonDilutionMode | str,
        poison_id_override: str | None = None,
    ) -> ExtremeSustainedDPSWeaponPoisonDilutionSelection:
        try:
            selected_mode = (
                mode
                if isinstance(mode, ExtremeSustainedDPSWeaponPoisonDilutionMode)
                else ExtremeSustainedDPSWeaponPoisonDilutionMode(
                    str(mode or "").strip().casefold()
                )
            )
        except ValueError as exc:
            raise ValueError(f"unsupported weapon-poison dilution mode: {mode!r}") from exc

        unresolved: list[str] = list(tuple(formula_selection.unresolved))
        if not formula_selection.exact_effect_set_proven:
            unresolved.append(
                "weapon-poison dilution selection requires a proven formula effect set"
            )

        effects: list[ExtremeSustainedDPSWeaponPoisonSelectedEffect] = []
        for source in tuple(formula_selection.selected_effects):
            if selected_mode is ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE:
                duration = float(source.base_duration_seconds)
            else:
                if source.triple_duration_seconds is None:
                    unresolved.append(
                        f"{formula_selection.poison_id}: {source.effect_name} has no "
                        "source-preserved triple-effect duration"
                    )
                    continue
                duration = float(source.triple_duration_seconds)

            if duration < 0.0:
                unresolved.append(
                    f"{formula_selection.poison_id}: {source.effect_name} selected "
                    "duration cannot be negative"
                )
                continue
            effects.append(
                ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                    effect_name=source.effect_name,
                    duration_seconds=duration,
                )
            )

        deduped = tuple(dict.fromkeys(row for row in unresolved if row))
        selected_poison_id = (
            str(poison_id_override or "").strip()
            or str(formula_selection.poison_id or "").strip()
        )
        return ExtremeSustainedDPSWeaponPoisonDilutionSelection(
            poison_id=selected_poison_id,
            formula_id=str(formula_selection.formula_id or "").strip(),
            mode=selected_mode,
            effects=tuple(effects),
            evidence=(
                *tuple(formula_selection.evidence),
                f"Explicit weapon-poison dilution witness: {selected_mode.value}",
                (
                    f"Runtime poison identity override: {selected_poison_id}"
                    if poison_id_override
                    else "Runtime poison identity preserved from formula selection"
                ),
                f"Exact poison effect durations selected: {len(effects)}",
                "Dilution mode is caller-proven; this service never infers base/triple from effect count or item name.",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonDilutionMode",
    "ExtremeSustainedDPSWeaponPoisonSelectedEffect",
    "ExtremeSustainedDPSWeaponPoisonDilutionSelection",
    "ExtremeSustainedDPSWeaponPoisonDilutionSelectionService",
]
