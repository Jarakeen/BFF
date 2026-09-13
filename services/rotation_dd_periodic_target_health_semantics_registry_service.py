from __future__ import annotations

"""Load reviewed DD periodic target-Health timing semantics from repository data.

The registry is evidence-only. It does not infer whether a periodic target-Health
condition snapshots at cast or re-checks on every tick. Missing or empty registry
data therefore resolves to no executable target-Health timing semantics.
"""

import json
from pathlib import Path

from services.rotation_periodic_target_health_semantics_service import (
    PeriodicTargetHealthTimingPolicy,
    RotationPeriodicTargetHealthSemantics,
)


class RotationDDPeriodicTargetHealthSemanticsRegistryService:
    """Load source-reviewed periodic target-Health timing semantics."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "rotation_dd_periodic_target_health_semantics.json"
        )

    def load(self) -> tuple[RotationPeriodicTargetHealthSemantics, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                "DD periodic target-Health semantics registry must be a JSON object"
            )
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError(
                "DD periodic target-Health semantics registry schema_version must be 1"
            )
        rows = payload.get("entries", [])
        if not isinstance(rows, list):
            raise ValueError(
                "DD periodic target-Health semantics entries must be a list"
            )

        semantics: list[RotationPeriodicTargetHealthSemantics] = []
        seen: set[tuple[str, int]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(
                    f"DD periodic target-Health semantics entry {index} must be an object"
                )
            try:
                semantic = RotationPeriodicTargetHealthSemantics(
                    skill_entity_id=str(row["skill_entity_id"]),
                    coefficient_number=int(row["coefficient_number"]),
                    policy=PeriodicTargetHealthTimingPolicy(str(row["policy"])),
                    source=str(row["source"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid DD periodic target-Health semantics entry {index}: {exc}"
                ) from exc

            key = (semantic.skill_entity_id, semantic.coefficient_number)
            if key in seen:
                raise ValueError(
                    "duplicate DD periodic target-Health semantics for "
                    f"{semantic.skill_entity_id} coefficient {semantic.coefficient_number}"
                )
            seen.add(key)
            semantics.append(semantic)
        return tuple(semantics)


__all__ = ["RotationDDPeriodicTargetHealthSemanticsRegistryService"]
