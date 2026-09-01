from __future__ import annotations

"""Canonical, update-aware Alchemy formula catalog.

The source corpus already exposes explicit formula rows. This module treats
those rows as evidence instead of trying to re-derive ESO's reagent interaction
rules from names or folklore.

A formula is identified by its reagent set plus its canonical trait set for a
specific game update. Duplicate appearances across per-effect UESP pages are
merged into one formula while retaining source evidence.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from .combat_effect_semantics import (
    GameUpdate,
    is_known_alchemy_trait,
    normalize_game_update,
    resolve_alchemy_trait_name,
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    return _clean(value).casefold()


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values:
        value = _clean(raw)
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return tuple(output)


def _normalize_source_trait_cell(value: str, *, game_update: GameUpdate) -> str:
    """Remove source-table annotations only when the underlying trait is known."""

    clean = _clean(value)
    suffix = " (triple)"
    if clean.casefold().endswith(suffix):
        candidate = clean[: -len(suffix)].strip()
        if is_known_alchemy_trait(candidate, game_update=game_update):
            return candidate
    return clean


@dataclass(frozen=True)
class AlchemyFormula:
    reagents: tuple[str, ...]
    traits: tuple[str, ...]
    game_update: GameUpdate
    source_effects: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()

    @property
    def canonical_id(self) -> str:
        reagent_key = "+".join(sorted(_norm(value).replace(" ", "_") for value in self.reagents))
        trait_key = "+".join(sorted(_norm(value).replace(" ", "_") for value in self.traits))
        return f"alchemy_formula:{self.game_update.value.casefold()}:{reagent_key}:{trait_key}"


@dataclass(frozen=True)
class AlchemyFormulaCatalog:
    formulas: tuple[AlchemyFormula, ...]
    game_update: GameUpdate
    unresolved: tuple[str, ...] = ()

    @classmethod
    def from_processed_payload(
        cls,
        payload: dict[str, Any],
        *,
        game_update: GameUpdate | str = GameUpdate.U50,
        allow_legacy_alias: bool = False,
    ) -> "AlchemyFormulaCatalog":
        update = normalize_game_update(game_update)
        unresolved: list[str] = []
        merged: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}

        effects = payload.get("effects", []) if isinstance(payload, dict) else []
        if not isinstance(effects, list):
            return cls((), update, ("Processed Alchemy payload has no effect list",))

        for effect_record in effects:
            if not isinstance(effect_record, dict):
                continue

            effect_name = _clean(effect_record.get("effect_name"))
            source_files = _unique(effect_record.get("source_files", []) or ())
            formulas = effect_record.get("formulas", [])
            if not isinstance(formulas, list):
                continue

            for index, formula in enumerate(formulas, start=1):
                if not isinstance(formula, dict):
                    continue

                reagents = _unique(formula.get("ingredients", []) or ())
                explicit_traits = _unique(formula.get("effects", []) or ())
                if len(reagents) < 2:
                    unresolved.append(
                        f"{effect_name or 'Alchemy effect'} formula #{index}: fewer than two reagents"
                    )
                    continue

                # Every formula row is evidence on a specific per-effect page.
                # The page's own effect is therefore part of the formula even
                # when the table only lists secondary effects in its cells.
                raw_traits = _unique((effect_name, *explicit_traits))
                if not raw_traits:
                    unresolved.append(
                        f"{effect_name or 'Alchemy effect'} formula #{index}: no explicit effects"
                    )
                    continue

                canonical_traits: list[str] = []
                removed_traits: list[str] = []
                unknown_traits: list[str] = []
                for source_trait in raw_traits:
                    raw_trait = _normalize_source_trait_cell(source_trait, game_update=update)
                    resolved = resolve_alchemy_trait_name(
                        raw_trait,
                        game_update=update,
                        allow_legacy_alias=allow_legacy_alias,
                    )
                    if resolved is None:
                        removed_traits.append(source_trait)
                        continue
                    if not is_known_alchemy_trait(resolved, game_update=update):
                        unknown_traits.append(source_trait)
                        continue
                    canonical_traits.append(resolved)

                if unknown_traits:
                    unresolved.append(
                        f"{effect_name or 'Alchemy effect'} formula #{index}: "
                        f"non-trait source cells rejected: {', '.join(unknown_traits)}"
                    )
                    continue

                if removed_traits:
                    unresolved.append(
                        f"{effect_name or 'Alchemy effect'} formula #{index}: "
                        f"obsolete traits for {update.value}: {', '.join(removed_traits)}"
                    )
                    if not allow_legacy_alias:
                        continue

                traits = _unique(canonical_traits)
                if not traits:
                    continue

                reagent_key = tuple(sorted(_norm(value) for value in reagents))
                trait_key = tuple(sorted(_norm(value) for value in traits))
                key = (reagent_key, trait_key)
                bucket = merged.setdefault(
                    key,
                    {
                        "reagents": reagents,
                        "traits": traits,
                        "source_effects": [],
                        "source_files": [],
                    },
                )
                if effect_name and effect_name not in bucket["source_effects"]:
                    bucket["source_effects"].append(effect_name)
                for source_file in source_files:
                    if source_file not in bucket["source_files"]:
                        bucket["source_files"].append(source_file)

        formulas_out = tuple(
            sorted(
                (
                    AlchemyFormula(
                        reagents=tuple(bucket["reagents"]),
                        traits=tuple(bucket["traits"]),
                        game_update=update,
                        source_effects=tuple(bucket["source_effects"]),
                        source_files=tuple(bucket["source_files"]),
                    )
                    for bucket in merged.values()
                ),
                key=lambda formula: formula.canonical_id,
            )
        )
        return cls(formulas_out, update, tuple(unresolved))

    def find_by_traits(self, *traits: str, exact: bool = True) -> tuple[AlchemyFormula, ...]:
        requested = {_norm(value) for value in traits if _clean(value)}
        if not requested:
            return ()

        matches: list[AlchemyFormula] = []
        for formula in self.formulas:
            available = {_norm(value) for value in formula.traits}
            if (exact and available == requested) or (not exact and requested.issubset(available)):
                matches.append(formula)
        return tuple(matches)
