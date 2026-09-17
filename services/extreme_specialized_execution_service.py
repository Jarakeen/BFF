from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_healing_event_record_service import (
    ExtremeHealingEventRecordService,
)
from services.extreme_movement_static_package_service import (
    ExtremeMovementStaticPackageService,
)
from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)


@dataclass(frozen=True)
class ExtremeSpecializedInputRequirement:
    key: str
    label: str
    kind: str
    required: bool = True
    note: str = ""


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
    value_text: str | None = None


class ExtremeSpecializedExecutionService:
    """One UI-facing gateway for non-static Extreme execution families.

    Family services remain authoritative for ESO mechanics. This class normalizes
    their outputs and owns one family-input registry so the Extreme Build Lab does
    not grow separate ad-hoc forms and execution branches for every record.
    """

    _DIRECT_KEYS = frozenset(
        {
            "actual_heal",
            "critical_heal",
            "movement_speed",
            "sprint_speed",
            "stealthed_movement_speed",
        }
    )

    _FAMILY_REQUIREMENTS = {
        "actual-heal-event": (),
        "single-event-output": (
            ExtremeSpecializedInputRequirement(
                "event_source",
                "Event Source",
                "canonical_candidate",
                note="Select/prove the legal Bash or damage-shield event source before scoring.",
            ),
        ),
        "resource-timeline": (
            ExtremeSpecializedInputRequirement(
                "duration_seconds",
                "Duration",
                "seconds",
                note="Sustained records require an explicit comparison window.",
            ),
            ExtremeSpecializedInputRequirement(
                "timeline_evidence",
                "Timeline Evidence",
                "canonical_timeline",
                note="Reuse Phase 4 resource events or explicit Ultimate generation events.",
            ),
        ),
        # Reviewed build-owned movement sources can now produce a lower-bound
        # record without asking the user to manually enter stat buckets. Missing
        # runtime/provider families remain unresolved evidence in the result.
        "movement-state": (),
        "stealth-state": (
            ExtremeSpecializedInputRequirement(
                "stealth_sources",
                "Stealth Sources",
                "canonical_state",
                note="Aggregate reviewed flat and multiplicative detection-radius reductions.",
            ),
        ),
        "stealth-runtime": (
            ExtremeSpecializedInputRequirement(
                "duration_seconds",
                "Duration",
                "seconds",
                note="Uptime is only meaningful over an explicit comparison window.",
            ),
            ExtremeSpecializedInputRequirement(
                "invisibility_windows",
                "Invisibility Windows",
                "canonical_intervals",
                note="Intervals must come from proven legal invisibility providers; do not infer tooltip durations here.",
            ),
        ),
    }

    def __init__(
        self,
        *,
        healing_events: ExtremeHealingEventRecordService | None = None,
        movement_package: ExtremeMovementStaticPackageService | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        self.healing_events = healing_events or ExtremeHealingEventRecordService()
        self.movement_package = movement_package or (
            ExtremeMovementStaticPackageService(database_path)
            if database_path is not None
            else None
        )

    @classmethod
    def requirements_for(cls, objective_key: str) -> tuple[ExtremeSpecializedInputRequirement, ...]:
        descriptor = ExtremeRecordExecutionCatalogService.descriptor(objective_key)
        if descriptor.status is not ExtremeRecordExecutionStatus.SPECIALIZED:
            return ()
        try:
            return cls._FAMILY_REQUIREMENTS[descriptor.execution_family]
        except KeyError as exc:
            raise ValueError(
                f"No specialized input contract for Extreme family {descriptor.execution_family!r}"
            ) from exc

    @classmethod
    def can_execute_without_extra_inputs(cls, objective_key: str) -> bool:
        key = str(objective_key or "").strip().casefold()
        if key not in cls._DIRECT_KEYS:
            return False
        return not cls.requirements_for(key)

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
        requirements = self.requirements_for(key)
        if requirements:
            labels = ", ".join(requirement.label for requirement in requirements if requirement.required)
            raise ValueError(
                f"{descriptor.objective.label} requires family-specific scenario inputs before execution: {labels}"
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

            value = result.best_scored_value
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=value,
                value_text=None if value is None else f"{value:,.0f}",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=result.global_maximum_proven,
                summary_rows=tuple(summary),
                unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
                search_scope=tuple(catalog.search_scope),
                omitted_scope=tuple(catalog.omitted_scope),
            )

        if key in {"movement_speed", "sprint_speed", "stealthed_movement_speed"}:
            if self.movement_package is None:
                raise ValueError("Extreme movement package requires a canonical database path")
            result = self.movement_package.evaluate(key)
            state = result.result
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=state.raw_multiplier,
                value_text=f"{state.raw_multiplier * 100.0:.1f}%",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=(
                    ("Reviewed raw speed", f"{state.raw_multiplier * 100.0:.1f}%"),
                    ("Effective speed", f"{state.effective_multiplier * 100.0:.1f}%"),
                    ("Effective cap", f"{state.effective_cap_multiplier * 100.0:.0f}%"),
                ),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        raise AssertionError(f"Unhandled zero-input specialized Extreme record: {key}")


__all__ = [
    "ExtremeSpecializedExecutionResult",
    "ExtremeSpecializedExecutionService",
    "ExtremeSpecializedInputRequirement",
]
