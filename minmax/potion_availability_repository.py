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
    formula: AlchemyFormula | None
    effects: tuple[EffectVariant, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.formula is not None and bool(self.effects) and not self.unresolved


class PotionAvailabilityRepository:
    """Resolve a saved potion selection to source-backed Potion EffectVariants.

    This repository models *availability*, not uptime. A selected potion proves
    the build can use that formula. It does not apply its effects to standing
    character stats and it does not infer cooldown, Medicinal Use, or use timing.
    """

    LEGACY_ALIASES: dict[str, tuple[str, ...]] = {
        "spell power": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        "spell power potion": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
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

    def _catalog(self, *, allow_legacy_alias: bool = False) -> AlchemyFormulaCatalog:
        if not self.processed_path.exists():
            return AlchemyFormulaCatalog((), self.game_update, (f"Alchemy processed source missing: {self.processed_path}",))
        try:
            payload = json.loads(self.processed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return AlchemyFormulaCatalog((), self.game_update, (f"Alchemy processed source unreadable: {exc}",))
        return AlchemyFormulaCatalog.from_processed_payload(
            payload,
            game_update=self.game_update,
            allow_legacy_alias=allow_legacy_alias,
        )

    def _formula_for_selection(self, selected_label: str) -> tuple[AlchemyFormula | None, tuple[str, ...]]:
        clean = " ".join(str(selected_label or "").strip().split())
        if not clean:
            return None, ()

        catalog = self._catalog(allow_legacy_alias=self.game_update is GameUpdate.U51)
        if not catalog.formulas:
            return None, catalog.unresolved or ("Alchemy formula catalog is empty",)

        # Canonical IDs are the durable saved identity for arbitrary crafted
        # formulas. Legacy aliases exist only for old saved-build compatibility.
        if clean.casefold().startswith("alchemy_formula:"):
            matches = tuple(formula for formula in catalog.formulas if formula.canonical_id.casefold() == clean.casefold())
        else:
            traits = self.LEGACY_ALIASES.get(self._norm(clean))
            if traits is None:
                return None, (
                    f"Potion selection is not an exact canonical formula or known legacy alias: {clean}",
                )
            if self.game_update is GameUpdate.U51:
                traits = tuple(
                    {"Increase Spell Power": "Increase Power", "Spell Critical": "Critical"}.get(value, value)
                    for value in traits
                )
            matches = catalog.find_by_traits(*traits, exact=True)

        if len(matches) == 1:
            return matches[0], ()
        if not matches:
            return None, (f"Potion formula not found for selection: {clean}",)
        return None, (
            f"Potion selection resolves to {len(matches)} formulas and must be saved by canonical formula ID: {clean}",
        )

    def _effect_variants(self, formula: AlchemyFormula, selected_label: str) -> tuple[tuple[EffectVariant, ...], tuple[str, ...]]:
        if not self.database_path.exists():
            return (), (f"Alchemy database missing: {self.database_path}",)

        variants: list[EffectVariant] = []
        unresolved: list[str] = []
        with sqlite3.connect(self.database_path) as db:
            for trait in formula.traits:
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
            return PotionAvailability(selected_label="", formula=None)

        formula, unresolved = self._formula_for_selection(clean)
        if formula is None:
            return PotionAvailability(clean, None, (), unresolved)

        effects, db_unresolved = self._effect_variants(formula, clean)
        return PotionAvailability(clean, formula, effects, db_unresolved)
