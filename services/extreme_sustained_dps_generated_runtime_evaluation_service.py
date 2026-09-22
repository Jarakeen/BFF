from __future__ import annotations

"""Exact generated sustained-DPS evaluation with bar-legal gear runtime evidence.

This service reuses the saved-build DD Combat Simulation stack but replaces saved-build
progression lookup with one explicit generated-candidate progression witness. Verified
named gear buffs may flow through the shared runtime CombatState path. Active non-named
gear effects remain explicit blockers until a generic timed-effect -> build-context
bridge exists.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from minmax.gear_set_repository import GearSetRepository
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationTargetState,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
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
from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationEvidenceService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibilityService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateResult,
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.extreme_saved_rotation_combat_record_service import (
    ExtremeSustainedDPSRecord,
)
from services.extreme_sustained_dps_runtime_effect_projection_service import (
    ExtremeSustainedDPSRuntimeEffectProjectionService,
)
from services.minmax_character_progression_adapter import (
    SavedBuildProgressionResolution,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextService,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextService,
)


_DD_ROLE_KEYS = {"dd", "dps", "damage", "damage dealer", "damage_dealer"}


class ExtremeSustainedDPSExplicitProgressionAdapter:
    """Expose caller-owned generated progression through the saved-context contract."""

    def __init__(
        self,
        progression: CharacterProgression,
        *,
        character_id: str = "generated-sustained-dps-candidate",
    ) -> None:
        self.progression = progression
        self.character_id = str(character_id or "").strip() or "generated-sustained-dps-candidate"

    def resolve(self, build: PlayerBuild) -> SavedBuildProgressionResolution:
        progression = replace(
            self.progression,
            attributes=AttributeAllocation(
                health=int(getattr(build, "AttributeHealth", 0) or 0),
                magicka=int(getattr(build, "AttributeMagicka", 0) or 0),
                stamina=int(getattr(build, "AttributeStamina", 0) or 0),
            ),
        )
        return SavedBuildProgressionResolution(
            character_id=self.character_id,
            progression=progression,
        )


class _GearBoundRuntimeSnapshotState:
    """Inject dual-bar gear activation into the shared runtime projector."""

    def __init__(
        self,
        *,
        delegate: ExtremeRuntimeSnapshotCombatStateService,
        activation: ExtremeDualBarSetActivationEvidenceCatalog,
    ) -> None:
        self.delegate = delegate
        self.activation = activation
    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        active_bar: str,
        snapshot: ExtremeRuntimeSnapshot,
        base_combat_state: CombatState | None = None,
        base_active_buffs: tuple[str, ...] = (),
    ) -> ExtremeRuntimeSnapshotCombatStateResult:
        projected = self.delegate.resolve(
            build,
            progression=progression,
            active_bar=active_bar,
            snapshot=snapshot,
            gear_activation=self.activation,
            base_combat_state=base_combat_state,
            base_active_buffs=base_active_buffs,
        )
        return projected


@dataclass(frozen=True)
class ExtremeGeneratedSustainedDPSRuntimeResult:
    record: ExtremeSustainedDPSRecord | None
    summary: CombatSimulationDamageSummary | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.record is not None
            and self.summary is not None
            and self.summary.complete_damage_evidence
            and not self.unresolved
        )


class ExtremeSustainedDPSGeneratedRuntimeEvaluationService:
    """Evaluate one explicit generated DD build/gear/rotation/runtime witness."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        activation_service: ExtremeDualBarSetActivationEvidenceService | None = None,
        summary_service: CombatSimulationDamageSummaryService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        repository = GearSetRepository(self.database_path)
        eligibility = ExtremeNamedGearSetSlotEligibilityService(self.database_path).build()
        self.activation_service = activation_service or ExtremeDualBarSetActivationEvidenceService(
            repository=repository,
            eligibility=eligibility,
        )
        self.summary_service = summary_service or CombatSimulationDamageSummaryService()

    @staticmethod
    def _role_is_dd(build: PlayerBuild) -> bool:
        role = " ".join(
            str(getattr(build, "Role", "") or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .split()
        )
        return role in _DD_ROLE_KEYS

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    def evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        gear_state: ExtremeDualBarGearState,
        plan: RotationPlan,
        runtime_snapshot: ExtremeRuntimeSnapshot,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
    ) -> ExtremeGeneratedSustainedDPSRuntimeResult:
        if not self._role_is_dd(build):
            return ExtremeGeneratedSustainedDPSRuntimeResult(
                record=None,
                summary=None,
                evidence=(),
                unresolved=("Generated sustained-DPS runtime evaluation requires a DD/DPS build",),
            )
        if (
            not runtime_snapshot.runtime_history
            and not runtime_snapshot.runtime_history_complete
        ):
            return ExtremeGeneratedSustainedDPSRuntimeResult(
                record=None,
                summary=None,
                evidence=(),
                unresolved=(
                    "Generated sustained-DPS runtime evaluation requires authoritative runtime_history",
                ),
            )
        if int(target_health) <= 0:
            raise ValueError("generated sustained-DPS target_health must be positive")
        if float(target_resistance) < 0.0:
            raise ValueError("generated sustained-DPS target_resistance cannot be negative")

        candidate_build = ExtremeDualBarGearStateService.materialize(build, gear_state)
        activation = self.activation_service.build(gear_state, build=build)
        if activation.unresolved:
            return ExtremeGeneratedSustainedDPSRuntimeResult(
                record=None,
                summary=None,
                evidence=(),
                unresolved=self._dedupe(activation.unresolved),
            )

        explicit_progression = ExtremeSustainedDPSExplicitProgressionAdapter(progression)
        static_context_service = RotationStaticBuildContextService(
            database_path=self.database_path,
            progression_adapter=explicit_progression,
        )
        runtime_snapshot_state = _GearBoundRuntimeSnapshotState(
            delegate=ExtremeRuntimeSnapshotCombatStateService(self.database_path),
            activation=activation,
        )
        runtime_combat_state = RotationPlanRuntimeCombatStateService(
            runtime_snapshot_state=runtime_snapshot_state,
        )

        effective_progression = explicit_progression.resolve(candidate_build).progression

        def runtime_combat_state_resolver(time_seconds: float, sequence: int | None = None):
            return runtime_combat_state.resolve(
                candidate_build,
                progression=effective_progression,
                plan=plan,
                runtime_snapshot_source=runtime_snapshot,
                time_seconds=time_seconds,
                sequence=sequence,
                initial_bar=initial_bar,
            )

        runtime_build_context = RotationPlanRuntimeBuildContextService(
            static_context_service=static_context_service,
            runtime_effect_projector=ExtremeSustainedDPSRuntimeEffectProjectionService,
        )

        def runtime_build_context_resolver(time_seconds: float, sequence: int | None = None):
            return runtime_build_context.resolve(
                candidate_build,
                runtime_combat_state_resolver=runtime_combat_state_resolver,
                time_seconds=time_seconds,
                sequence=sequence,
            )

        simulator = CombatSimulationSavedBuildDDService(
            provider_service=CombatSimulationSavedBuildDDProviderService(
                database_path=self.database_path,
                static_context_service=static_context_service,
            )
        )
        target = str(target_name or "").strip() or "Boss"
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
        result = simulator.simulate(
            build_snapshot=EffectiveBuildSnapshot.from_candidate_build(
                candidate_build,
                provenance=(
                    "generated sustained-DPS dual-bar gear witness",
                    "explicit generated CharacterProgression",
                    "authoritative runtime history",
                ),
            ),
            plan=plan,
            target_state=target_state,
            damage_target_identity=target,
            target_resistance=float(target_resistance),
            initial_bar=initial_bar,
            runtime_build_context_resolver=runtime_build_context_resolver,
        )
        summary = self.summary_service.summarize(result, target_identity=target)
        unresolved = self._dedupe((*summary.unresolved, *summary.damage_unresolved))
        evidence = (
            f"Generated candidate rotation horizon: {plan.duration_seconds:g}s",
            f"Explicit target Health: {int(target_health)}",
            f"Explicit target resistance: {float(target_resistance):g}",
            "Dual-bar named-set activation bound into shared runtime snapshot truth",
            "Named buffs and reviewed timed non-named runtime stat effects may alter exact runtime build contexts",
            "Damage evaluated through Phase 14 Combat Simulation using candidate_build provenance",
        )
        if summary.modeled_dps is None:
            return ExtremeGeneratedSustainedDPSRuntimeResult(
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
        return ExtremeGeneratedSustainedDPSRuntimeResult(
            record=record,
            summary=summary,
            evidence=evidence,
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeGeneratedSustainedDPSRuntimeResult",
    "ExtremeSustainedDPSExplicitProgressionAdapter",
    "ExtremeSustainedDPSGeneratedRuntimeEvaluationService",
]
