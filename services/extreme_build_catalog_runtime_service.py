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
    ExtremeSubclassSlotAllocationService,
)


class ExtremeBuildCatalogRuntimeService:
    """Load and consume a precomputed Extreme Build catalog safely at runtime.

    This layer does not build the catalog. It only accepts a generated catalog
    when its schema version, subclass-rule version, and source database fingerprint
    match the current runtime database. A missing, stale, incompatible, or
    structurally malformed catalog returns None so callers can fall back to
    canonical live enumeration instead of trusting damaged cached data.
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

    @staticmethod
    def _parse_slot_counts(
        raw_slot_counts: object,
        *,
        expected_lines: tuple[str, ...],
    ) -> tuple[tuple[str, int], ...] | None:
        if not isinstance(raw_slot_counts, list):
            return None
        parsed: list[tuple[str, int]] = []
        try:
            for item in raw_slot_counts:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    return None
                line = str(item[0] or "").strip().casefold()
                count = int(item[1])
                if not line or count < 0:
                    return None
                parsed.append((line, count))
        except (TypeError, ValueError):
            return None

        slot_counts = tuple(parsed)
        if tuple(sorted(line for line, _ in slot_counts)) != expected_lines:
            return None
        if len({line for line, _ in slot_counts}) != len(expected_lines):
            return None
        if sum(count for _, count in slot_counts) != ExtremeSubclassSlotAllocationService.ACTIVE_BAR_SLOTS:
            return None
        return slot_counts

    @staticmethod
    def _numeric_formula_value(item: dict[str, Any], key: str) -> float | None:
        try:
            return float(item.get(key) or 0.0)
        except (TypeError, ValueError):
            return None

    def reviewed_allocations(
        self,
        equipped_skill_lines: tuple[str, ...],
        objective_key: str,
        *,
        reference_value: float | None = None,
        include_known_zero: bool = False,
    ) -> tuple[ExtremeSubclassSlotAllocationResult, ...] | None:
        """Rehydrate reviewed allocation scores from cached formulas.

        Returns None when this catalog cannot safely answer the requested line
        set. That is intentionally different from an empty tuple: None tells the
        caller to fall back to live canonical scoring, while () means a valid
        catalog handled the line set but this context has no resolved allocation.
        """
        if self.catalog is None:
            return None
        objective = str(objective_key or "").strip()
        lines = tuple(
            sorted(
                str(line or "").strip().casefold()
                for line in equipped_skill_lines
                if str(line or "").strip()
            )
        )
        if not objective or not lines:
            return ()

        line_key = "|".join(lines)
        formula_root = self.catalog.get("passive_allocation_formulas")
        if not isinstance(formula_root, dict):
            return None
        by_line_set = formula_root.get("by_line_set")
        if not isinstance(by_line_set, dict):
            return None
        rows = by_line_set.get(line_key)
        if not isinstance(rows, list):
            return None

        results: list[ExtremeSubclassSlotAllocationResult] = []
        for row in rows:
            if not isinstance(row, dict):
                return None
            slot_counts = self._parse_slot_counts(
                row.get("slot_counts"),
                expected_lines=lines,
            )
            if slot_counts is None:
                return None

            formulas = row.get("formulas")
            if not isinstance(formulas, list):
                return None
            if any(not isinstance(item, dict) for item in formulas):
                return None

            matching = [
                item
                for item in formulas
                if item.get("objective_key") == objective
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

            coefficients: list[tuple[dict[str, Any], float, float, float]] = []
            for item in matching:
                flat = self._numeric_formula_value(item, "flat")
                ratio = self._numeric_formula_value(item, "ratio")
                percent = self._numeric_formula_value(item, "percent_of_reference")
                if flat is None or ratio is None or percent is None:
                    return None
                sources = item.get("sources", ())
                if not isinstance(sources, (list, tuple)):
                    return None
                coefficients.append((item, flat, ratio, percent))

            if reference_value is None and any(percent != 0.0 for _, _, _, percent in coefficients):
                continue

            projected = 0.0
            sources: list[str] = []
            for item, flat, ratio, percent in coefficients:
                projected += flat
                projected += ratio
                projected += float(reference_value or 0.0) * percent
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
