from __future__ import annotations

"""Audit canonical jewelry glyphs for Extreme max-resource relevance.

This service does not duplicate jewelry-glyph math.  It asks the canonical
``JewelryGlyphEffectRepository`` to resolve every known jewelry glyph and proves
objective irrelevance only when every glyph has mapped effects with known stat
identity and none can modify the requested max resource.

Unknown, empty, or stat-less glyph effects fail closed because they could hide a
resource-relevant mechanic.  Infused remains a separate trait interaction; this
service answers only whether the canonical glyph universe contains a direct
max-resource effect worth amplifying.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
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

    def build(self, objective_key: str) -> ExtremeJewelryResourceGlyphAudit:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
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
