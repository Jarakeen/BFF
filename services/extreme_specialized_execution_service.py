from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_bash_saved_build_record_service import (
    ExtremeBashSavedBuildRecordService,
)
from services.extreme_damage_shield_saved_build_record_service import (
    ExtremeDamageShieldSavedBuildRecordService,
)
from services.extreme_healing_event_record_service import (
    ExtremeHealingEventRecordService,
)
from services.extreme_invisibility_duration_record_service import (
    ExtremeInvisibilityDurationRecordService,
)
from services.extreme_invisibility_uptime_record_service import (
    ExtremeInvisibilityUptimeRecordService,
)
from services.extreme_movement_static_package_service import (
    ExtremeMovementStaticPackageService,
)
from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from services.extreme_saved_rotation_combat_record_service import (
    ExtremeSavedRotationCombatRecordService,
)
from services.extreme_saved_rotation_resource_record_service import (
    ExtremeSavedRotationResourceRecordService,
)
from services.extreme_stealth_source_package_service import (
    ExtremeStealthSourcePackageService,
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
    """One UI-facing gateway for non-static Extreme execution families."""

    _DIRECT_KEYS = frozenset(
        {
            "actual_heal",
            "critical_heal",
            "damage_shield",
            "bash_damage",
            "resource_sustain",
            "sustained_dps",
            "ultimate_generation",
            "movement_speed",
            "sprint_speed",
            "stealthed_movement_speed",
            "detection_radius_reduction",
            "invisibility_duration",
        }
    )
    _DURATION_INPUT_KEYS = frozenset({"invisibility_uptime"})
    _SAVED_BUILD_REQUIRED_KEYS = frozenset(
        {
            "actual_heal",
            "critical_heal",
            "damage_shield",
            "bash_damage",
            "resource_sustain",
            "ultimate_generation",
        }
    )

    _FAMILY_REQUIREMENTS = {
        "actual-heal-event": (),
        "single-event-output": (
            ExtremeSpecializedInputRequirement(
                "event_source",
                "Event Source",
                "canonical_candidate",
                note="Select/prove the legal event source before scoring.",
            ),
        ),
        "combat-simulation": (
            ExtremeSpecializedInputRequirement(
                "target_health",
                "Target Health",
                "integer",
                note="Explicit target maximum/current Health for the modeled comparison.",
            ),
            ExtremeSpecializedInputRequirement(
                "target_resistance",
                "Target Resistance",
                "rating",
                note="Explicit target resistance used by canonical DD damage evaluation.",
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
        "movement-state": (),
        "stealth-state": (),
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
    _OBJECTIVE_REQUIREMENTS = {
        "bash_damage": (),
        "damage_shield": (),
        # Saved RotationPlan artifacts own the explicit timeline/workload for the
        # two resource-timeline records. No second scenario editor is required.
        "resource_sustain": (),
        "sustained_dps": (
            ExtremeSpecializedInputRequirement(
                "target_health",
                "Target Health",
                "integer",
                note="Explicit target Health; no training-dummy Health is assumed.",
            ),
            ExtremeSpecializedInputRequirement(
                "target_resistance",
                "Target Resistance",
                "rating",
                note="Explicit target resistance; no dummy/boss armor is assumed.",
            ),
        ),
        "ultimate_generation": (),
        "invisibility_duration": (),
        "invisibility_uptime": (
            ExtremeSpecializedInputRequirement(
                "duration_seconds",
                "Duration",
                "seconds",
                note="Choose the comparison horizon for reviewed invisibility recurrence.",
            ),
        ),
    }

    def __init__(
        self,
        *,
        healing_events: ExtremeHealingEventRecordService | None = None,
        shield_record: ExtremeDamageShieldSavedBuildRecordService | None = None,
        bash_record: ExtremeBashSavedBuildRecordService | None = None,
        saved_rotation_resources: ExtremeSavedRotationResourceRecordService | None = None,
        saved_rotation_combat: ExtremeSavedRotationCombatRecordService | None = None,
        movement_package: ExtremeMovementStaticPackageService | None = None,
        stealth_package: ExtremeStealthSourcePackageService | None = None,
        invisibility_duration_record: ExtremeInvisibilityDurationRecordService | None = None,
        invisibility_uptime_record: ExtremeInvisibilityUptimeRecordService | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        self.healing_events = healing_events or ExtremeHealingEventRecordService()
        self.shield_record = shield_record or (
            ExtremeDamageShieldSavedBuildRecordService(database_path)
            if database_path is not None
            else None
        )
        self.bash_record = bash_record or (
            ExtremeBashSavedBuildRecordService(database_path)
            if database_path is not None
            else None
        )
        self.saved_rotation_resources = saved_rotation_resources or (
            ExtremeSavedRotationResourceRecordService(database_path)
            if database_path is not None
            else None
        )
        self.saved_rotation_combat = saved_rotation_combat or (
            ExtremeSavedRotationCombatRecordService(database_path)
            if database_path is not None
            else None
        )
        self.movement_package = movement_package or (
            ExtremeMovementStaticPackageService(database_path)
            if database_path is not None
            else None
        )
        self.stealth_package = stealth_package or (
            ExtremeStealthSourcePackageService(database_path)
            if database_path is not None
            else None
        )
        self.invisibility_duration_record = invisibility_duration_record or (
            ExtremeInvisibilityDurationRecordService(database_path)
            if database_path is not None
            else None
        )
        self.invisibility_uptime_record = invisibility_uptime_record or (
            ExtremeInvisibilityUptimeRecordService(database_path)
            if database_path is not None
            else None
        )

    @classmethod
    def requirements_for(cls, objective_key: str) -> tuple[ExtremeSpecializedInputRequirement, ...]:
        key = str(objective_key or "").strip().casefold()
        descriptor = ExtremeRecordExecutionCatalogService.descriptor(key)
        if descriptor.status is not ExtremeRecordExecutionStatus.SPECIALIZED:
            return ()
        if key in cls._OBJECTIVE_REQUIREMENTS:
            return cls._OBJECTIVE_REQUIREMENTS[key]
        try:
            return cls._FAMILY_REQUIREMENTS[descriptor.execution_family]
        except KeyError as exc:
            raise ValueError(
                f"No specialized input contract for Extreme family {descriptor.execution_family!r}"
            ) from exc

    @classmethod
    def can_execute_without_extra_inputs(cls, objective_key: str) -> bool:
        key = str(objective_key or "").strip().casefold()
        return key in cls._DIRECT_KEYS and not cls.requirements_for(key)

    @classmethod
    def can_execute_with_duration_input(cls, objective_key: str) -> bool:
        key = str(objective_key or "").strip().casefold()
        requirements = cls.requirements_for(key)
        return (
            key in cls._DURATION_INPUT_KEYS
            and len(requirements) == 1
            and requirements[0].key == "duration_seconds"
        )

    @classmethod
    def can_execute_with_combat_target_inputs(cls, objective_key: str) -> bool:
        key = str(objective_key or "").strip().casefold()
        requirements = cls.requirements_for(key)
        return tuple(row.key for row in requirements) == (
            "target_health",
            "target_resistance",
        )

    @classmethod
    def requires_saved_build(cls, objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() in cls._SAVED_BUILD_REQUIRED_KEYS

    def execute(
        self,
        build: PlayerBuild | None,
        objective_key: str,
        *,
        active_bar: str = "front",
        duration_seconds: float | None = None,
        target_health: int | None = None,
        target_resistance: float | None = None,
        target_name: str = "Boss",
    ) -> ExtremeSpecializedExecutionResult:
        key = str(objective_key or "").strip().casefold()
        descriptor = ExtremeRecordExecutionCatalogService.descriptor(key)
        if descriptor.status is not ExtremeRecordExecutionStatus.SPECIALIZED:
            raise ValueError(f"Extreme record is not specialized: {objective_key!r}")
        requirements = self.requirements_for(key)
        if requirements:
            provided = {
                "duration_seconds": duration_seconds,
                "target_health": target_health,
                "target_resistance": target_resistance,
            }
            missing = tuple(
                requirement.label
                for requirement in requirements
                if requirement.required and provided.get(requirement.key) is None
            )
            if missing:
                raise ValueError(
                    f"{descriptor.objective.label} requires family-specific scenario inputs before execution: "
                    + ", ".join(missing)
                )

        if key in {"actual_heal", "critical_heal"}:
            if build is None:
                raise ValueError(f"{descriptor.objective.label} requires a saved-build starting context")
            result = self.healing_events.evaluate(build, key, active_bar=active_bar)
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

        if key == "damage_shield":
            if build is None:
                raise ValueError(f"{descriptor.objective.label} requires a saved-build starting context")
            if self.shield_record is None:
                raise ValueError("Extreme damage-shield record requires a canonical database path")
            result = self.shield_record.evaluate(build, active_bar=active_bar)
            summary = [("Active bar", active_bar)]
            if result.skill_name:
                summary.append(("Shield skill", result.skill_name))
            if result.entity_id:
                summary.append(("Entity", result.entity_id))
            if result.value is not None:
                summary.append(("Reviewed shield lower bound", f"{result.value:,.0f}"))
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=result.value,
                value_text=None if result.value is None else f"{result.value:,.0f}",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        if key == "bash_damage":
            if build is None:
                raise ValueError(f"{descriptor.objective.label} requires a saved-build starting context")
            if self.bash_record is None:
                raise ValueError("Extreme Bash record requires a canonical database path")
            result = self.bash_record.evaluate(build, active_bar=active_bar)
            value = result.value
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=value,
                value_text=f"{value:,.0f}",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=(
                    ("Active bar", active_bar),
                    ("Reviewed Bash lower bound", f"{value:,.0f}"),
                ),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        if key == "sustained_dps":
            if build is None:
                raise ValueError(f"{descriptor.objective.label} requires a saved-build starting context")
            if target_health is None or target_resistance is None:
                raise ValueError(
                    f"{descriptor.objective.label} requires explicit target Health and resistance"
                )
            if self.saved_rotation_combat is None:
                raise ValueError("Extreme sustained-DPS record requires a canonical database path")
            result = self.saved_rotation_combat.sustained_dps(
                build,
                target_health=int(target_health),
                target_resistance=float(target_resistance),
                target_name=target_name,
            )
            record = result.record
            summary_rows: list[tuple[str, str]] = [
                ("Target Health", f"{int(target_health):,}"),
                ("Target Resistance", f"{float(target_resistance):g}"),
            ]
            value = None
            value_text = None
            if record is not None:
                value = record.modeled_dps
                value_text = f"{value:,.2f} DPS modeled saved-rotation lower bound"
                summary_rows.extend(
                    (
                        ("Executed horizon", f"{record.duration_seconds:g}s"),
                        ("Applied damage", f"{record.applied_damage:,.2f}"),
                        (
                            "Ending target Health",
                            "unknown"
                            if record.ending_target_health is None
                            else f"{record.ending_target_health:,}",
                        ),
                        ("Target dead", "YES" if record.target_dead else "NO"),
                    )
                )
                if record.killing_source:
                    summary_rows.append(("Killing source", record.killing_source))
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=value,
                value_text=value_text,
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary_rows),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        if key in {"resource_sustain", "ultimate_generation"}:
            if build is None:
                raise ValueError(f"{descriptor.objective.label} requires a saved-build starting context")
            if self.saved_rotation_resources is None:
                raise ValueError("Extreme saved-rotation resource records require a canonical database path")

            if key == "resource_sustain":
                result = self.saved_rotation_resources.resource_sustain(build)
                record = result.record
                summary: list[tuple[str, str]] = []
                if result.resource is not None:
                    summary.append(("Spent resource", result.resource.value.title()))
                if record is not None:
                    summary.extend(
                        (
                            ("Saved rotation horizon", f"{record.duration_seconds:g}s"),
                            ("Net resource", f"{record.net_resource:+d}"),
                            ("Net resource / second", f"{record.net_resource_per_second:+.2f}"),
                            ("Minimum amount", str(record.minimum_amount)),
                            ("Resolved cost events", str(result.action_cost_event_count)),
                        )
                    )
                    value = record.net_resource_per_second
                    value_text = f"{value:+.2f}/s reviewed saved-rotation lower bound"
                else:
                    value = None
                    value_text = None
                return ExtremeSpecializedExecutionResult(
                    objective_key=key,
                    label=descriptor.objective.label,
                    execution_family=descriptor.execution_family,
                    value=value,
                    value_text=value_text,
                    mechanic_complete=result.mechanic_complete,
                    global_maximum_proven=False,
                    summary_rows=tuple(summary),
                    unresolved=result.unresolved,
                    search_scope=result.evidence,
                    omitted_scope=result.unresolved,
                )

            result = self.saved_rotation_resources.ultimate_generation(build)
            record = result.record
            summary = []
            if record is not None:
                summary.extend(
                    (
                        ("Saved rotation horizon", f"{record.duration_seconds:g}s"),
                        ("Generated Ultimate", f"{record.total_generated:g}"),
                        ("Ultimate / second", f"{record.generated_per_second:.2f}"),
                        ("Generation events", str(record.event_count)),
                    )
                )
                value = record.generated_per_second
                value_text = f"{value:.2f}/s reviewed saved-rotation lower bound"
            else:
                value = None
                value_text = None
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=value,
                value_text=value_text,
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
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

        if key == "detection_radius_reduction":
            if self.stealth_package is None:
                raise ValueError("Extreme stealth package requires a canonical database path")
            result = self.stealth_package.evaluate()
            witness = result.realization
            summary: list[tuple[str, str]] = [
                ("Reviewed legal gear reduction", f"{result.reviewed_flat_reduction_meters:g} m"),
                ("Gear denominator proven", "YES" if result.gear_denominator_proven else "NO"),
            ]
            if witness is not None:
                summary.append(("Gear sets", ", ".join(witness.set_names)))
                summary.append(("Set counts", " + ".join(str(value) for value in witness.counts)))
                summary.append(("Weapon shape", witness.weapon_shape.value))
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=result.reviewed_flat_reduction_meters,
                value_text=f"{result.reviewed_flat_reduction_meters:g} m reviewed gear reduction",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        if key == "invisibility_duration":
            if self.invisibility_duration_record is None:
                raise ValueError("Extreme invisibility duration record requires a canonical database path")
            result = self.invisibility_duration_record.evaluate()
            summary: list[tuple[str, str]] = []
            if result.provider is not None:
                summary.append(("Reviewed provider", result.provider.name))
            if result.duration_seconds is not None:
                summary.append(("Reviewed contiguous duration", f"{result.duration_seconds:g}s"))
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=result.duration_seconds,
                value_text=(
                    None
                    if result.duration_seconds is None
                    else f"{result.duration_seconds:g}s reviewed lower bound"
                ),
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        if key == "invisibility_uptime":
            if duration_seconds is None:
                raise ValueError("MOST Invisibility Uptime requires a comparison duration")
            if self.invisibility_uptime_record is None:
                raise ValueError("Extreme invisibility uptime record requires a canonical database path")
            result = self.invisibility_uptime_record.evaluate(duration_seconds=duration_seconds)
            summary: list[tuple[str, str]] = [
                ("Comparison horizon", f"{result.duration_seconds:g}s"),
                ("Reviewed covered time", f"{result.covered_seconds:g}s"),
                ("Reviewed windows", str(result.window_count)),
            ]
            if result.provider is not None:
                summary.append(("Reviewed provider", result.provider.name))
            return ExtremeSpecializedExecutionResult(
                objective_key=key,
                label=descriptor.objective.label,
                execution_family=descriptor.execution_family,
                value=result.uptime_ratio,
                value_text=f"{result.uptime_ratio * 100.0:.1f}% reviewed lower bound",
                mechanic_complete=result.mechanic_complete,
                global_maximum_proven=False,
                summary_rows=tuple(summary),
                unresolved=result.unresolved,
                search_scope=result.evidence,
                omitted_scope=result.unresolved,
            )

        raise AssertionError(f"Unhandled specialized Extreme record: {key}")


__all__ = [
    "ExtremeSpecializedExecutionResult",
    "ExtremeSpecializedExecutionService",
    "ExtremeSpecializedInputRequirement",
]
