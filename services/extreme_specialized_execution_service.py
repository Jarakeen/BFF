from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_healing_event_record_service import (
    ExtremeHealingEventRecordService,
)
from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)


@dataclass(frozen=True)
class ExtremeSpecializedExecutionResult:
    objective_key: str
    label: str
    execution_family: str
    value: float | None
    mechanic_complete: bool
    global_maximum_proven: bool
    summary_rows: tuple[tuple[str, str], ...]
    unresolved: tuple[str, ...]
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]


class ExtremeSpecializedExecutionService:
    """One UI-facing gateway for non-static Extreme execution families.

    Family services remain authoritative for ESO mechanics.  This class only
    normalizes their outputs into one presentation contract so the Extreme Build
    Lab does not grow one page-specific execution path per record.

    Healing-event records are the first zero-extra-input specialized family: the
    selected saved build and active bar are sufficient to run their existing H1
    class-route search. Other specialized families remain explicit until their
    required scenario/source inputs are supplied by the page.
    """

    _DIRECT_KEYS = frozenset({"actual_heal", "critical_heal"})

    def __init__(
        self,
        *,
        healing_events: ExtremeHealingEventRecordService | None = None,
    ) -> None:
        self.healing_events = healing_events or ExtremeHealingEventRecordService()

    @classmethod
    def can_execute_without_extra_inputs(cls, objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() in cls._DIRECT_KEYS

    def execute(
        self,
        build: PlayerBuild,
        objective_key: str,
        *,
        active_bar: str = "front",
    ) -> ExtremeSpecializedExecutionResult:
        key = str(objective_key or "").strip().casefold()
        descriptor = ExtremeRecordExecutionCatalogService.descriptor(key)
        if descriptor.status is not ExtremeRecordExecutionStatus.SPECIALIZED:
            raise ValueError(f"Extreme record is not specialized: {objective_key!r}")
        if key not in self._DIRECT_KEYS:
            raise ValueError(
                f"{descriptor.objective.label} requires family-specific scenario inputs before execution"
            )

        if key in {"actual_heal", "critical_heal"}:
            result = self.healing_events.evaluate(
                build,
                key,
                active_bar=active_bar,
            )
            catalog = result.catalog
            winner = catalog.best_scored
            unresolved: list[str] = []
            summary: list[tuple[str, str]] = []
            if winner is not None:
                summary.extend(
                    (
                        ("Heal", winner.candidate.name),
                        ("Class", winner.route.base_class.value.title()),
                        ("Class lines", ", ".join(winner.route.equipped_skill_lines)),
                        ("Bar slot", str(winner.slotted_index + 1)),
                    )
                )
                unresolved.extend(winner.unresolved)
            else:
                unresolved.append("No scored legal healing-event candidate was produced")

            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=result.best_scored_value,
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=result.global_maximum_proven,
                summary_rows=tuple(summary),
                unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
                search_scope=tuple(catalog.search_scope),
                omitted_scope=tuple(catalog.omitted_scope),
            )

        raise AssertionError(f"Unhandled direct specialized Extreme record: {key}")


__all__ = [
    "ExtremeSpecializedExecutionResult",
    "ExtremeSpecializedExecutionService",
]
