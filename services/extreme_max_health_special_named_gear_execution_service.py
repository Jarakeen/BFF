from __future__ import annotations

"""Dispatch classified Max Health special named-gear branches to canonical executors.

Classification says *what* makes a named-gear breakpoint special. This bridge says
which already-canonical execution contract owns that obligation. It does not
reimplement runtime-condition materialization or Twice-Born Star Mundus scoring.

Conditional branches and cumulative conditional bundles are executed through
``ExtremeResourceCandidateRuntimeConditionService`` for the materialized candidate
build. Search-state mutations are accepted only when the reviewed rule has a
canonical execution surface; ``ALLOWS_TWO_MUNDUS`` is owned by the existing
Twice-Born structural evaluator.
"""

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_gear_search_state_execution_coverage_service import (
    ExtremeGearSearchStateExecutionCoverageService,
)
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialBranchKind,
    ExtremeMaxHealthSpecialNamedGearBranch,
    ExtremeMaxHealthSpecialNamedGearBranchResult,
)
from services.extreme_resource_candidate_runtime_condition_service import (
    ExtremeResourceCandidateRuntimeConditionProjection,
    ExtremeResourceCandidateRuntimeConditionService,
)


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialNamedGearExecution:
    branch: ExtremeMaxHealthSpecialNamedGearBranch
    execution_owner: str
    runtime_projection: ExtremeResourceCandidateRuntimeConditionProjection | None = None
    search_state_rule: ExtremeGearSearchStateRule | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def executable(self) -> bool:
        if self.unresolved:
            return False
        if self.runtime_projection is not None:
            return self.runtime_projection.projection_complete
        return self.search_state_rule is not None and bool(self.execution_owner)


@dataclass(frozen=True)
class ExtremeMaxHealthSpecialNamedGearExecutionResult:
    executions: tuple[ExtremeMaxHealthSpecialNamedGearExecution, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_executable(self) -> bool:
        return bool(self.executions) and not self.unresolved and all(
            row.executable for row in self.executions
        )


class ExtremeMaxHealthSpecialNamedGearExecutionService:
    """Execute or dispatch every classified Max Health special gear obligation."""

    _TWICE_BORN_OWNER = (
        "services.extreme_twice_born_mundus_structural_stat_evaluator."
        "ExtremeTwiceBornMundusStructuralStatEvaluator"
    )

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        runtime_condition_service: ExtremeResourceCandidateRuntimeConditionService | None = None,
    ) -> None:
        if database_path is None and runtime_condition_service is None:
            raise ValueError(
                "database_path is required unless runtime_condition_service is supplied"
            )
        self.runtime_condition_service = (
            runtime_condition_service
            or ExtremeResourceCandidateRuntimeConditionService(database_path)
        )

    @staticmethod
    def _search_state_owners() -> dict[ExtremeGearSearchStateRule, tuple[str, ...]]:
        report = ExtremeGearSearchStateExecutionCoverageService.build()
        return {row.rule: row.execution_surfaces for row in report.rows if row.executable}

    @staticmethod
    def _required_conditions(
        branch: ExtremeMaxHealthSpecialNamedGearBranch,
    ) -> tuple[str, ...]:
        if branch.required_conditions:
            return tuple(branch.required_conditions)
        return (() if not branch.condition else (branch.condition,))

    def _execute_branch(
        self,
        branch: ExtremeMaxHealthSpecialNamedGearBranch,
        *,
        build: PlayerBuild,
        active_bar: str,
        food: str,
        route: ExtremeHealClassRoute | None,
    ) -> ExtremeMaxHealthSpecialNamedGearExecution:
        if branch.kind in {
            ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_FLAT,
            ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_PERCENT,
            ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE,
        }:
            required = self._required_conditions(branch)
            projection = self.runtime_condition_service.build(
                "max_health",
                build=build,
                active_bar=active_bar,
                food=food,
                route=route,
            )
            unresolved: list[str] = list(projection.unresolved)
            for condition in required:
                if condition not in projection.required_conditions:
                    unresolved.append(
                        f"materialized candidate does not expose required condition: {condition}"
                    )
                if condition not in projection.active_conditions:
                    unresolved.append(
                        f"required special-gear condition is not active: {condition}"
                    )
            return ExtremeMaxHealthSpecialNamedGearExecution(
                branch=branch,
                execution_owner=(
                    "services.extreme_resource_candidate_runtime_condition_service."
                    "ExtremeResourceCandidateRuntimeConditionService"
                ),
                runtime_projection=projection,
                unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
            )

        if branch.kind is ExtremeMaxHealthSpecialBranchKind.SEARCH_STATE_MUTATION:
            rule = branch.search_state_rule
            if rule is None:
                return ExtremeMaxHealthSpecialNamedGearExecution(
                    branch=branch,
                    execution_owner="",
                    unresolved=("classified search-state branch has no search-state rule",),
                )
            owners = self._search_state_owners().get(rule, ())
            if rule is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS:
                owner = next(
                    (value for value in owners if "ExtremeTwiceBornMundusStructuralStatEvaluator" in value),
                    "",
                )
            else:
                owner = owners[0] if owners else ""
            unresolved = () if owner else (
                f"search-state rule has no canonical execution owner: {rule.value}",
            )
            return ExtremeMaxHealthSpecialNamedGearExecution(
                branch=branch,
                execution_owner=owner,
                search_state_rule=rule,
                unresolved=unresolved,
            )

        return ExtremeMaxHealthSpecialNamedGearExecution(
            branch=branch,
            execution_owner="",
            unresolved=(f"unsupported special branch kind: {branch.kind}",),
        )

    def execute(
        self,
        classified: ExtremeMaxHealthSpecialNamedGearBranchResult,
        *,
        build: PlayerBuild,
        active_bar: str = "front",
        food: str = "",
        route: ExtremeHealClassRoute | None = None,
    ) -> ExtremeMaxHealthSpecialNamedGearExecutionResult:
        unresolved: list[str] = list(classified.unresolved)
        rows = tuple(
            self._execute_branch(
                branch,
                build=build,
                active_bar=active_bar,
                food=food,
                route=route,
            )
            for branch in classified.branches
        )
        for row in rows:
            unresolved.extend(row.unresolved)
        return ExtremeMaxHealthSpecialNamedGearExecutionResult(
            executions=rows,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeMaxHealthSpecialNamedGearExecution",
    "ExtremeMaxHealthSpecialNamedGearExecutionResult",
    "ExtremeMaxHealthSpecialNamedGearExecutionService",
]
