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
    mode: ExtremeSustainedDPSWeaponPoisonDilutionMode | None
    effects: tuple[ExtremeSustainedDPSWeaponPoisonSelectedEffect, ...]
    effect_modes: tuple[
        tuple[str, ExtremeSustainedDPSWeaponPoisonDilutionMode],
        ...,
    ] = ()
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
            effect_modes=tuple(
                (effect.effect_name, selected_mode)
                for effect in effects
            ),
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


    @classmethod
    def resolve_per_effect(
        cls,
        *,
        formula_selection: ExtremeSustainedDPSWeaponPoisonFormulaSelection,
        effect_modes: tuple[
            tuple[str, ExtremeSustainedDPSWeaponPoisonDilutionMode | str],
            ...,
        ],
        poison_id_override: str | None = None,
    ) -> ExtremeSustainedDPSWeaponPoisonDilutionSelection:
        unresolved: list[str] = list(tuple(formula_selection.unresolved))
        if not formula_selection.exact_effect_set_proven:
            unresolved.append(
                "weapon-poison per-effect dilution selection requires a proven formula effect set"
            )

        normalized_modes: dict[
            str,
            ExtremeSustainedDPSWeaponPoisonDilutionMode,
        ] = {}
        display_names: dict[str, str] = {}
        for raw_name, raw_mode in tuple(effect_modes):
            name = " ".join(str(raw_name or "").strip().split())
            key = name.casefold()
            if not key:
                unresolved.append(
                    "weapon-poison per-effect dilution witness has blank effect name"
                )
                continue
            try:
                selected_mode = (
                    raw_mode
                    if isinstance(
                        raw_mode,
                        ExtremeSustainedDPSWeaponPoisonDilutionMode,
                    )
                    else ExtremeSustainedDPSWeaponPoisonDilutionMode(
                        str(raw_mode or "").strip().casefold()
                    )
                )
            except ValueError:
                unresolved.append(
                    f"{name}: unsupported weapon-poison dilution mode {raw_mode!r}"
                )
                continue
            existing = normalized_modes.get(key)
            if existing is not None and existing is not selected_mode:
                unresolved.append(
                    f"{name}: conflicting per-effect dilution witnesses"
                )
                continue
            normalized_modes[key] = selected_mode
            display_names[key] = name

        selected_effect_keys = {
            str(source.effect_name or "").strip().casefold()
            for source in tuple(formula_selection.selected_effects)
        }
        extra = tuple(
            display_names[key]
            for key in normalized_modes
            if key not in selected_effect_keys
        )
        if extra:
            unresolved.append(
                "per-effect dilution witness includes effects outside the proven formula: "
                + ", ".join(extra)
            )

        effects: list[ExtremeSustainedDPSWeaponPoisonSelectedEffect] = []
        selected_modes: list[
            tuple[str, ExtremeSustainedDPSWeaponPoisonDilutionMode]
        ] = []
        for source in tuple(formula_selection.selected_effects):
            effect_name = str(source.effect_name or "").strip()
            key = effect_name.casefold()
            selected_mode = normalized_modes.get(key)
            if selected_mode is None:
                unresolved.append(
                    f"{formula_selection.poison_id}: {effect_name} has no explicit "
                    "per-effect dilution witness"
                )
                continue

            if selected_mode is ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE:
                duration = float(source.base_duration_seconds)
            else:
                if source.triple_duration_seconds is None:
                    unresolved.append(
                        f"{formula_selection.poison_id}: {effect_name} has no "
                        "source-preserved triple-effect duration"
                    )
                    continue
                duration = float(source.triple_duration_seconds)

            if duration < 0.0:
                unresolved.append(
                    f"{formula_selection.poison_id}: {effect_name} selected "
                    "duration cannot be negative"
                )
                continue
            effects.append(
                ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                    effect_name=effect_name,
                    duration_seconds=duration,
                )
            )
            selected_modes.append((effect_name, selected_mode))

        selected_poison_id = (
            str(poison_id_override or "").strip()
            or str(formula_selection.poison_id or "").strip()
        )
        deduped = tuple(dict.fromkeys(row for row in unresolved if row))
        return ExtremeSustainedDPSWeaponPoisonDilutionSelection(
            poison_id=selected_poison_id,
            formula_id=str(formula_selection.formula_id or "").strip(),
            mode=None,
            effects=tuple(effects),
            effect_modes=tuple(selected_modes),
            evidence=(
                *tuple(formula_selection.evidence),
                f"Explicit per-effect weapon-poison dilution witnesses: {len(selected_modes)}",
                (
                    f"Runtime poison identity override: {selected_poison_id}"
                    if poison_id_override
                    else "Runtime poison identity preserved from formula selection"
                ),
                f"Exact poison effect durations selected: {len(effects)}",
                "Per-effect dilution modes are caller-proven; mixed base/triple formulas "
                "are supported without promoting unmarked source cells into mechanics.",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonDilutionMode",
    "ExtremeSustainedDPSWeaponPoisonSelectedEffect",
    "ExtremeSustainedDPSWeaponPoisonDilutionSelection",
    "ExtremeSustainedDPSWeaponPoisonDilutionSelectionService",
]
