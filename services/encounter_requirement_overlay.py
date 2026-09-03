from __future__ import annotations

"""Read-only overlay for explicit analysis-context requirements.

The canonical encounter service remains authoritative for boss mechanics. This proxy
only appends requirements supplied by another explicit source, such as a raid coverage
profile, while delegating every other encounter operation unchanged.
"""

from collections.abc import Mapping

from services.encounter_service import EncounterRequirement, EncounterService


class EncounterRequirementOverlayService:
    def __init__(
        self,
        base: EncounterService,
        additional_requirements: Mapping[str, tuple[EncounterRequirement, ...]],
    ) -> None:
        self._base = base
        self._additional = dict(additional_requirements)
        for encounter_id, rows in self._additional.items():
            if not encounter_id:
                raise ValueError("overlay encounter ids must be non-empty")
            seen: set[str] = set()
            for row in rows:
                if row.encounter_id != encounter_id:
                    raise ValueError(
                        "overlay requirement encounter_id must match its mapping key"
                    )
                if row.requirement_id in seen:
                    raise ValueError(
                        "overlay requirements cannot duplicate requirement_id within an encounter"
                    )
                seen.add(row.requirement_id)

    def requirements(self, encounter_id: str) -> tuple[EncounterRequirement, ...]:
        canonical = self._base.requirements(encounter_id)
        overlay = self._additional.get(encounter_id, ())
        canonical_ids = {row.requirement_id for row in canonical}
        collisions = canonical_ids & {row.requirement_id for row in overlay}
        if collisions:
            raise ValueError(
                "overlay requirement ids collide with canonical encounter requirements: "
                + ", ".join(sorted(collisions))
            )
        return canonical + overlay

    def __getattr__(self, name: str):
        return getattr(self._base, name)
