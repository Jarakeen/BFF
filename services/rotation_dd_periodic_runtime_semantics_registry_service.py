from __future__ import annotations

import json
from pathlib import Path

from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
    RotationPeriodicDamageRuntimeSemantics,
)


class RotationDDPeriodicRuntimeSemanticsRegistryService:
    """Load reviewed DD periodic runtime semantics from versioned repository data.

    The registry is deliberately evidence-only. It does not infer activation anchors,
    first-tick timing, refresh behavior, magnitude timing, cadence, or successive-hit
    scaling from skill names or tooltip prose. Missing/empty registries therefore
    resolve to no executable periodic semantics.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "rotation_dd_periodic_runtime_semantics.json"
        )

    def load(self) -> tuple[RotationPeriodicDamageRuntimeSemantics, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("DD periodic runtime semantics registry must be a JSON object")
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError(
                "DD periodic runtime semantics registry schema_version must be 1"
            )
        rows = payload.get("entries", [])
        if not isinstance(rows, list):
            raise ValueError("DD periodic runtime semantics entries must be a list")

        semantics: list[RotationPeriodicDamageRuntimeSemantics] = []
        seen: set[tuple[str, int]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(
                    f"DD periodic runtime semantics entry {index} must be an object"
                )
            try:
                semantic = RotationPeriodicDamageRuntimeSemantics(
                    skill_entity_id=str(row["skill_entity_id"]),
                    coefficient_number=int(row["coefficient_number"]),
                    first_tick_offset_seconds=float(row["first_tick_offset_seconds"]),
                    refresh_boundary=PeriodicDamageRefreshBoundary(
                        str(row["refresh_boundary"])
                    ),
                    source=str(row["source"]),
                    verified_interval_seconds=(
                        None
                        if row.get("verified_interval_seconds") is None
                        else float(row["verified_interval_seconds"])
                    ),
                    magnitude_policy=PeriodicDamageMagnitudePolicy(
                        str(row["magnitude_policy"])
                    ),
                    successive_hit_multiplier=(
                        None
                        if row.get("successive_hit_multiplier") is None
                        else float(row["successive_hit_multiplier"])
                    ),
                    activation_anchor=PeriodicDamageActivationAnchor(
                        str(row.get("activation_anchor", "cast"))
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid DD periodic runtime semantics entry {index}: {exc}"
                ) from exc
            key = (semantic.skill_entity_id, semantic.coefficient_number)
            if key in seen:
                raise ValueError(
                    "duplicate DD periodic runtime semantics for "
                    f"{semantic.skill_entity_id} coefficient {semantic.coefficient_number}"
                )
            seen.add(key)
            semantics.append(semantic)
        return tuple(semantics)


__all__ = ["RotationDDPeriodicRuntimeSemanticsRegistryService"]
