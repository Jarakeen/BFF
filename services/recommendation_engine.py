# services/recommendation_engine.py
"""Simple effect-coverage recommendations from indexed reference data."""

from __future__ import annotations

from typing import Any, Iterable


class RecommendationEngine:
    """Rank individual alternatives by how many missing effects they provide."""

    def recommend(
        self,
        missing_effects: Iterable[str],
        reference_library: Any,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return skills, sets, and potions that solve missing effects.

        This method ranks candidates independently. It does not select a
        combination, assign choices, or optimize a roster.
        """
        required = {effect for effect in missing_effects if isinstance(effect, str)}
        return {
            "skills": self._rank_alternatives(required, "skills", reference_library),
            "sets": self._rank_alternatives(required, "gear_sets", reference_library),
            "potions": self._rank_alternatives(required, "potions", reference_library),
        }

    def _rank_alternatives(
        self,
        missing_effects: set[str],
        source_layer: str,
        reference_library: Any,
    ) -> list[dict[str, Any]]:
        candidates: dict[int, dict[str, Any]] = {}

        for effect in missing_effects:
            for record in reference_library.get_effect_providers(effect):
                if record.get("source_layer") != source_layer:
                    continue

                record_key = record.get("id") or id(record)
                candidate = candidates.setdefault(
                    record_key,
                    {
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "solved_effects": [],
                        "solved_count": 0,
                        "object": record,
                    },
                )
                if effect not in candidate["solved_effects"]:
                    candidate["solved_effects"].append(effect)
                    candidate["solved_count"] += 1

        return sorted(
            candidates.values(),
            key=lambda candidate: (
                -candidate["solved_count"],
                str(candidate["name"] or "").casefold(),
            ),
        )
