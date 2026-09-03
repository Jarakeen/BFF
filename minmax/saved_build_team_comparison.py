from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from minmax.calculation import CalculationResult, StatBreakdown
from minmax.context_factory import BuildCalculationContextFactory
from minmax.dd_damage import DDDamageEvent, DDDamageResult, calculate_dd_damage
from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import DDStatEvaluation, evaluate_dd_stats
from minmax.evaluation_context import EvaluationContext
from minmax.gear_set_repository import GearSetRepository
from minmax.group_effects import GroupEffect
from minmax.group_evaluation import GroupEvaluation
from minmax.group_evaluator import GroupEvaluator
from minmax.race_repository import RaceRepository
from minmax.roster import RosterCandidate
from minmax.role import Role
from minmax.stat_ids import StatId
from minmax.team_comparison import TeamComparison
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.saved_build_capability_service import (
    SavedBuildCapabilityAudit,
    SavedBuildCapabilityService,
)


@dataclass(frozen=True)
class PlayerEvaluationEvidence:
    """Traceable static, single-event evaluation for one saved build."""

    player_name: str
    character_name: str
    build_name: str
    active_bar: str
    dd_event: DDDamageEvent
    evaluation_context: EvaluationContext
    dd_expected_damage: float
    dd_stats: DDStatEvaluation
    damage: DDDamageResult
    static_unresolved: tuple[str, ...]
    roster_candidate: RosterCandidate


@dataclass(frozen=True)
class SavedBuildRosterMember:
    """One explicitly selected saved build in a modeled roster."""

    member_id: str
    build_name: str
    active_bar: str
    group_effects: tuple[GroupEffect, ...] = ()


