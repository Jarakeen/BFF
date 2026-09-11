from __future__ import annotations

"""Audit canonical jewelry glyphs for Extreme max-resource relevance.

This service owns no jewelry arithmetic. It reviews the canonical semantic effect
identities recorded for every jewelry glyph and asks only whether any effect can
directly modify the requested maximum resource. Legitimate non-core-stat mechanics
such as block-cost reduction or potion duration therefore remain valid catalog
evidence without being forced through ``EffectMapper``.

Legacy corpus rows with a sparse semantic-effect table may fall back to their
stored canonical description. That fallback is proof-only: it can prove a row
irrelevant to the requested max resource or keep it relevant/unresolved, but it
never invents engine arithmetic or mutates the database.

Unknown or empty semantic identities and descriptions fail closed. Infused remains
a separate trait interaction; this service answers only whether the canonical glyph
universe contains a direct max-resource effect worth amplifying.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.stat_ids import StatId
from services.extreme_gear_set_resource_objective_screening_service import (
    ExtremeGearSetResourceObjectiveScreeningService,
)


_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}
_OBJECTIVE_EFFECT_TYPES = {
    "max_health": frozenset(("max_health", "maximum_health")),
    "max_magicka": frozenset(("max_magicka", "maximum_magicka")),
    "max_stamina": frozenset(("max_stamina", "maximum_stamina")),
}


@dataclass(frozen=True)
class ExtremeJewelryResourceGlyphAudit:
    objective_key: str
    glyphs_reviewed: int
    relevant_glyphs: tuple[str, ...]
    irrelevant_glyphs: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return self.glyphs_reviewed > 0 and not self.unresolved

    @property
    def objective_irrelevance_proven(self) -> bool:
        return self.denominator_proven and not self.relevant_glyphs


class ExtremeJewelryResourceGlyphRelevanceService:
    """Prove whether any canonical jewelry glyph can directly change a max resource."""

    SUPPORTED_OBJECTIVES = tuple(_OBJECTIVE_STATS)

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: JewelryGlyphEffectRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no jewelry glyph repository is supplied")
        self.repository = repository or JewelryGlyphEffectRepository(database_path)  # type: ignore[arg-type]

    def _effect_types(self, name: str) -> tuple[str, ...] | None:
        resolver = getattr(self.repository, "get_jewelry_glyph_effect_types_by_name", None)
        if not callable(resolver):
            return None
        return tuple(
            dict.fromkeys(
                str(value or "").strip().casefold()
                for value in resolver(name)
                if str(value or "").strip()
            )
        )

    def _descriptions(self, name: str) -> tuple[str, ...]:
        resolver = getattr(self.repository, "get_jewelry_glyph_descriptions_by_name", None)
        if not callable(resolver):
            return ()
        return tuple(
            dict.fromkeys(
                str(value or "").strip()
                for value in resolver(name)
                if str(value or "").strip()
            )
        )

    @staticmethod
    def _description_classification(
        descriptions: tuple[str, ...],
        objective_key: str,
    ) -> str:
        """Return irrelevant/relevant/unresolved for sparse semantic rows."""
        if not descriptions:
            return "unresolved"
        saw_relevant = False
        for description in descriptions:
            screening = ExtremeGearSetResourceObjectiveScreeningService.review(
                description,
                objective_key,
            )
            if screening.target_resource_mentioned:
                saw_relevant = True
                continue
            if not screening.proven_irrelevant:
                return "unresolved"
        return "relevant" if saw_relevant else "irrelevant"

    def build(self, objective_key: str) -> ExtremeJewelryResourceGlyphAudit:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        target_effect_types = _OBJECTIVE_EFFECT_TYPES.get(key)
        if target is None or target_effect_types is None:
            raise KeyError(f"unreviewed Extreme jewelry resource glyph objective: {objective_key!r}")

        names = tuple(
            dict.fromkeys(
                str(name or "").strip()
                for name in self.repository.list_names()
                if str(name or "").strip()
            )
        )
        unresolved: list[str] = []
        relevant: list[str] = []
        irrelevant: list[str] = []

        if not names:
            unresolved.append("Canonical jewelry glyph catalog is empty")

        for name in names:
            semantic_effects = self._effect_types(name)
            if semantic_effects is not None:
                if not semantic_effects:
                    classification = self._description_classification(
                        self._descriptions(name),
                        key,
                    )
                    if classification == "irrelevant":
                        irrelevant.append(name)
                    elif classification == "relevant":
                        relevant.append(name)
                    else:
                        unresolved.append(
                            f"Canonical jewelry glyph has no semantic effects or proof-safe description classification: {name}"
                        )
                    continue
                if any(effect_type in target_effect_types for effect_type in semantic_effects):
                    relevant.append(name)
                else:
                    irrelevant.append(name)
                continue

            # Compatibility fallback for injected/legacy repositories that expose
            # only mapped engine effects. Production uses semantic source identity.
            effects = tuple(
                self.repository.get_jewelry_glyph_effect_by_name(
                    name,
                    use_max_value=True,
                )
            )
            if not effects:
                unresolved.append(f"Canonical jewelry glyph has no mapped effects: {name}")
                continue

            unknown = tuple(effect for effect in effects if effect.stat is None)
            if unknown:
                unresolved.append(
                    f"Canonical jewelry glyph has effect(s) without stat identity: {name}"
                )
                continue

            if any(effect.stat is target for effect in effects):
                relevant.append(name)
            else:
                irrelevant.append(name)

        return ExtremeJewelryResourceGlyphAudit(
            objective_key=key,
            glyphs_reviewed=len(names),
            relevant_glyphs=tuple(sorted(relevant, key=str.casefold)),
            irrelevant_glyphs=tuple(sorted(irrelevant, key=str.casefold)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
