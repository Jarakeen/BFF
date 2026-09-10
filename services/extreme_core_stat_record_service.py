from __future__ import annotations

"""Canonical access to currently executable core Extreme stat records.

This service is the narrow bridge between the legacy/static Extreme optimizer
and the newer Extreme Records contract.  It deliberately exposes only objectives
that the static optimizer can execute today.  The resulting records remain
truthful lower bounds until the full legal-character denominator is proven.

Consumers such as Comp Maker should depend on this service/record contract rather
than importing the underlying optimizer and reproducing mechanics locally.
"""

from services.extreme_optimization_service import (
    EXTREME_OBJECTIVES,
    ExtremeOptimizationService,
)
from services.extreme_record_objective_catalog_service import (
    ExtremeRecordObjective,
    get_extreme_record_objective,
)
from services.extreme_record_result import ExtremeRecordResult
from services.extreme_static_optimization_record_adapter import (
    ExtremeStaticOptimizationRecordAdapter,
)


_EXECUTABLE_KEYS: tuple[str, ...] = tuple(objective.key for objective in EXTREME_OBJECTIVES)
_EXECUTABLE_KEY_SET = frozenset(_EXECUTABLE_KEYS)


class ExtremeCoreStatRecordService:
    """Execute bounded core-stat searches and return canonical record evidence."""

    def __init__(
        self,
        *,
        optimizer: ExtremeOptimizationService | None = None,
        adapter: ExtremeStaticOptimizationRecordAdapter | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeOptimizationService()
        self.adapter = adapter or ExtremeStaticOptimizationRecordAdapter()

    @staticmethod
    def supported_objectives() -> tuple[ExtremeRecordObjective, ...]:
        """Return executable record objectives in canonical optimizer order."""

        return tuple(get_extreme_record_objective(key) for key in _EXECUTABLE_KEYS)

    @staticmethod
    def supports(objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() in _EXECUTABLE_KEY_SET

    def record_for_build(
        self,
        baseline_build,
        objective_key: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeRecordResult:
        key = str(objective_key or "").strip().casefold()
        if key not in _EXECUTABLE_KEY_SET:
            # Resolve through the canonical catalog first so a typo is reported as
            # an unsupported record objective rather than as an optimizer detail.
            objective = get_extreme_record_objective(key)
            raise ValueError(
                f"Extreme Record objective {objective.key!r} is cataloged but is not "
                "yet executable by the core static stat optimizer"
            )

        result = self.optimizer.optimize(
            baseline_build,
            key,
            active_bar=active_bar,
            max_passes=max_passes,
        )
        record = self.adapter.adapt(result)
        if record.objective_key != key:
            raise ValueError(
                "Extreme core stat adapter returned mismatched objective: "
                f"requested {key!r}, received {record.objective_key!r}"
            )
        return record

    def records_for_build(
        self,
        baseline_build,
        *,
        objective_keys: tuple[str, ...] | None = None,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> tuple[ExtremeRecordResult, ...]:
        keys = _EXECUTABLE_KEYS if objective_keys is None else tuple(objective_keys)
        return tuple(
            self.record_for_build(
                baseline_build,
                key,
                active_bar=active_bar,
                max_passes=max_passes,
            )
            for key in keys
        )
