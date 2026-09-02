from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .alchemy_formula_catalog import AlchemyFormula, AlchemyFormulaCatalog
from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import EffectLayer
from .combat_effect_semantics import GameUpdate, normalize_game_update
from .support_effect_category import SupportEffectCategory
from .support_target_type import SupportTargetType

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"
DEFAULT_PROCESSED = ROOT / "data" / "processed" / "alchemy_effects.json"


@dataclass(frozen=True)
class PotionAvailability:
    selected_label: str
    formulas: tuple[AlchemyFormula, ...] = ()
    effects: tuple[EffectVariant, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.formulas) and bool(self.effects) and not self.unresolved

    @property
    def canonical_traits(self) -> tuple[str, ...]:
        if not self.formulas:
            return ()
        return self.formulas[0].traits


class PotionAvailabilityRepository:
    """Resolve a saved potion selection to source-backed Potion EffectVariants.

    A selected potion proves availability only. It does not imply activation,
    standing uptime, cooldown use, or Medicinal Use ownership.

    The processed JSON is a convenient build-time artifact, not a required
    runtime dependency. The canonical SQLite import preserves each UESP alchemy
    record in ``effect_variant.raw_json``; when the processed file is omitted
    from a lean install, the catalog is reconstructed from those exact payloads.
    """

    LEGACY_ALIASES: dict[str, tuple[str, ...]] = {
        "spell power": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        "spell power potion": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        "health elixir": ("Restore Health",),
        "elixir of health": ("Restore Health",),
    }

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE,
        processed_path: str | Path = DEFAULT_PROCESSED,
        *,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        self.database_path = Path(database_path)
        self.processed_path = Path(processed_path)
        self.game_update = normalize_game_update(game_update)

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _slug(value: str) -> str:
        return "_".join(PotionAvailabilityRepository._norm(value).replace("-", " ").split())

    @classmethod
    def _family_id(cls, formula: AlchemyFormula) -> str:
        trait_key = "+".join(sorted(cls._slug(value) for value in formula.traits))
        return f"alchemy_family:{formula.game_update.value.casefold()}:{trait_key}"

    @staticmethod
    def _category(value: str | None) -> SupportEffectCategory:
        text = str(value or "").strip().casefold()
        if "debuff" in text:
            return SupportEffectCategory.DEBUFF
        if "buff" in text:
            return SupportEffectCategory.BUFF
        if "status" in text:
            return SupportEffectCategory.STATUS
        return SupportEffectCategory.OTHER

    def _database_catalog_payload(self) -> tuple[dict[str, object] | None, tuple[str, ...]]:
        if not self.database_path.exists():
            return None, (f"Alchemy database missing: {self.database_path}",)

        try:
            with sqlite3.connect(self.database_path) as db:
                tables = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not {"effect", "effect_variant"}.issubset(tables):
                    return None, ("Alchemy database is missing effect/effect_variant tables",)

                columns = {
                    str(row[1])
                    for row in db.execute("PRAGMA table_info(effect_variant)").fetchall()
                }
                if "raw_json" not in columns:
                    return None, ("Alchemy database effect_variant table has no raw_json source payload",)

                rows = db.execute(
                    """
                    SELECT e.name, ev.raw_json
                    FROM effect e
                    JOIN effect_variant ev ON ev.effect_id = e.id
                    WHERE lower(trim(COALESCE(ev.type, ''))) = 'potion'
                      AND trim(COALESCE(ev.raw_json, '')) <> ''
                    ORDER BY e.id, ev.id
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            return None, (f"Alchemy database catalog unreadable: {exc}",)

        effects: list[dict[str, object]] = []
        malformed = 0
        seen_names: set[str] = set()
        for effect_name, raw_json in rows:
            try:
                payload = json.loads(str(raw_json))
            except (TypeError, ValueError, json.JSONDecodeError):
                malformed += 1
                continue
            if not isinstance(payload, dict):
                malformed += 1
                continue
            formulas = payload.get("formulas")
            if not isinstance(formulas, list) or not formulas:
                continue

            name = str(payload.get("effect_name") or effect_name or "").strip()
            if not name or name.casefold() in seen_names:
                continue
            seen_names.add(name.casefold())
            effects.append(
                {
                    "effect_name": name,
                    "source_files": payload.get("source_files", []) or [],
                    "formulas": formulas,
                }
            )

        if not effects:
            detail = ""
            if malformed:
                detail = f"; {malformed} malformed raw_json payload(s) rejected"
            return None, (f"Alchemy database contains no reusable formula payloads{detail}",)
        return {"effects": effects}, ()

    def _catalog(self, *, allow_legacy_alias: bool = False) -> AlchemyFormulaCatalog:
        payload: dict[str, object] | None = None
        source_errors: tuple[str, ...] = ()

        if self.processed_path.exists():
            try:
                loaded = json.loads(self.processed_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
                else:
                    source_errors = ("Alchemy processed source is not a JSON object",)
            except (OSError, json.JSONDecodeError) as exc:
                source_errors = (f"Alchemy processed source unreadable: {exc}",)
        else:
            source_errors = (f"Alchemy processed source missing: {self.processed_path}",)

        if payload is None:
            payload, db_errors = self._database_catalog_payload()
            if payload is None:
                return AlchemyFormulaCatalog(
                    (),
                    self.game_update,
                    tuple(dict.fromkeys((*source_errors, *db_errors))),
                )

        return AlchemyFormulaCatalog.from_processed_payload(
            payload,
            game_update=self.game_update,
            allow_legacy_alias=allow_legacy_alias,
        )

    def _formulas_for_selection(self, selected_label: str) -> tuple[tuple[AlchemyFormula, ...], tuple[str, ...]]:
        clean = " ".join(str(selected_label or "").strip().split())
        if not clean:
            return (), ()

        catalog = self._catalog(allow_legacy_alias=self.game_update is GameUpdate.U51)
        if not catalog.formulas:
            return (), catalog.unresolved or ("Alchemy formula catalog is empty",)

        if clean.casefold().startswith("alchemy_formula:"):
            matches = tuple(
                formula
                for formula in catalog.formulas
                if formula.canonical_id.casefold() == clean.casefold()
            )
            if not matches:
                return (), (f"Potion formula not found for selection: {clean}",)
            return matches, ()

        if clean.casefold().startswith("alchemy_family:"):
            matches = tuple(
                formula
                for formula in catalog.formulas
                if self._family_id(formula).casefold() == clean.casefold()
            )
            if not matches:
                return (), (f"Potion effect family not found for selection: {clean}",)
            return matches, ()

        traits = self.LEGACY_ALIASES.get(self._norm(clean))
        if traits is None:
            return (), (
                f"Potion selection is not an exact canonical formula, canonical family, or known legacy alias: {clean}",
            )
        if self.game_update is GameUpdate.U51:
            traits = tuple(
                {"Increase Spell Power": "Increase Power", "Spell Critical": "Critical"}.get(value, value)
                for value in traits
            )
        matches = catalog.find_by_traits(*traits, exact=True)
        if not matches:
            return (), (f"Potion effect family not found for selection: {clean}",)
        return matches, ()

    def _effect_variants(
        self,
        traits: tuple[str, ...],
        selected_label: str,
    ) -> tuple[tuple[EffectVariant, ...], tuple[str, ...]]:
        if not self.database_path.exists():
            return (), (f"Alchemy database missing: {self.database_path}",)

        variants: list[EffectVariant] = []
        unresolved: list[str] = []
        with sqlite3.connect(self.database_path) as db:
            for trait in traits:
                row = db.execute(
                    """
                    SELECT ev.id, e.name, e.category, ev.type
                    FROM effect e
                    JOIN effect_variant ev ON ev.effect_id = e.id
                    WHERE lower(trim(e.name)) = lower(trim(?))
                      AND lower(trim(COALESCE(ev.type, ''))) = 'potion'
                    ORDER BY ev.id
                    LIMIT 1
                    """,
                    (trait,),
                ).fetchone()
                if row is None:
                    unresolved.append(f"Potion EffectVariant missing from database: {trait}")
                    continue
                _variant_id, effect_name, category, _variant_type = row
                variants.append(
                    EffectVariant(
                        name=self._slug(str(effect_name)),
                        layer=EffectLayer.CONSUMABLE,
                        source=f"Potion: {selected_label}",
                        trigger="potion_use",
                        condition="selected potion available; activation and uptime are not assumed",
                        target_type=SupportTargetType.SELF,
                        category=self._category(category),
                    )
                )
        return tuple(variants), tuple(unresolved)

    def resolve(self, selected_label: str) -> PotionAvailability:
        clean = " ".join(str(selected_label or "").strip().split())
        if not clean:
            return PotionAvailability(selected_label="")

        formulas, unresolved = self._formulas_for_selection(clean)
        if not formulas:
            return PotionAvailability(clean, (), (), unresolved)

        traits = formulas[0].traits
        if any(set(formula.traits) != set(traits) for formula in formulas[1:]):
            return PotionAvailability(
                clean,
                formulas,
                (),
                (f"Potion formula family has inconsistent effect traits: {clean}",),
            )

        effects, db_unresolved = self._effect_variants(traits, clean)
        return PotionAvailability(clean, formulas, effects, db_unresolved)
