from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.resource_costs import ResourceType
from minmax.ultimate_generation_sources import CombatAttackUltimateGenerationSource
from models.build_model import PlayerBuild
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
)
from services.build_service import BuildService
from services.extreme_resource_timeline_record_service import (
    ExtremeResourceSustainRecord,
    ExtremeResourceTimelineRecordService,
    ExtremeUltimateGenerationRecord,
)
from services.rotation_sustain_service import RotationSustainService


@dataclass(frozen=True)
class ExtremeSavedRotationSustainResult:
    resource: ResourceType | None
    record: ExtremeResourceSustainRecord | None
    action_cost_event_count: int
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return self.record is not None and self.record.mechanic_complete and not self.unresolved


@dataclass(frozen=True)
class ExtremeSavedRotationUltimateResult:
    record: ExtremeUltimateGenerationRecord | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return self.record is not None and self.record.mechanic_complete and not self.unresolved


class ExtremeSavedRotationResourceRecordService:
    """Reuse canonical saved RotationPlan artifacts for the final timeline records.

    This is intentionally a lower-bound route, not a replacement for global
    Extreme search. Resource Sustain evaluates only primary resources the saved
    plan actually spends, preventing an unused resource from winning by doing
    nothing. Ultimate Generation uses the canonical successful-LA/HA combat source
    as an explicit constructive Extreme witness; broader Heroism/provider search
    remains visible as unresolved scope.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        artifact_service: BuildRotationArtifactService | None = None,
        catalog_service=None,
        sustain_service: RotationSustainService | None = None,
        combat_ultimate_source: CombatAttackUltimateGenerationSource | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        data_dir = self.database_path.parent
        self.artifact_service = artifact_service or BuildRotationArtifactService(
            data_dir / "build_rotations.json"
        )
        self.catalog_service = catalog_service or BuildService(
            data_dir / "builds.json"
        ).canonical.catalog_service
        self.sustain_service = sustain_service or RotationSustainService(
            self.database_path
        )
        self.combat_ultimate_source = (
            combat_ultimate_source or CombatAttackUltimateGenerationSource()
        )

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))

    def _plan_for(self, build: PlayerBuild):
        build_id = resolve_canonical_build_id(self.catalog_service, build)
        if not build_id:
            return None, (
                "Selected build could not be resolved to one canonical build_id for saved-rotation ownership",
            )
        plan = self.artifact_service.get_rotation_plan(build_id)
        if plan is None:
            return None, (
                f"Selected build has no saved canonical RotationPlan artifact ({build_id})",
            )
        return plan, ()

    def resource_sustain(self, build: PlayerBuild) -> ExtremeSavedRotationSustainResult:
        plan, plan_unresolved = self._plan_for(build)
        if plan is None:
            return ExtremeSavedRotationSustainResult(
                resource=None,
                record=None,
                action_cost_event_count=0,
                evidence=(),
                unresolved=plan_unresolved,
            )

        candidates = []
        projection_unresolved: list[str] = list(plan.unresolved)
        for resource in (ResourceType.MAGICKA, ResourceType.STAMINA):
            projection = self.sustain_service.evaluate(
                build=build,
                plan=plan,
                resource=resource,
            )
            projection_unresolved.extend(projection.unresolved)
            action_count = len(projection.run.action_cost_events)
            if action_count <= 0:
                continue
            record = ExtremeResourceTimelineRecordService.resource_sustain(
                projection.run.sustain,
                duration_seconds=plan.duration_seconds,
                unresolved=projection.unresolved,
            )
            candidates.append((record.net_resource_per_second, resource.value, resource, record, action_count))

        if not candidates:
            return ExtremeSavedRotationSustainResult(
                resource=None,
                record=None,
                action_cost_event_count=0,
                evidence=(
                    f"Saved rotation horizon: {plan.duration_seconds:g}s",
                ),
                unresolved=self._dedupe(
                    (*projection_unresolved, "Saved rotation spends no resolved Magicka or Stamina actions")
                ),
            )

        _score, _name, resource, record, action_count = max(candidates, key=lambda row: (row[0], row[1]))
        evidence = (
            f"Saved canonical rotation horizon: {plan.duration_seconds:g}s",
            f"Selected spent resource branch: {resource.value}",
            f"Resolved {action_count} {resource.value} action-cost events through Phase 4 sustain",
            "Unused primary-resource branches are not eligible to win by doing nothing",
        )
        unresolved = self._dedupe(
            (
                *record.unresolved,
                "Global Extreme sustain search across alternate legal rotations/builds remains open",
            )
        )
        return ExtremeSavedRotationSustainResult(
            resource=resource,
            record=record,
            action_cost_event_count=action_count,
            evidence=evidence,
            unresolved=unresolved,
        )

    def ultimate_generation(self, build: PlayerBuild) -> ExtremeSavedRotationUltimateResult:
        plan, plan_unresolved = self._plan_for(build)
        if plan is None:
            return ExtremeSavedRotationUltimateResult(
                record=None,
                evidence=(),
                unresolved=plan_unresolved,
            )

        events = self.combat_ultimate_source.events_from_plan(
            plan=plan,
            assume_scheduled_attacks_damage=True,
        )
        record = ExtremeResourceTimelineRecordService.ultimate_generation(
            events,
            duration_seconds=plan.duration_seconds,
            unresolved=tuple(plan.unresolved),
        )
        evidence = (
            f"Saved canonical rotation horizon: {plan.duration_seconds:g}s",
            f"Canonical base-combat Ultimate events from scheduled LA/HA triggers: {len(events)}",
            "Constructive Extreme witness treats scheduled light/heavy attacks as successful damaging triggers",
        )
        unresolved = self._dedupe(
            (
                *record.unresolved,
                "Heroism and other legal Ultimate-generation provider search remains open",
                "Global Extreme generation search across alternate legal rotations/builds remains open",
            )
        )
        return ExtremeSavedRotationUltimateResult(
            record=record,
            evidence=evidence,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSavedRotationResourceRecordService",
    "ExtremeSavedRotationSustainResult",
    "ExtremeSavedRotationUltimateResult",
]
