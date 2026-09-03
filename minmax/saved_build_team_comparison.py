from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.build import Build
from minmax.dd_damage import DDDamageEvent
from minmax.dd_single_build_evaluator import DDBuildEvaluator
from minmax.evaluation_context import EvaluationContext
from minmax.group_effects import GroupEffect
from minmax.group_evaluator import GroupEvaluator
from minmax.roster import RosterCandidate
from minmax.role import Role
from minmax.team_comparison import TeamComparison
from models.build_model import PlayerBuild
from services.build_service import BuildService


@dataclass(frozen=True)
class PlayerEvaluationEvidence:
    """Traceable evidence for one player's personal damage in team comparison."""
    
    player_name: str
    character_name: str
    build_name: str
    active_bar: str
    dd_event: DDDamageEvent
    evaluation_context: EvaluationContext
    dd_expected_damage: float
    roster_candidate: RosterCandidate


class SavedBuildTeamComparisonAdapter:
    """
    Adapter that loads two saved builds and compares them through TeamComparison.
    
    For Phase 12, this is a minimal implementation that:
    - Accepts exact saved build names and active bars
    - Uses DDBuildEvaluator with explicit DDDamageEvent and EvaluationContext
    - Creates RosterCandidate instances with traceable personal_damage
    - Does not invent rotations, trial requirements, or encounter-specific rules
    """

    def __init__(
        self,
        *,
        builds_path: Path,
        database_path: Path,
    ):
        self.builds_path = Path(builds_path)
        self.database_path = Path(database_path)
        self.build_service = BuildService(self.builds_path)
        self.dd_evaluator = DDBuildEvaluator()

    def _find_saved_build(self, build_name: str) -> PlayerBuild:
        """Find a saved build by name, raising ValueError if not found."""
        roster = self.build_service.load()
        key = str(build_name or "").strip().casefold()
        matches = [b for b in roster.Members if str(b.BuildName or "").strip().casefold() == key]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous saved build name: {build_name!r}")
        raise ValueError(f"Saved build not found: {build_name!r}")

    def _get_active_bar_skills(self, build: PlayerBuild, active_bar: str) -> tuple[str, ...]:
        """Extract skill names from the active bar."""
        if active_bar == "front":
            skills = getattr(build, "FrontBarSkills", None) or ()
        elif active_bar == "back":
            skills = getattr(build, "BackBarSkills", None) or ()
        else:
            raise ValueError(f"Invalid active_bar: {active_bar!r}; expected 'front' or 'back'")
        
        return tuple(str(s or "").strip() for s in skills if str(s or "").strip())

    def _evaluate_player(
        self,
        saved_build: PlayerBuild,
        active_bar: str,
        event: DDDamageEvent,
        context: EvaluationContext,
    ) -> PlayerEvaluationEvidence:
        """
        Evaluate a saved build's personal damage.
        
        For Phase 12, uses a minimal Build object with an empty stats dictionary.
        The provided DDDamageEvent and EvaluationContext are the scenario inputs.
        
        Returns PlayerEvaluationEvidence with traceable personal damage.
        """
        # Validate active bar has skills
        skills = self._get_active_bar_skills(saved_build, active_bar)
        if not skills:
            raise ValueError(
                f"Saved build {saved_build.BuildName!r} has no skills on {active_bar} bar"
            )

        # For Phase 12 MVP: use minimal Build with explicit event and context
        # Real builds would go through full character/progression pipeline
        minimal_build = Build(name=str(saved_build.BuildName or "unnamed").strip())

        # Evaluate DD damage through existing pipeline
        dd_evaluation = self.dd_evaluator.evaluate(
            minimal_build,
            event,
            context,
        )

        player_name = str(saved_build.Name or "unnamed").strip()
        character_name = str(saved_build.Name or "unnamed").strip()
        build_name = str(saved_build.BuildName or "unnamed").strip()

        roster_candidate = RosterCandidate(
            name=player_name,
            role=Role.DD,  # Phase 12 is DD-focused
            class_name=str(saved_build.EsoClass or "Unknown"),
            personal_damage=dd_evaluation.damage.expected_damage,
        )

        return PlayerEvaluationEvidence(
            player_name=player_name,
            character_name=character_name,
            build_name=build_name,
            active_bar=active_bar,
            dd_event=event,
            evaluation_context=context,
            dd_expected_damage=dd_evaluation.damage.expected_damage,
            roster_candidate=roster_candidate,
        )

    def compare(
        self,
        baseline_build_name: str,
        baseline_active_bar: str,
        candidate_build_name: str,
        candidate_active_bar: str,
        event: DDDamageEvent,
        context: EvaluationContext | None = None,
        group_effects: tuple[GroupEffect, ...] = (),
    ) -> tuple[TeamComparison, PlayerEvaluationEvidence, PlayerEvaluationEvidence]:
        """
        Compare two saved builds through the team comparison engine.
        
        Returns (TeamComparison, baseline_evidence, candidate_evidence).
        
        Raises ValueError if builds cannot be resolved or evaluations fail.
        """
        if context is None:
            context = EvaluationContext()

        baseline_build = self._find_saved_build(baseline_build_name)
        candidate_build = self._find_saved_build(candidate_build_name)

        baseline_evidence = self._evaluate_player(
            baseline_build,
            baseline_active_bar,
            event,
            context,
        )

        candidate_evidence = self._evaluate_player(
            candidate_build,
            candidate_active_bar,
            event,
            context,
        )

        # Build rosters with group effects
        baseline_roster = [baseline_evidence.roster_candidate]
        candidate_roster = [
            candidate_evidence.roster_candidate,
            *[
                RosterCandidate(
                    name=effect.source,
                    role=Role.DD,
                    class_name="Support",
                    personal_damage=0.0,
                    group_effects=(effect,),
                )
                for effect in group_effects
            ],
        ]

        # Evaluate rosters
        baseline_eval = GroupEvaluator().evaluate(baseline_roster)
        candidate_eval = GroupEvaluator().evaluate(candidate_roster)

        # Create comparison
        comparison = TeamComparison(
            baseline_name=baseline_build_name,
            candidate_name=candidate_build_name,
            baseline_evaluation=baseline_eval,
            candidate_evaluation=candidate_eval,
        )

        return comparison, baseline_evidence, candidate_evidence

    def compare(
        self,
        baseline_build_name: str,
        baseline_active_bar: str,
        candidate_build_name: str,
        candidate_active_bar: str,
        event: DDDamageEvent,
        context: EvaluationContext | None = None,
        group_effects: tuple[GroupEffect, ...] = (),
    ) -> tuple[TeamComparison, PlayerEvaluationEvidence, PlayerEvaluationEvidence]:
        """
        Compare two saved builds through the team comparison engine.
        
        Returns (TeamComparison, baseline_evidence, candidate_evidence).
        
        Raises ValueError if builds cannot be resolved or evaluations fail.
        """
        if context is None:
            context = EvaluationContext()

        baseline_build = self._find_saved_build(baseline_build_name)
        candidate_build = self._find_saved_build(candidate_build_name)

        baseline_evidence = self._evaluate_player(
            baseline_build,
            baseline_active_bar,
            event,
            context,
        )

        candidate_evidence = self._evaluate_player(
            candidate_build,
            candidate_active_bar,
            event,
            context,
        )

        # Build rosters with group effects
        baseline_roster = [baseline_evidence.roster_candidate]
        candidate_roster = [
            candidate_evidence.roster_candidate,
            *[
                RosterCandidate(
                    name=effect.source,
                    role=Role.DD,
                    class_name="Support",
                    personal_damage=0.0,
                    group_effects=(effect,),
                )
                for effect in group_effects
            ],
        ]

        # Evaluate rosters
        baseline_eval = GroupEvaluator().evaluate(baseline_roster)
        candidate_eval = GroupEvaluator().evaluate(candidate_roster)

        # Create comparison
        comparison = TeamComparison(
            baseline_name=baseline_build_name,
            candidate_name=candidate_build_name,
            baseline_evaluation=baseline_eval,
            candidate_evaluation=candidate_eval,
        )

        return comparison, baseline_evidence, candidate_evidence
