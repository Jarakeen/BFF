from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_context import build_candidate_context
from minmax.build_candidate_evaluator import evaluate_healing_candidate, rank_candidate_comparisons
from minmax.build_candidate_healing import ModeledHealingPotency, measure_modeled_healing_potency
from minmax.build_candidate_mundus import enumerate_mundus_candidates
from minmax.build_candidate_sustain import BuildCandidateSustainComparison, compare_sustain_runs
from minmax.build_sustain import evaluate_named_build_sustain
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.saved_build_activity import create_saved_bar_activity_plan
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.saved_build_capability_service import SavedBuildCapabilityService

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _find_build(builds: tuple[PlayerBuild, ...] | list[PlayerBuild], requested: str) -> PlayerBuild:
    key = str(requested or "").strip().casefold()
    matches = [build for build in builds if str(build.BuildName or "").strip().casefold() == key]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous build name: {requested!r}")
    raise ValueError(f"Saved build not found: {requested!r}")


def _skills_for_bar(build: PlayerBuild, active_bar: str) -> tuple[str, ...]:
    values = build.FrontBarSkills if active_bar == "front" else build.BackBarSkills
    return tuple(str(value or "").strip() for value in values if str(value or "").strip())


def _select_verified_healing_skills(
    skill_names: tuple[str, ...],
    tooltip_service: SavedBuildSkillTooltipService,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    selected: list[str] = []
    excluded: list[str] = []
    unresolved: list[str] = []
    for skill_name in skill_names:
        resolution = tooltip_service.coefficients.resolve_name(skill_name)
        if resolution.rank is None:
            messages = resolution.unresolved or ("skill identity unresolved",)
            unresolved.extend(f"{skill_name}: {message}" for message in messages)
            continue
        components = tooltip_service.components.get_for_skill_rank(resolution.rank.skill_rank_id)
        if not components:
            unresolved.append(f"{skill_name}: component classification unavailable")
            continue
        if any(component.effect_kind is SkillEffectKind.HEAL for component in components):
            selected.append(skill_name)
            continue
        if any(component.effect_kind is SkillEffectKind.UNKNOWN for component in components):
            unresolved.append(f"{skill_name}: effect kind unresolved for one or more components")
            continue
        excluded.append(skill_name)
    return tuple(selected), tuple(excluded), tuple(dict.fromkeys(unresolved))


def _format_value(value: float | None) -> str:
    return "UNKNOWN" if value is None else f"{value:.3f}"


def _with_extra_unresolved(
    result: ModeledHealingPotency,
    messages: tuple[str, ...],
) -> ModeledHealingPotency:
    if not messages:
        return result
    return replace(
        result,
        unresolved=tuple(dict.fromkeys(tuple(result.unresolved) + tuple(messages))),
    )


def audit_saved_build_candidates(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
    active_bar: str,
    resource: ResourceType,
    duration_seconds: float,
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2

    build_service = BuildService(builds_path)
    try:
        baseline_build = _find_build(build_service.load().Members, build_name)
    except ValueError as exc:
        print(exc)
        return 3

    progression_resolution = MinmaxCharacterProgressionAdapter(
        build_service.canonical.catalog_service
    ).resolve(baseline_build)
    if not progression_resolution.resolved:
        print("Canonical character progression is required for Phase 12 candidate evaluation:")
        for message in progression_resolution.unresolved:
            print(f"  - {message}")
        return 4

    character_id = progression_resolution.character_id
    baseline_build_id = (
        str(getattr(baseline_build, "BuildId", "") or "").strip()
        or str(baseline_build.BuildName or "").strip()
        or "saved-build"
    )
    progression = progression_resolution.progression

    mundus_repository = MundusRepository(database_path)
    candidates = enumerate_mundus_candidates(
        baseline_build=baseline_build,
        character_id=character_id,
        baseline_build_id=baseline_build_id,
        mundus_repository=mundus_repository,
    )
    if len(candidates) < 2:
        print(f"Phase 12 requires at least two Mundus candidates; found {len(candidates)}")
        return 5

    context_factory = BuildCalculationContextFactory(
        race_repository=RaceRepository(database_path),
        gear_set_repository=GearSetRepository(database_path),
    )
    baseline_context = context_factory.build(
        character_id=character_id,
        build_id=baseline_build_id,
        build=baseline_build,
        progression=progression,
        active_bar=active_bar,
        fight_duration=duration_seconds,
    )

    bar_skill_names = _skills_for_bar(baseline_build, active_bar)
    tooltip_service = SavedBuildSkillTooltipService(database_path)
    healing_skill_names, excluded_skill_names, healing_selection_unresolved = (
        _select_verified_healing_skills(bar_skill_names, tooltip_service)
    )
    baseline_healing = _with_extra_unresolved(
        measure_modeled_healing_potency(
            build=baseline_build,
            context=baseline_context,
            skill_names=healing_skill_names,
            tooltip_service=tooltip_service,
        ),
        healing_selection_unresolved,
    )

    capability_service = SavedBuildCapabilityService(build_service, database_path)
    baseline_capability = capability_service.audit_build(baseline_build)

    activity_plan = create_saved_bar_activity_plan(
        baseline_build,
        active_bar=active_bar,
        duration_seconds=duration_seconds,
    )
    ability_cost_repository = AbilityCostRepository(database_path)
    cost_modifier_resolver = BuildActionCostModifierResolver(
        JewelryCostModifierRepository(database_path),
        JewelryTraitRepository(database_path),
    )
    baseline_sustain = evaluate_named_build_sustain(
        build=baseline_build,
        context=baseline_context,
        resource=resource,
        duration_seconds=duration_seconds,
        actions=activity_plan.actions,
        ability_cost_repository=ability_cost_repository,
        cost_modifier_resolver=cost_modifier_resolver,
    )

    def resolve_context(candidate):
        return build_candidate_context(
            candidate=candidate,
            baseline_progression=progression,
            context_factory=context_factory,
            active_bar=active_bar,
            fight_duration=duration_seconds,
        )

    def resolve_sustain(candidate_context):
        if candidate_context.context is None or candidate_context.unresolved:
            unresolved = candidate_context.unresolved or ("Candidate calculation context is unavailable",)
            return BuildCandidateSustainComparison(
                baseline_run=baseline_sustain,
                candidate_run=None,
                constraint=CandidateConstraint(
                    name=f"{resource.value} sustain",
                    status=ConstraintStatus.UNKNOWN,
                    explanation="Sustain comparison is unresolved: " + "; ".join(unresolved),
                ),
                unresolved=tuple(unresolved),
            )
        candidate_run = evaluate_named_build_sustain(
            build=candidate_context.candidate.candidate_build,
            context=candidate_context.context,
            resource=resource,
            duration_seconds=duration_seconds,
            actions=activity_plan.actions,
            ability_cost_repository=ability_cost_repository,
            cost_modifier_resolver=cost_modifier_resolver,
        )
        return BuildCandidateSustainComparison(
            baseline_run=baseline_sustain,
            candidate_run=candidate_run,
            constraint=compare_sustain_runs(
                resource=resource,
                baseline_run=baseline_sustain,
                candidate_run=candidate_run,
            ),
            unresolved=tuple(baseline_sustain.unresolved) + tuple(candidate_run.unresolved),
        )

    # Build-level Phase 12 has no exact encounter assignment to preserve yet.
    # Capability coverage remains enforced. Phase 13 will supply encounter-specific
    # Phase 11 assignments instead of this empty assignment context.
    baseline_assignments = ()

    evaluations = tuple(
        evaluate_healing_candidate(
            candidate=candidate,
            baseline_build=baseline_build,
            baseline_healing=baseline_healing,
            baseline_capability=baseline_capability,
            baseline_assignments=baseline_assignments,
            member_id=character_id,
            healing_skill_names=healing_skill_names,
            tooltip_service=tooltip_service,
            capability_service=capability_service,
            resolve_context=resolve_context,
            resolve_sustain=resolve_sustain,
            resolve_assignments=lambda _candidate_build: (),
        )
        for candidate in candidates
    )
    comparisons = tuple(evaluation.comparison for evaluation in evaluations)
    ranking = rank_candidate_comparisons(comparisons)

    print()
    print("========================================")
    print(" PHASE 12 SAVED-BUILD CANDIDATE AUDIT")
    print("========================================")
    print(f"Database:       {database_path}")
    print(f"Saved builds:   {builds_path}")
    print(f"Character:      {baseline_build.Name or '(unnamed)'}")
    print(f"Character ID:   {character_id}")
    print(f"Build:          {baseline_build.BuildName or '(unnamed)'}")
    print(f"Build ID:       {baseline_build_id}")
    print(f"Active bar:     {active_bar}")
    print(f"Baseline Mundus: {baseline_build.Mundus or '(unset)'}")
    print(f"Sustain:        {resource.value} over {duration_seconds:g}s")
    print(f"Bar skills:     {', '.join(bar_skill_names) if bar_skill_names else '(none)'}")
    print(f"Healing skills: {', '.join(healing_skill_names) if healing_skill_names else '(none)'}")
    print(f"Proven non-heals excluded: {', '.join(excluded_skill_names) if excluded_skill_names else '(none)'}")
    print("Objective:      modeled healing-component potency (one application per verified heal component)")
    print("Boundary:       not HPS; no encounter-specific Phase 11 assignments in this build-level audit")
    print()
    print(f"Baseline healing potency: {_format_value(baseline_healing.value if baseline_healing.resolved else None)}")
    if baseline_healing.unresolved:
        print("Baseline healing unresolved:")
        for message in baseline_healing.unresolved:
            print(f"  - {message}")
    if baseline_capability.capability_unresolved:
        print("Baseline capability unresolved:")
        for message in baseline_capability.capability_unresolved:
            print(f"  - {message}")
    if baseline_sustain.unresolved:
        print("Baseline sustain unresolved:")
        for message in baseline_sustain.unresolved:
            print(f"  - {message}")

    print()
    print(f"Mundus candidates evaluated: {len(comparisons)}")
    print(f"Rankable candidates:         {len(ranking.ranked)}")
    print()

    for index, comparison in enumerate(comparisons, start=1):
        change = comparison.candidate.changes[0] if comparison.candidate.changes else None
        after = change.after if change is not None else comparison.candidate.candidate_id
        print(f"[{index:02d}] {after}")
        print(f"  Candidate ID: {comparison.candidate.candidate_id}")
        print(f"  Healing:      {_format_value(comparison.candidate_value)}")
        print(f"  Delta:        {_format_value(comparison.delta)}")
        print(f"  Rankable:     {comparison.is_rankable}")
        print(f"  Improvement:  {comparison.is_improvement}")
        for constraint in comparison.constraints:
            print(f"  Constraint:   {constraint.name} = {constraint.status.value} | {constraint.explanation}")
        if comparison.unresolved:
            print("  Unresolved:")
            for message in comparison.unresolved:
                print(f"    - {message}")
        if comparison.rejection_reason:
            print(f"  Rejected:     {comparison.rejection_reason}")
        print()

    print("Deterministic rank order:")
    if not ranking.ranked:
        print("  (none; every candidate is blocked or unresolved)")
    for index, comparison in enumerate(ranking.ranked, start=1):
        change = comparison.candidate.changes[0] if comparison.candidate.changes else None
        after = change.after if change is not None else comparison.candidate.candidate_id
        print(f"  {index:02d}. {after}: delta={comparison.delta:.3f}")

    print()
    if ranking.recommended is None:
        print("Recommendation: none. No candidate is both proven-safe and an objective improvement.")
    else:
        recommended = ranking.recommended
        change = recommended.candidate.changes[0] if recommended.candidate.changes else None
        after = change.after if change is not None else recommended.candidate.candidate_id
        print(
            f"Recommendation: {after} | baseline={recommended.baseline_value:.3f} "
            f"candidate={recommended.candidate_value:.3f} delta={recommended.delta:.3f}"
        )
        for constraint in recommended.constraints:
            print(f"  - {constraint.name}: {constraint.status.value}: {constraint.explanation}")
    print()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate bounded Phase 12 Mundus candidates against one real saved build."
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", default="DF Healer")
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--resource", choices=("health", "magicka", "stamina"), default="magicka")
    parser.add_argument("--duration", type=float, default=20.0)
    return parser


if __name__ == "__main__":
    arguments = _parser().parse_args()
    raise SystemExit(
        audit_saved_build_candidates(
            database_path=arguments.database,
            builds_path=arguments.builds,
            build_name=arguments.build,
            active_bar=arguments.active_bar,
            resource=ResourceType(arguments.resource),
            duration_seconds=arguments.duration,
        )
    )
