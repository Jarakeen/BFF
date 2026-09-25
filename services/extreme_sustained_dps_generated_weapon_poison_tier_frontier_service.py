from __future__ import annotations

"""Source-backed generated weapon-poison tier frontier.

Generated poison formulas prove an exact Alchemy trait set but not a crafted inventory
label or tier. Imported Poison effect rows independently preserve solvent, level, and
base/triple durations. This service intersects those tier coordinates across every trait
in one exact formula and exposes the common finite tier denominator without inventing
an item name or selecting a preferred tier.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from minmax.alchemy_formula_catalog import AlchemyFormula
from services.extreme_sustained_dps_weapon_poison_identity_service import (
    ExtremeSustainedDPSWeaponPoisonItemEvidence,
    ExtremeSustainedDPSWeaponPoisonPossibleEffect,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate:
    structural_index: int
    solvent: str
    level: int
    item_evidence: ExtremeSustainedDPSWeaponPoisonItemEvidence


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier:
    candidates: tuple[ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService:
    """Enumerate common source-backed Poison tier coordinates for an exact formula."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _norm(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _float(value: object) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _trait_rows(
        self,
        formula: AlchemyFormula,
    ) -> tuple[
        dict[str, dict[tuple[str, int], ExtremeSustainedDPSWeaponPoisonPossibleEffect]],
        tuple[str, ...],
        int,
    ]:
        if not self.database_path.exists():
            return {}, (f"Alchemy database missing: {self.database_path}",), 0

        wanted = {self._norm(trait): str(trait).strip() for trait in formula.traits}
        if not wanted:
            return {}, ("generated poison formula has no canonical traits",), 0

        try:
            with sqlite3.connect(self.database_path) as db:
                tables = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not {"effect", "effect_variant"}.issubset(tables):
                    return {}, (
                        "Alchemy database is missing effect/effect_variant tables",
                    ), 0
                columns = {
                    str(row[1])
                    for row in db.execute(
                        "PRAGMA table_info(effect_variant)"
                    ).fetchall()
                }
                if "raw_json" not in columns:
                    return {}, (
                        "Alchemy database effect_variant table has no raw_json source payload",
                    ), 0
                rows = db.execute(
                    """
                    SELECT e.name, ev.raw_json
                    FROM effect e
                    JOIN effect_variant ev ON ev.effect_id = e.id
                    WHERE lower(trim(COALESCE(ev.type, ''))) = 'poison'
                      AND trim(COALESCE(ev.raw_json, '')) <> ''
                    ORDER BY e.id, ev.id
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            return {}, (f"Alchemy poison catalog unreadable: {exc}",), 0

        found: dict[
            str,
            dict[tuple[str, int], ExtremeSustainedDPSWeaponPoisonPossibleEffect],
        ] = {key: {} for key in wanted}
        unresolved: list[str] = []
        inspected = 0

        for db_effect_name, raw_json in rows:
            db_effect_key = self._norm(db_effect_name)
            try:
                payload = json.loads(str(raw_json))
            except (TypeError, ValueError, json.JSONDecodeError):
                if db_effect_key in wanted:
                    unresolved.append(
                        f"{wanted[db_effect_key]} has malformed imported Poison source payload"
                    )
                continue
            if not isinstance(payload, dict):
                if db_effect_key in wanted:
                    unresolved.append(
                        f"{wanted[db_effect_key]} has non-object imported Poison source payload"
                    )
                continue

            effect_name = str(
                payload.get("effect_name") or db_effect_name or ""
            ).strip()
            effect_key = self._norm(effect_name)
            if effect_key not in wanted:
                continue

            tiers = payload.get("tiers")
            if not isinstance(tiers, list):
                unresolved.append(
                    f"{wanted[effect_key]} has no imported Poison tier rows"
                )
                continue

            for tier in tiers:
                if not isinstance(tier, dict):
                    continue
                inspected += 1
                solvent = str(tier.get("solvent") or "").strip()
                level = self._int(tier.get("level"))
                duration = self._float(tier.get("duration"))
                triple_duration = self._float(tier.get("triple_duration"))
                if not solvent or level is None or duration is None or duration < 0.0:
                    continue

                coordinate = (self._norm(solvent), int(level))
                row = ExtremeSustainedDPSWeaponPoisonPossibleEffect(
                    effect_name=wanted[effect_key],
                    base_duration_seconds=float(duration),
                    triple_duration_seconds=triple_duration,
                    solvent=solvent,
                    level=int(level),
                )
                existing = found[effect_key].get(coordinate)
                if existing is not None and existing != row:
                    unresolved.append(
                        f"{wanted[effect_key]} has conflicting Poison tier evidence "
                        f"for {solvent} level {level}"
                    )
                    continue
                found[effect_key][coordinate] = row

        for key, display in wanted.items():
            if not found[key]:
                unresolved.append(
                    f"{display} has no usable imported Poison tier evidence"
                )

        return found, tuple(dict.fromkeys(unresolved)), inspected

    def frontier(
        self,
        formula: AlchemyFormula,
    ) -> ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier:
        found, unresolved, inspected = self._trait_rows(formula)
        trait_keys = tuple(self._norm(trait) for trait in formula.traits)

        common: set[tuple[str, int]] = set()
        if trait_keys and all(key in found and found[key] for key in trait_keys):
            common = set(found[trait_keys[0]])
            for key in trait_keys[1:]:
                common.intersection_update(found[key])

        if not common and not unresolved:
            unresolved = (
                "generated poison formula traits share no common solvent/level tier coordinate",
            )

        candidates: list[ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate] = []
        for index, coordinate in enumerate(
            sorted(common, key=lambda row: (row[1], row[0]))
        ):
            solvent_key, level = coordinate
            effects = tuple(found[key][coordinate] for key in trait_keys)
            solvent = str(effects[0].solvent or "").strip()
            candidates.append(
                ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate(
                    structural_index=index,
                    solvent=solvent,
                    level=int(level),
                    item_evidence=ExtremeSustainedDPSWeaponPoisonItemEvidence(
                        poison_id=formula.canonical_id,
                        possible_effects=effects,
                        source_evidence_complete=True,
                        exact_selection_proven=False,
                        evidence=(
                            f"Generated formula tier coordinate: {solvent} level {level}",
                            f"Formula traits with matching tier evidence: {len(effects)}/{len(trait_keys)}",
                            "Tier evidence was matched by canonical trait + solvent + level, not by crafted item display name.",
                        ),
                        unresolved=(
                            "generated formula tier evidence proves durations but dilution mode remains separate",
                        ),
                    ),
                )
            )

        final_unresolved = tuple(
            dict.fromkeys(str(row).strip() for row in unresolved if str(row).strip())
        )
        denominator_proven = bool(candidates) and not final_unresolved
        return ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier(
            candidates=tuple(candidates),
            candidate_count=len(candidates),
            denominator_proven=denominator_proven,
            evidence=(
                f"Generated poison formula traits: {len(trait_keys)}",
                f"Imported matching Poison tier rows inspected: {inspected}",
                f"Common solvent/level tier coordinates: {len(candidates)}",
                "No preferred poison tier is selected by this frontier.",
            ),
            unresolved=final_unresolved,
        )

    def candidate_at(
        self,
        formula: AlchemyFormula,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate:
        frontier = self.frontier(formula)
        if not frontier.denominator_proven:
            raise ValueError(
                "generated poison tier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )
        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("generated poison tier candidate index out of range")
        return frontier.candidates[target]


__all__ = [
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate",
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontier",
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService",
]
