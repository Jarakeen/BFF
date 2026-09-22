from __future__ import annotations

"""Adapt generated dynamic plan choices into canonical whole-plan DPS evidence."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, TypeVar

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_progression import CharacterProgression
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSWholePlanEvaluation,
)
from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
    ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
)


T = TypeVar("T")


@dataclass(frozen=True)
class ExtremeSustainedDPSWholePlanRuntimeScenario:
    build: PlayerBuild
    progression: CharacterProgression
    gear_state: ExtremeDualBarGearState
    runtime_snapshot: ExtremeRuntimeSnapshot
    target_health: int
    target_resistance: float
    target_name: str = "Boss"
    runtime_effects: tuple[EffectVariant, ...] = ()

    def __post_init__(self) -> None:
        if int(self.target_health) <= 0:
            raise ValueError("whole-plan runtime scenario target_health must be positive")
        if float(self.target_resistance) < 0.0:
            raise ValueError("whole-plan runtime scenario target_resistance cannot be negative")
        object.__setattr__(self, "target_health", int(self.target_health))
        object.__setattr__(self, "target_resistance", float(self.target_resistance))
        object.__setattr__(self, "target_name", str(self.target_name or "").strip() or "Boss")
        object.__setattr__(self, "runtime_effects", tuple(self.runtime_effects))


class ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator(Generic[T]):
    def __init__(
        self,
        *,
        runtime_service: ExtremeSustainedDPSGeneratedRuntimeEvaluationService,
        scenario: ExtremeSustainedDPSWholePlanRuntimeScenario,
        choice_id_resolver: Callable[[T], str],
        plan_resolver: Callable[[T], RotationPlan],
        initial_bar_resolver: Callable[[T], str],
    ) -> None:
        self.runtime_service = runtime_service
        self.scenario = scenario
        self.choice_id_resolver = choice_id_resolver
        self.plan_resolver = plan_resolver
        self.initial_bar_resolver = initial_bar_resolver

    def evaluate(self, choice: T) -> ExtremeSustainedDPSWholePlanEvaluation:
        choice_id = str(self.choice_id_resolver(choice) or "").strip()
        if not choice_id:
            raise ValueError("generated whole-plan choice evaluator requires stable choice identity")

        plan = self.plan_resolver(choice)
        initial_bar = str(self.initial_bar_resolver(choice) or "").strip().casefold()
        if initial_bar not in {"front", "back"}:
            raise ValueError(
                f"generated whole-plan choice {choice_id!r} has invalid initial bar {initial_bar!r}"
            )

        result = self.runtime_service.evaluate(
            self.scenario.build,
            progression=self.scenario.progression,
            gear_state=self.scenario.gear_state,
            plan=plan,
            runtime_snapshot=self.scenario.runtime_snapshot,
            runtime_effects=tuple(getattr(self.scenario, "runtime_effects", ())),
            target_health=self.scenario.target_health,
            target_resistance=self.scenario.target_resistance,
            target_name=self.scenario.target_name,
            initial_bar=initial_bar,
        )

        return ExtremeSustainedDPSWholePlanEvaluation(
            choice_id=choice_id,
            modeled_dps=(
                None if result.record is None else float(result.record.modeled_dps)
            ),
            duration_seconds=(
                None if result.record is None else float(result.record.duration_seconds)
            ),
            mechanic_complete=bool(result.mechanic_complete),
            unresolved=tuple(result.unresolved),
        )


class ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluatorService:
    """Build fixed-witness whole-plan evaluators without owning combat mechanics."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        scenario: ExtremeSustainedDPSWholePlanRuntimeScenario,
        runtime_service: ExtremeSustainedDPSGeneratedRuntimeEvaluationService | None = None,
    ) -> None:
        self.runtime_service = (
            runtime_service
            or ExtremeSustainedDPSGeneratedRuntimeEvaluationService(database_path)
        )
        self.scenario = scenario

    def evaluator(
        self,
        *,
        choice_id_resolver: Callable[[T], str],
        plan_resolver: Callable[[T], RotationPlan],
        initial_bar_resolver: Callable[[T], str],
    ) -> ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator[T]:
        return ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator(
            runtime_service=self.runtime_service,
            scenario=self.scenario,
            choice_id_resolver=choice_id_resolver,
            plan_resolver=plan_resolver,
            initial_bar_resolver=initial_bar_resolver,
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator",
    "ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluatorService",
    "ExtremeSustainedDPSWholePlanRuntimeScenario",
]
