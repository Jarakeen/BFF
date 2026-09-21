from __future__ import annotations

"""Saved-build sustained-DPS records backed by Phase 14 Combat Simulation.

This service is an Extreme/Optimization consumer of Combat Simulation. It does
not choose builds, rotations, targets, or target assumptions. It evaluates one
explicit saved build + saved RotationPlan witness and returns a constructive
sustained-DPS lower bound when damage evidence is complete.
"""

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationTargetState,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
)
from services.build_service import BuildService
from services.combat_simulation_damage_summary_service import (
    CombatSimulationDamageSummary,
    CombatSimulationDamageSummaryService,
)
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
)
from services.combat_simulation_saved_build_dd_service import (
    CombatSimulationSavedBuildDDService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextService,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


@dataclass(frozen=True)
class ExtremeSustainedDPSRecord:
    duration_seconds: float
    modeled_dps: float
    attempted_damage: float
    applied_damage: float
    total_overkill: float
    ending_target_health: int | None
    target_dead: bool
    killing_source: str | None
    damage_complete: bool = True


@dataclass(frozen=True)
class ExtremeSavedRotationSustainedDPSResult:
    record: ExtremeSustainedDPSRecord | None
    summary: CombatSimulationDamageSummary | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.record is not None
            and self.record.damage_complete
            and self.summary is not None
            and self.summary.complete_damage_evidence
            and not self.unresolved
        )


class ExtremeSavedRotationCombatRecordService:
    """Evaluate one saved DD build/rotation through canonical Combat Simulation."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        artifact_service: BuildRotationArtifactService | None = None,
        catalog_service=None,
        simulator: CombatSimulationSavedBuildDDService | None = None,
        summary_service: CombatSimulationDamageSummaryService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        data_dir = self.database_path.parent
        self.artifact_service = artifact_service or BuildRotationArtifactService(
            data_dir / "build_rotations.json"
        )
        self.catalog_service = catalog_service or BuildService(
            data_dir / "builds.json"
        ).canonical.catalog_service
        self.simulator = simulator or CombatSimulationSavedBuildDDService(
            provider_service=CombatSimulationSavedBuildDDProviderService(
                database_path=self.database_path,
                static_context_service=RotationStaticBuildContextService(
                    database_path=self.database_path,
                    builds_path=data_dir / "builds.json",
                ),
            )
        )
        self.summary_service = summary_service or CombatSimulationDamageSummaryService()

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

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

    @staticmethod
    def _dd_role(build: PlayerBuild) -> bool:
        role = " ".join(
            str(getattr(build, "Role", "") or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .split()
        )
        return role in _DD_ROLE_KEYS

    def sustained_dps(
        self,
        build: PlayerBuild,
        *,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
    ) -> ExtremeSavedRotationSustainedDPSResult:
        if not self._dd_role(build):
            return ExtremeSavedRotationSustainedDPSResult(
                record=None,
                summary=None,
                evidence=(),
                unresolved=(
                    "MOST Sustained DPS requires a saved DD/DPS build",
                ),
            )
        if int(target_health) <= 0:
            raise ValueError("sustained DPS target_health must be positive")
        if float(target_resistance) < 0:
            raise ValueError("sustained DPS target_resistance cannot be negative")
        target = str(target_name or "").strip() or "Boss"

        plan, plan_unresolved = self._plan_for(build)
        if plan is None:
            return ExtremeSavedRotationSustainedDPSResult(
                record=None,
                summary=None,
                evidence=(),
                unresolved=plan_unresolved,
            )

        target_state = CombatSimulationTargetState(
            combatants=(
                CombatSimulationCombatant(
                    target,
                    "enemy",
                    current_health=int(target_health),
                    maximum_health=int(target_health),
                ),
            ),
        )
        result = self.simulator.simulate(
            build_snapshot=EffectiveBuildSnapshot.from_saved_build(build),
            plan=plan,
            target_state=target_state,
            damage_target_identity=target,
            target_resistance=float(target_resistance),
        )
        summary = self.summary_service.summarize(
            result,
            target_identity=target,
        )

        evidence = (
            f"Saved canonical rotation horizon: {plan.duration_seconds:g}s",
            f"Explicit target Health: {int(target_health)}",
            f"Explicit target resistance: {float(target_resistance):g}",
            "Damage evaluated through Phase 14 saved-build DD Combat Simulation",
        )
        unresolved = self._dedupe(
            (
                *summary.unresolved,
                *summary.damage_unresolved,
                "Global Extreme sustained-DPS search across alternate legal builds/rotations remains open",
            )
        )
        if summary.modeled_dps is None:
            return ExtremeSavedRotationSustainedDPSResult(
                record=None,
                summary=summary,
                evidence=evidence,
                unresolved=unresolved,
            )

        record = ExtremeSustainedDPSRecord(
            duration_seconds=float(summary.duration_seconds),
            modeled_dps=float(summary.modeled_dps),
            attempted_damage=float(summary.attempted_damage),
            applied_damage=float(summary.applied_damage),
            total_overkill=float(summary.total_overkill),
            ending_target_health=summary.ending_target_health,
            target_dead=bool(summary.target_dead),
            killing_source=summary.killing_source,
            damage_complete=summary.complete_damage_evidence,
        )
        return ExtremeSavedRotationSustainedDPSResult(
            record=record,
            summary=summary,
            evidence=evidence,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSavedRotationCombatRecordService",
    "ExtremeSavedRotationSustainedDPSResult",
    "ExtremeSustainedDPSRecord",
]