@dataclass(frozen=True)
class SavedBuildRosterScenario:
    """A named 2-12 member roster evaluated under one shared scenario."""

    name: str
    members: tuple[SavedBuildRosterMember, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Roster scenario name is required.")
        if not 2 <= len(self.members) <= 12:
            raise ValueError("A saved-build roster scenario requires 2 to 12 members.")
        member_ids = [member.member_id.strip() for member in self.members]
        if any(not member_id for member_id in member_ids):
            raise ValueError("Every roster member requires a non-empty member_id.")
        folded = [member_id.casefold() for member_id in member_ids]
        if len(folded) != len(set(folded)):
            raise ValueError("Roster member_id values must be unique.")


@dataclass(frozen=True)
class SavedBuildRosterEvaluation:
    scenario: SavedBuildRosterScenario
    group_evaluation: GroupEvaluation
    player_evidence: tuple[PlayerEvaluationEvidence, ...]


@dataclass(frozen=True)
class SavedBuildRosterComparison:
    comparison: TeamComparison
    baseline: SavedBuildRosterEvaluation
    candidate: SavedBuildRosterEvaluation


class SavedBuildTeamComparisonAdapter:
    """
    Compare two saved-build single-member scenarios.

    This is deliberately not a raid-DPS or rotation simulator. Personal damage
    is one expected damage event evaluated from the canonical static saved-build
    context. Group effects supplied to compare are declared effects supplied by
    the candidate itself; a multi-member roster must attach each effect to its
    real selected provider rather than inventing a zero-damage support player.
    """

    def __init__(
        self,
        *,
        builds_path: Path,
        database_path: Path,
        progression_adapter=None,
        context_factory=None,
    ) -> None:
        self.builds_path = Path(builds_path)
        self.database_path = Path(database_path)
        self.build_service = BuildService(self.builds_path)
        self.progression_adapter = progression_adapter or MinmaxCharacterProgressionAdapter(
            self.build_service.canonical.catalog_service
        )
        self.context_factory = context_factory or BuildCalculationContextFactory(
            race_repository=RaceRepository(self.database_path),
            gear_set_repository=GearSetRepository(self.database_path),
        )

    def _find_saved_build(self, build_name: str) -> PlayerBuild:
        roster = self.build_service.load()
        key = str(build_name or "").strip().casefold()
        matches = [build for build in roster.Members if str(build.BuildName or "").strip().casefold() == key]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous saved build name: {build_name!r}")
        raise ValueError(f"Saved build not found: {build_name!r}")

    @staticmethod
    def _normalized_active_bar(active_bar: str) -> str:
        value = str(active_bar or "").strip().casefold()
        if value not in {"front", "back"}:
            raise ValueError(f"Invalid active_bar: {active_bar!r}; expected 'front' or 'back'")
        return value

    def _get_active_bar_skills(self, build: PlayerBuild, active_bar: str) -> tuple[str, ...]:
        bar = self._normalized_active_bar(active_bar)
        skills = build.FrontBarSkills if bar == "front" else build.BackBarSkills
        return tuple(str(skill or "").strip() for skill in skills if str(skill or "").strip())

    @staticmethod
    def _role(value: str) -> Role:
        try:
            return Role(str(value or "").strip().casefold())
        except ValueError:
            return Role.DD

    @staticmethod
    def _calculation_result(snapshot) -> CalculationResult:
        if snapshot.core_state is None:
            raise ValueError("Canonical static context has no resolved core stat state.")
        percent_stats = {StatId.CRITICAL_CHANCE, StatId.CRITICAL_DAMAGE}
        stats: dict[StatId, StatBreakdown] = {}
        for stat in (
            StatId.WEAPON_DAMAGE,
            StatId.SPELL_DAMAGE,
            StatId.PHYSICAL_PENETRATION,
            StatId.SPELL_PENETRATION,
            StatId.CRITICAL_CHANCE,
            StatId.CRITICAL_DAMAGE,
        ):
            trace = snapshot.core_state.derived.get(stat)
            value = float(trace.final_value) if trace is not None else 0.0
            if stat in percent_stats:
                value *= 100.0
            stats[stat] = StatBreakdown(base=value)
        return CalculationResult(stats=stats)

    def _evaluate_player(
        self,
        saved_build: PlayerBuild,
        active_bar: str,
        event: DDDamageEvent,
        context: EvaluationContext,
        *,
        group_effects: tuple[GroupEffect, ...] = (),
    ) -> PlayerEvaluationEvidence:
        bar = self._normalized_active_bar(active_bar)
        if not self._get_active_bar_skills(saved_build, bar):
            raise ValueError(f"Saved build {saved_build.BuildName!r} has no skills on {bar} bar")

        progression_resolution = self.progression_adapter.resolve(saved_build)
        if not progression_resolution.resolved:
            detail = "; ".join(progression_resolution.unresolved)
            raise ValueError(
                f"Canonical character progression is required for "
                f"{saved_build.BuildName!r}: {detail}"
            )

        build_id = (
            str(getattr(saved_build, "BuildId", "") or "").strip()
            or str(saved_build.BuildName or "").strip()
        )
        snapshot = self.context_factory.build(
            character_id=progression_resolution.character_id,
            build_id=build_id,
            build=saved_build,
            progression=progression_resolution.progression,
            active_bar=bar,
            target_count=context.target_count,
            target_resistance=context.target_resistance,
            fight_duration=context.fight_duration,
        )
        calculation = self._calculation_result(snapshot)
        dd_stats = evaluate_dd_stats(calculation, context)
        raw_damage = calculate_dd_damage(event, dd_stats)
        mitigation = None
        if context.target_resistance is not None and raw_damage.penetration_stat is not None:
            mitigation = calculate_dd_mitigation(
                target_resistance=context.target_resistance,
                penetration=raw_damage.penetration,
            )
        damage = calculate_dd_damage(event, dd_stats, mitigation=mitigation)

        player_name = str(saved_build.Name or saved_build.BuildName or "unnamed").strip()
        roster_candidate = RosterCandidate(
            name=player_name,
            role=self._role(saved_build.Role),
            class_name=str(saved_build.EsoClass or "Unknown"),
            personal_damage=damage.final_damage,
            group_effects=group_effects,
        )
        return PlayerEvaluationEvidence(
            player_name=player_name,
            character_name=player_name,
            build_name=str(saved_build.BuildName or "unnamed").strip(),
            active_bar=bar,
            dd_event=event,
            evaluation_context=context,
            dd_expected_damage=damage.final_damage,
            dd_stats=dd_stats,
            damage=damage,
            static_unresolved=tuple(snapshot.unresolved_gear_effects),
            roster_candidate=roster_candidate,
        )

    @staticmethod
    def _with_static_unresolved(
        evaluation: GroupEvaluation,
        evidence: PlayerEvaluationEvidence,
    ) -> GroupEvaluation:
        messages = tuple(dict.fromkeys(
            tuple(evaluation.unresolved_effects)
            + tuple(f"{evidence.build_name}: {message}" for message in evidence.static_unresolved)
        ))
        return replace(evaluation, unresolved_effects=messages)

    def evaluate_roster(
        self,
        scenario: SavedBuildRosterScenario,
        event: DDDamageEvent,
        context: EvaluationContext | None = None,
    ) -> SavedBuildRosterEvaluation:
        """Evaluate selected saved builds together as one shared roster."""
        if context is None:
            context = EvaluationContext()

        evidence_rows: list[PlayerEvaluationEvidence] = []
        roster: list[RosterCandidate] = []
        static_unresolved: list[str] = []

        for member in scenario.members:
            evidence = self._evaluate_player(
                self._find_saved_build(member.build_name),
                member.active_bar,
                event,
                context,
                group_effects=member.group_effects,
            )
            candidate = replace(evidence.roster_candidate, name=member.member_id.strip())
            evidence = replace(evidence, roster_candidate=candidate)
            evidence_rows.append(evidence)
            roster.append(candidate)
            static_unresolved.extend(
                f"{member.member_id.strip()} ({evidence.build_name}): {message}"
                for message in evidence.static_unresolved
            )

        evaluation = GroupEvaluator().evaluate(roster)
        evaluation = replace(
            evaluation,
            unresolved_effects=tuple(
                dict.fromkeys(tuple(evaluation.unresolved_effects) + tuple(static_unresolved))
            ),
        )
        return SavedBuildRosterEvaluation(
            scenario=scenario,
            group_evaluation=evaluation,
            player_evidence=tuple(evidence_rows),
        )

    def compare_rosters(
        self,
        baseline: SavedBuildRosterScenario,
        candidate: SavedBuildRosterScenario,
        event: DDDamageEvent,
        context: EvaluationContext | None = None,
    ) -> SavedBuildRosterComparison:
        """Compare two explicitly selected saved-build rosters."""
        baseline_evaluation = self.evaluate_roster(baseline, event, context)
        candidate_evaluation = self.evaluate_roster(candidate, event, context)
        comparison = TeamComparison(
            baseline_name=baseline.name,
            candidate_name=candidate.name,
            baseline_evaluation=baseline_evaluation.group_evaluation,
            candidate_evaluation=candidate_evaluation.group_evaluation,
        )
        return SavedBuildRosterComparison(
            comparison=comparison,
            baseline=baseline_evaluation,
            candidate=candidate_evaluation,
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
        if context is None:
            context = EvaluationContext()

        baseline_evidence = self._evaluate_player(
            self._find_saved_build(baseline_build_name),
            baseline_active_bar,
            event,
            context,
        )
        candidate_evidence = self._evaluate_player(
            self._find_saved_build(candidate_build_name),
            candidate_active_bar,
            event,
            context,
            group_effects=group_effects,
        )
        baseline_evaluation = self._with_static_unresolved(
            GroupEvaluator().evaluate([baseline_evidence.roster_candidate]),
            baseline_evidence,
        )
        candidate_evaluation = self._with_static_unresolved(
            GroupEvaluator().evaluate([candidate_evidence.roster_candidate]),
            candidate_evidence,
        )
        comparison = TeamComparison(
            baseline_name=baseline_evidence.build_name,
            candidate_name=candidate_evidence.build_name,
            baseline_evaluation=baseline_evaluation,
            candidate_evaluation=candidate_evaluation,
        )
        return comparison, baseline_evidence, candidate_evidence
