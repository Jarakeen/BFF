from __future__ import annotations

"""Canonical exact-action occurrence evaluation for generated finite-axis choices.

This service adapts CP, passive-rank, and dual-bar gear candidate payloads onto one
fixed generated witness, then delegates exact action consequence resolution to
CombatSimulationSavedBuildDDProviderService. It owns no ESO damage formulas.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.rotation_plan import RotationAction, RotationPlan
from models.build_model import PlayerBuild
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
)
from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointCandidate,
)
from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
    ExtremeSustainedDPSExplicitProgressionAdapter,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankCandidate,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrenceEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSExactActionScenario:
    plan: RotationPlan
    action_time_seconds: float
    action_sequence: int
    target_resistance: float
    initial_bar: str = "front"
    execute_target_identity: str = ""

    def __post_init__(self) -> None:
        bar = str(self.initial_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("exact action scenario initial_bar must be front or back")
        object.__setattr__(self, "initial_bar", bar)
        if float(self.target_resistance) < 0.0:
            raise ValueError("exact action scenario target_resistance cannot be negative")


class _ExplicitGeneratedActionEvaluator:
    def __init__(
        self,
        *,
        database_path: Path,
        build: PlayerBuild,
        progression: CharacterProgression,
        scenario: ExtremeSustainedDPSExactActionScenario,
    ) -> None:
        self.database_path = database_path
        self.build = build
        self.progression = progression
        self.scenario = scenario

    def evaluate(self) -> RotationActionDamageOccurrenceEvidence:
        action = self._action_at_coordinate()
        if action is None:
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=float(self.scenario.action_time_seconds),
                action_sequence=int(self.scenario.action_sequence),
                unresolved=(
                    "Exact scheduled action coordinate is absent from the fixed rotation plan",
                ),
            )

        static_context = RotationStaticBuildContextService(
            database_path=self.database_path,
            progression_adapter=ExtremeSustainedDPSExplicitProgressionAdapter(
                self.progression
            ),
        )
        provider = CombatSimulationSavedBuildDDProviderService(
            database_path=self.database_path,
            static_context_service=static_context,
        ).resolve(
            player_build=self.build,
            plan=self.scenario.plan,
            target_resistance=float(self.scenario.target_resistance),
            initial_bar=self.scenario.initial_bar,
            execute_target_identity=self.scenario.execute_target_identity,
        )
        if not provider.resolved or provider.provider is None:
            return RotationActionDamageOccurrenceEvidence(
                action_time_seconds=action.time_seconds,
                action_sequence=action.sequence,
                unresolved=tuple(provider.unresolved)
                or ("Canonical DD action provider is unresolved",),
            )

        candidate = GeneratedRotationCandidate(
            candidate_id="extreme-finite-axis-action-evaluation",
            plan=self.scenario.plan,
            refresh_leads=(),
            action_claims=(),
        )
        return provider.provider.evaluate_action_occurrences(
            candidate=candidate,
            action=action,
        )

    def _action_at_coordinate(self) -> RotationAction | None:
        matches = tuple(
            action
            for action in self.scenario.plan.actions
            if float(action.time_seconds) == float(self.scenario.action_time_seconds)
            and int(action.sequence) == int(self.scenario.action_sequence)
        )
        if len(matches) > 1:
            raise ValueError(
                "fixed rotation plan contains duplicate exact action coordinate"
            )
        return matches[0] if matches else None


class ExtremeSustainedDPSFiniteAxisCanonicalActionEvaluatorService:
    """Build exact-action evaluators for concrete generated frontier payloads."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        baseline_build: PlayerBuild,
        baseline_progression: CharacterProgression,
        scenario: ExtremeSustainedDPSExactActionScenario,
    ) -> None:
        self.database_path = Path(database_path)
        self.baseline_build = baseline_build
        self.baseline_progression = baseline_progression
        self.scenario = scenario

    def champion_points(self):
        outer = self

        class _Evaluator:
            def evaluate(
                self,
                choice: ExtremeSustainedDPSChampionPointCandidate,
            ) -> RotationActionDamageOccurrenceEvidence:
                return _ExplicitGeneratedActionEvaluator(
                    database_path=outer.database_path,
                    build=choice.build,
                    progression=outer.baseline_progression,
                    scenario=outer.scenario,
                ).evaluate()

        return _Evaluator()

    def passive_ranks(self):
        outer = self

        class _Evaluator:
            def evaluate(
                self,
                choice: ExtremeSustainedDPSPassiveRankCandidate,
            ) -> RotationActionDamageOccurrenceEvidence:
                return _ExplicitGeneratedActionEvaluator(
                    database_path=outer.database_path,
                    build=outer.baseline_build,
                    progression=choice.progression,
                    scenario=outer.scenario,
                ).evaluate()

        return _Evaluator()

    def dual_bar_gear(self):
        outer = self

        class _Evaluator:
            def evaluate(
                self,
                choice: ExtremeDualBarGearState,
            ) -> RotationActionDamageOccurrenceEvidence:
                build = ExtremeDualBarGearStateService.materialize(
                    outer.baseline_build,
                    choice,
                )
                return _ExplicitGeneratedActionEvaluator(
                    database_path=outer.database_path,
                    build=build,
                    progression=outer.baseline_progression,
                    scenario=outer.scenario,
                ).evaluate()

        return _Evaluator()


__all__ = [
    "ExtremeSustainedDPSExactActionScenario",
    "ExtremeSustainedDPSFiniteAxisCanonicalActionEvaluatorService",
]
