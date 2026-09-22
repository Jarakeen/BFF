from __future__ import annotations

"""Whole-plan sustained-DPS evaluation over explicit finite runtime-state choices."""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSWholePlanEvaluation,
)
from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
    ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeStateEvaluationScenario:
    build: PlayerBuild
    progression: CharacterProgression
    gear_state: ExtremeDualBarGearState
    plan: RotationPlan
    target_health: int
    target_resistance: float
    target_name: str = "Boss"
    initial_bar: str = "front"

    def __post_init__(self) -> None:
        if int(self.target_health) <= 0:
            raise ValueError("runtime-state scenario target_health must be positive")
        if float(self.target_resistance) < 0.0:
            raise ValueError("runtime-state scenario target_resistance cannot be negative")
        bar = str(self.initial_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("runtime-state scenario initial_bar must be front or back")
        object.__setattr__(self, "target_health", int(self.target_health))
        object.__setattr__(self, "target_resistance", float(self.target_resistance))
        object.__setattr__(self, "target_name", str(self.target_name or "").strip() or "Boss")
        object.__setattr__(self, "initial_bar", bar)


class ExtremeSustainedDPSRuntimeStateWholePlanEvaluator:
    """Vary only runtime truth while every other modeled witness dimension stays fixed."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        scenario: ExtremeSustainedDPSRuntimeStateEvaluationScenario,
        runtime_service: ExtremeSustainedDPSGeneratedRuntimeEvaluationService | None = None,
    ) -> None:
        self.scenario = scenario
        self.runtime_service = (
            runtime_service
            or ExtremeSustainedDPSGeneratedRuntimeEvaluationService(database_path)
        )

    def evaluate(
        self,
        choice: ExtremeSustainedDPSRuntimeStateChoice,
    ) -> ExtremeSustainedDPSWholePlanEvaluation:
        result = self.runtime_service.evaluate(
            self.scenario.build,
            progression=self.scenario.progression,
            gear_state=self.scenario.gear_state,
            plan=self.scenario.plan,
            runtime_snapshot=choice.snapshot,
            runtime_effects=tuple(choice.effects),
            target_health=self.scenario.target_health,
            target_resistance=self.scenario.target_resistance,
            target_name=self.scenario.target_name,
            initial_bar=self.scenario.initial_bar,
        )

        record = result.record
        return ExtremeSustainedDPSWholePlanEvaluation(
            choice_id=choice.runtime_state_id,
            modeled_dps=(None if record is None else float(record.modeled_dps)),
            duration_seconds=(
                None if record is None else float(record.duration_seconds)
            ),
            mechanic_complete=bool(result.mechanic_complete and not choice.unresolved),
            unresolved=tuple(
                dict.fromkeys(
                    (
                        *choice.unresolved,
                        *result.unresolved,
                    )
                )
            ),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeStateEvaluationScenario",
    "ExtremeSustainedDPSRuntimeStateWholePlanEvaluator",
]
