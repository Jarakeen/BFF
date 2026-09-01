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

    This repository models *availability*, not uptime. A selected potion proves
    the build can use that effect family/formula. It does not apply its effects
    to standing character stats and it does not infer cooldown, Medicinal Use,
    or use timing.
    """

    LEGACY_ALIASES: dict[str, tuple[str, ...]] = {
        "spell power": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        "spell power potion": ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        # Older Builds UI values used human tier-name wording rather than a
        # canonical formula identity. These aliases mean only the single
        # Restore Health effect family; they do not imply tri-stat or another
        # multi-effect crafted formula.
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

    def _formulas_for_selection(self, selected_label: str) -> tuple[tuple[AlchemyFormula, ...], tuple[str, ...]]:
        clean = " ".join(str(selected_label or "").strip().split())
        if not clean:
            return (), ()

        catalog = self._catalog(allow_legacy_alias=self.game_update is GameUpdate.U51)
        if not catalog.formulas:
            return (), catalog.unresolved or ("Alchemy formula catalog is empty",)

        # Canonical formula IDs are a durable identity for one specific recipe.
        # Legacy aliases identify an effect family and may therefore have more
        # than one equivalent reagent formula.
        if clean.casefold().startswith("alchemy_formula:"):
            matches = tuple(
                formula
                for formula in catalog.formulas
                if formula.canonical_id.casefold() == clean.casefold()
            )
            if not matches:
                return (), (f"Potion formula not found for selection: {clean}",)
            return matches, ()

        traits = self.LEGACY_ALIASES.get(self._norm(clean))
        if traits is None:
            return (), (
                f"Potion selection is not an exact canonical formula or known legacy alias: {clean}",
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

        # Equivalent formulas in one family have the same canonical trait set.
        # Use that effect identity once; reagent alternatives remain inspectable
        # through `formulas` rather than duplicating EffectVariants.
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
