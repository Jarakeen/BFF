from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from minmax.alchemy_formula_catalog import AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate, normalize_game_update


@dataclass(frozen=True)
class PotionChoice:
    label: str
    canonical_id: str
    traits: tuple[str, ...]
    formula_count: int


class PotionChoiceService:
    """Build compact selectable potion effect families from canonical formulas."""

    def __init__(
        self,
        processed_path: str | Path,
        *,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        self.processed_path = Path(processed_path)
        self.game_update = normalize_game_update(game_update)

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _slug(value: str) -> str:
        return "_".join(PotionChoiceService._clean(value).casefold().replace("-", " ").split())

    @classmethod
    def family_id(cls, traits: tuple[str, ...], game_update: GameUpdate | str) -> str:
        update = normalize_game_update(game_update)
        trait_key = "+".join(sorted(cls._slug(value) for value in traits if cls._clean(value)))
        return f"alchemy_family:{update.value.casefold()}:{trait_key}"

    def _catalog(self) -> AlchemyFormulaCatalog:
        if not self.processed_path.exists():
            return AlchemyFormulaCatalog((), self.game_update, (f"Alchemy processed source missing: {self.processed_path}",))
        try:
            payload = json.loads(self.processed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return AlchemyFormulaCatalog((), self.game_update, (f"Alchemy processed source unreadable: {exc}",))
        return AlchemyFormulaCatalog.from_processed_payload(
            payload,
            game_update=self.game_update,
            allow_legacy_alias=self.game_update is GameUpdate.U51,
        )

    def list_choices(self) -> list[PotionChoice]:
        groups: dict[tuple[str, ...], list] = {}
        for formula in self._catalog().formulas:
            key = tuple(sorted(formula.traits, key=str.casefold))
            groups.setdefault(key, []).append(formula)

        choices = [
            PotionChoice(
                label=" + ".join(traits),
                canonical_id=self.family_id(traits, self.game_update),
                traits=traits,
                formula_count=len(formulas),
            )
            for traits, formulas in groups.items()
        ]
        return sorted(choices, key=lambda choice: choice.label.casefold())
