from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.extreme_build_catalog_service import (
    CATALOG_SCHEMA_VERSION,
    SUBCLASS_RULE_VERSION,
    ExtremeBuildCatalogService,
)
from services.extreme_subclass_slot_allocation_service import (
    ExtremeSubclassSlotAllocationResult,
)


class ExtremeBuildCatalogRuntimeService:
    """Load and consume a precomputed Extreme Build catalog safely at runtime.

    This layer does not build the catalog. It only accepts a generated catalog
    when its schema version, subclass-rule version, and source database fingerprint
    match the current runtime database. A missing or stale catalog returns None so
    callers can fall back to canonical live enumeration instead of trusting stale
    structural data.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        catalog_path: str | Path | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.catalog_path = (
            Path(catalog_path)
            if catalog_path is not None
            else self.database_path.parent / "generated" / "extreme_build_catalog.json"
        )
        self.catalog = self._load_current_catalog()

    @property
    def available(self) -> bool:
        return self.catalog is not None

    def _load_current_catalog(self) -> dict[str, Any] | None:
        if not self.catalog_path.is_file() or not self.database_path.is_file():
            return None
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return None
        if metadata.get("schema_version") != CATALOG_SCHEMA_VERSION:
            return None
        if metadata.get("subclass_rule_version") != SUBCLASS_RULE_VERSION:
            return None

        expected = metadata.get("source_database_sha256")
        actual = ExtremeBuildCatalogService(self.database_path).database_fingerprint()
        if not expected or expected != actual:
            return None
        return payload

    def reviewed_allocations(
        self,
        equipped_skill_lines: tuple[str, ...],
        objective_key: str,
        *,
        reference_value: float | None = None,
        include_known_zero: bool = False,
    ) -> tuple[ExtremeSubclassSlotAllocationResult, ...] | None:
        """Rehydrate reviewed allocation scores from cached formulas.

        Returns None when this catalog cannot answer the requested line set. That
        is intentionally different from an empty tuple: None tells the caller to
        fall back to live canonical scoring, while () means the current catalog
        handled the line set but found no resolved allocation for this context.
        """
        if self.catalog is None:
            return None
        objective = str(objective_key or "").strip()
        lines = tuple(sorted(str(line or "").strip().casefold() for line in equipped_skill_lines))
        if not objective or not lines:
            return ()

        line_key = "|".join(lines)
        formula_root = self.catalog.get("passive_allocation_formulas", {})
        by_line_set = formula_root.get("by_line_set", {}) if isinstance(formula_root, dict) else {}
        rows = by_line_set.get(line_key)
        if not isinstance(rows, list):
            return None

        results: list[ExtremeSubclassSlotAllocationResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_slot_counts = row.get("slot_counts")
            if not isinstance(raw_slot_counts, list):
                continue
            try:
                slot_counts = tuple((str(line), int(count)) for line, count in raw_slot_counts)
            except (TypeError, ValueError):
                continue

            formulas = row.get("formulas", [])
            matching = [
                item
                for item in formulas
                if isinstance(item, dict) and item.get("objective_key") == objective
            ]
            if not matching:
                if include_known_zero:
                    results.append(
                        ExtremeSubclassSlotAllocationResult(
                            objective_key=objective,
                            equipped_skill_lines=lines,
                            slot_counts=slot_counts,
                            projected_delta=0.0,
                            reviewed_sources=(),
                        )
                    )
                continue

            if reference_value is None and any(
                float(item.get("percent_of_reference") or 0.0) != 0.0
                for item in matching
            ):
                continue

            projected = 0.0
            sources: list[str] = []
            for item in matching:
                projected += float(item.get("flat") or 0.0)
                projected += float(item.get("ratio") or 0.0)
                projected += float(reference_value or 0.0) * float(
                    item.get("percent_of_reference") or 0.0
                )
                sources.extend(str(source) for source in item.get("sources", ()))

            results.append(
                ExtremeSubclassSlotAllocationResult(
                    objective_key=objective,
                    equipped_skill_lines=lines,
                    slot_counts=slot_counts,
                    projected_delta=projected,
                    reviewed_sources=tuple(sources),
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda row: (-row.projected_delta, row.slot_counts),
            )
        )
