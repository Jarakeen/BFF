from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_context import build_candidate_context
from minmax.build_candidate_damage import measure_modeled_damage_potency
from minmax.build_candidate_evaluator import evaluate_damage_candidate, rank_candidate_comparisons
from minmax.build_candidate_mundus import enumerate_mundus_candidates
from minmax.build_candidate_mundus_objective import damage_mundus_objective_unresolved
from minmax.build_candidate_provider_scope import build_default_raid_provider_scope
from minmax.build_candidate_sustain import BuildCandidateSustainComparison, compare_sustain_runs
from minmax.build_sustain import evaluate_named_build_sustain
from minmax.build_sustain_relevance import sustain_relevant_context_unresolved
from minmax.context_factory import BuildCalculationContextFactory
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.gear_set_repository import GearSetRepository
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.mundus_repository import MundusRepository
from minmax.race_repository import RaceRepository
from minmax.resource_costs import ResourceType
from minmax.saved_build_activity import create_saved_bar_activity_plan
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.saved_build_capability_service import SavedBuildCapabilityService
from tools.audit_phase12_saved_build_candidates import (
    _candidate_change_label,
    _find_build,
    _format_value,
)

DEFAULT_BUILDS = get_data_dir() / "builds.json"


def _is_dd_role(value: str) -> bool:
    normalized = " ".join(str(value or "").strip().casefold().split())
    return normalized in {"dd", "damage dealer", "damage"}


def _plain_constraint_explanation(constraint: CandidateConstraint) -> str:
    name = str(constraint.name or "").strip().casefold()
    status = constraint.status

    if "sustain" in name:
        resource = name.replace("sustain", "").strip() or "resource"
        label = resource.title()
        if status is ConstraintStatus.REPAIRED:
            return f"Your current build runs out of {label} in this test, but this change fixes that problem."
        if status is ConstraintStatus.UNSATISFIED:
            return f"This setup still runs out of {label} in the test, so it cannot be recommended."
        if status is ConstraintStatus.WORSENED:
            return f"This change makes your {label} sustain worse, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return f"BFF cannot prove that this setup can sustain its {label} use, so it will not guess."
        if status is ConstraintStatus.IMPROVED:
            return f"This change improves your modeled {label} sustain."
        if status is ConstraintStatus.PRESERVED:
            return f"This change keeps your modeled {label} sustain intact."

    if name == "capability_coverage":
        if status is ConstraintStatus.PRESERVED:
            return "This change does not remove any resolved buffs, debuffs, or other useful capabilities your current build provides."
        if status is ConstraintStatus.IMPROVED:
            return "This change keeps everything your current build already provides and adds at least one resolved capability."
        if status is ConstraintStatus.WORSENED:
            return "This change removes a useful capability from the current build, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return "BFF cannot prove that all of your current build's useful capabilities are still present, so it will not guess."

    if name in {"provider_responsibility", "provider responsibilities"}:
        if status is ConstraintStatus.PRESERVED:
            return "You can still handle the raid jobs this build was already assigned to provide."
        if status is ConstraintStatus.WORSENED:
            return "This change would stop you from reliably doing one of your assigned raid jobs, so it is blocked."
        if status is ConstraintStatus.UNKNOWN:
            return "BFF does not have enough evidence to prove that you can still handle every assigned raid job, so it will not guess."

    return constraint.explanation


def _print_dd_recommendation(
    recommended,
    *,
    metric_name: str,
    role_mismatch: bool,
    provider_scope_evaluated: bool,
) -> None:
    """Print a plain-English summary followed by exact Phase 12 evidence."""

    if recommended is None:
        print("Recommendation: none.")
        return

    reason = "hard-constraint repair" if recommended.is_constraint_repair else "damage improvement"
    print(f"Recommendation: {_candidate_change_label(recommended)}")
    print("  In plain English:")
    if recommended.is_constraint_repair:
        print("    - This option is recommended because it fixes a required problem in the current build, even if the damage comparison itself does not increase.")
    else:
        print("    - This option improves the selected damage comparison and still passes all required checks.")
    for constraint in recommended.constraints:
        print(f"    - {_plain_constraint_explanation(constraint)}")
    if recommended.candidate_value is not None and recommended.baseline_value is not None:
        if abs(float(recommended.candidate_value) - float(recommended.baseline_value)) <= 1e-9:
            print("    - This particular test does not show a damage increase from the change.")
        elif recommended.candidate_value > recommended.baseline_value:
            print("    - This particular comparison also shows a modeled damage increase.")
    if role_mismatch:
        print("    - This is only a diagnostic damage test on a non-DD build. It does not mean BFF recommends changing that healer or tank into a DD.")
    print("    - The damage number below is a standardized comparison value, not your actual rotation DPS.")

    print("  Technical evidence:")
    print(f"    Reason: {reason}")
    print("    Changed:")
    if recommended.candidate.changes:
        for change in recommended.candidate.changes:
            print(f"      - {change.path}: {change.before} -> {change.after}")
    else:
        print("      - no serialized build changes recorded")
    print("    Expected modeled improvement:")
    print(f"      - metric: {metric_name}")
    print(f"      - baseline: {_format_value(recommended.baseline_value)}")
    print(f"      - candidate: {_format_value(recommended.candidate_value)}")
    print(f"      - delta: {_format_value(recommended.delta)}")
    print("    Constraints:")
    if recommended.constraints:
        for constraint in recommended.constraints:
            print(f"      - {constraint.name}: {constraint.status.value} | {constraint.explanation}")
    else:
        print("      - none evaluated")
    print("    Unresolved:")
    if recommended.unresolved:
        for message in recommended.unresolved:
            print(f"      - {message}")
    else:
        print("      - none in the selected candidate evidence")
    print("    Boundaries:")
    print("      - modeled value is not rotation DPS or raid ceiling damage")
    print("      - encounter-specific skill uptime is not modeled by this audit")
    if provider_scope_evaluated:
        print("      - Phase 11 provider responsibilities were evaluated for the supplied encounter roster")
    else:
        print("      - provider responsibilities were not evaluated; no encounter assignment scope was supplied")
    if role_mismatch:
        print("      - diagnostic role override only; this is not a DD recommendation for the saved healer/tank role")


def audit_saved_dd_candidates(
    *,
    database_path: Path,
    builds_path: Path,
    build_name: str,
    active_bar: str,
    resource: ResourceType,
    duration_seconds: float,
    event: DDDamageEvent,
    target_resistance: float | None,
    allow_role_mismatch: bool = False,
    provider_encounter: str | None = None,
    provider_roster_build_names: tuple[str, ...] = (),
) -> int:
    if not database_path.exists():
        print(f"Database not found: {database_path}")
        return 1
    if not builds_path.exists():
        print(f"Saved builds not found: {builds_path}")
        return 2
    if provider_roster_build_names and not str(provider_encounter or "").strip():
        print("--provider-roster-build requires --provider-encounter")
        return 7

    build_service = BuildService(builds_path)
    saved_members = build_service.load().Members
    try:
        baseline_build = _find_build(saved_members, build_name)
    except ValueError as exc:
        print(exc)
        return 3

    if not _is_dd_role(baseline_build.Role) and not allow_role_mismatch:
        print(
            f"Saved build {baseline_build.BuildName!r} has role "
            f"{baseline_build.Role or '(unset)'!r}; the DD candidate audit "
            "requires a damage-dealer build. Use --allow-role-mismatch only "
            "for pipeline diagnostics."
        )
        return 6

    progression_resolution = MinmaxCharacterProgressionAdapter(
        build_service.canonical.catalog_service
    ).resolve(baseline_build)
    if not progression_resolution.resolved:
        print("Canonical character progression is required:")
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
    evaluation_context = EvaluationContext(
        fight_duration=duration_seconds,
        target_resistance=target_resistance,
    )
    baseline_context = context_factory.build(
        character_id=character_id,
        build_id=baseline_build_id,
        build=baseline_build,
        progression=progression,
        active_bar=active_bar,
        fight_duration=duration_seconds,
        target_resistance=target_resistance,
    )
    baseline_damage = measure_modeled_damage_potency(
        context=baseline_context,
        event=event,
        evaluation_context=evaluation_context,
    )
    capability_service = SavedBuildCapabilityService(build_service, database_path)
    baseline_capability = capability_service.audit_build(baseline_build)

    provider_scope = None
    provider_roster_builds: tuple[PlayerBuild, ...] = ()
    normalized_provider_encounter = str(provider_encounter or "").strip()
    if normalized_provider_encounter:
        try:
            companion_builds = tuple(
                _find_build(saved_members, roster_build_name)
                for roster_build_name in provider_roster_build_names
            )
            provider_roster_builds = (baseline_build,) + companion_builds
            provider_scope = build_default_raid_provider_scope(
                encounter_id=normalized_provider_encounter,
                member_id=character_id,
                roster_builds=provider_roster_builds,
                capability_service=capability_service,
                data_root=get_data_dir(),
                database_path=database_path,
            )
        except (ValueError, LookupError, OSError) as exc:
            print(f"Provider scope could not be resolved: {exc}")
            return 8

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
    baseline_sustain_context_unresolved = sustain_relevant_context_unresolved(
        baseline_build,
        tuple(baseline_context.unresolved_gear_effects),
    )

    def resolve_context(candidate):
        return build_candidate_context(
            candidate=candidate,
            baseline_progression=progression,
            context_factory=context_factory,
            active_bar=active_bar,
            fight_duration=duration_seconds,
            target_resistance=target_resistance,
        )

    def resolve_damage(candidate_context):
        return measure_modeled_damage_potency(
            context=candidate_context.context,
            event=event,
            evaluation_context=evaluation_context,
        )

    def resolve_sustain(candidate_context):
        if candidate_context.context is None:
            unresolved = candidate_context.unresolved or (
                "Candidate calculation context is unavailable",
            )
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

        candidate_build = candidate_context.candidate.candidate_build
        context_unresolved = (
            tuple(baseline_sustain_context_unresolved)
            + sustain_relevant_context_unresolved(
                candidate_build,
                tuple(candidate_context.unresolved),
            )
        )
        if context_unresolved:
            return BuildCandidateSustainComparison(
                baseline_run=baseline_sustain,
                candidate_run=None,
                constraint=CandidateConstraint(
                    name=f"{resource.value} sustain",
                    status=ConstraintStatus.UNKNOWN,
                    explanation="Sustain comparison is unresolved: "
                    + "; ".join(context_unresolved),
                ),
                unresolved=tuple(context_unresolved),
            )

        candidate_run = evaluate_named_build_sustain(
            build=candidate_build,
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

    comparisons = tuple(
        evaluate_damage_candidate(
            candidate=candidate,
            baseline_damage=baseline_damage,
            baseline_capability=baseline_capability,
            baseline_assignments=(provider_scope.baseline_assignments if provider_scope is not None else None),
            member_id=character_id,
            capability_service=capability_service,
            resolve_context=resolve_context,
            resolve_damage=resolve_damage,
            resolve_sustain=resolve_sustain,
            resolve_assignments=(provider_scope.assignments_for if provider_scope is not None else None),
            resolve_objective_coverage=lambda row: damage_mundus_objective_unresolved(row, mundus_repository),
        ).comparison
        for candidate in candidates
    )
    ranking = rank_candidate_comparisons(comparisons)

    print()
    print("========================================")
    print(" PHASE 12 SAVED-BUILD DD CANDIDATE AUDIT")
    print("========================================")
    print(f"Character:       {baseline_build.Name or '(unnamed)'}")
    print(f"Build:           {baseline_build.BuildName or '(unnamed)'}")
    print(f"Saved role:      {baseline_build.Role or '(unset)'}")
    if not _is_dd_role(baseline_build.Role):
        print("Role boundary:   diagnostic override; this is not a DD recommendation")
    print(f"Active bar:      {active_bar}")
    print(f"Baseline Mundus: {baseline_build.Mundus or '(unset)'}")
    print(f"Damage metric:   {baseline_damage.metric_name}")
    print(f"Event:           base={event.base_value:g}; scaling={event.scaling_coefficient:g}; type={event.damage_type or 'untyped'}")
    print(f"Target resistance: {_format_value(target_resistance)}")
    print(f"Sustain:         {resource.value} over {duration_seconds:g}s")
    print("Action plan:     synthetic saved-bar stress plan; not an observed rotation")
    print("Candidate scope: one Mundus change per candidate")
    if provider_scope is None:
        print("Provider scope:  not evaluated; no encounter assignment context supplied")
    else:
        roster_label = ", ".join(str(build.BuildName or build.Name or "(unnamed)") for build in provider_roster_builds)
        print(f"Provider scope:  encounter={provider_scope.encounter_id}; saved roster={roster_label}; baseline assignment rows={len(provider_scope.baseline_assignments)}")
        for assignment in provider_scope.baseline_assignments:
            primaries = ", ".join(provider.character_name or provider.member_id for provider in assignment.primary_providers) or "none"
            print(f"Provider base:   {assignment.requirement_id}={assignment.status.value}; primary={primaries}")
    print("Boundary:        not rotation DPS and not raid ceiling damage")
    print(f"Baseline value:  {_format_value(baseline_damage.value)}")
    print()

    for index, comparison in enumerate(comparisons, start=1):
        print(f"[{index:02d}] {_candidate_change_label(comparison)}")
        print(f"  Damage:      {_format_value(comparison.candidate_value)}")
        print(f"  Delta:       {_format_value(comparison.delta)}")
        print(f"  Rankable:    {comparison.is_rankable}")
        for constraint in comparison.constraints:
            print(f"  Constraint:  {constraint.name}={constraint.status.value} | {constraint.explanation}")
        for message in comparison.unresolved:
            print(f"  Unresolved:  {message}")
        print()

    print("Deterministic rank order:")
    if not ranking.ranked:
        print("  (none; every candidate is blocked or unresolved)")
    for index, comparison in enumerate(ranking.ranked, start=1):
        print(f"  {index:02d}. {_candidate_change_label(comparison)}: delta={comparison.delta:.3f}")

    print()
    _print_dd_recommendation(
        ranking.recommended,
        metric_name=baseline_damage.metric_name,
        role_mismatch=not _is_dd_role(baseline_build.Role),
        provider_scope_evaluated=provider_scope is not None,
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Rank bounded Mundus candidates for one named saved build through canonical static DD and sustain evaluation.")
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--builds", type=Path, default=DEFAULT_BUILDS)
    parser.add_argument("--build", required=True)
    parser.add_argument("--active-bar", choices=("front", "back"), default="front")
    parser.add_argument("--resource", choices=("health", "magicka", "stamina"), default="magicka")
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--base-value", type=float, default=1000.0)
    parser.add_argument("--scaling-coefficient", type=float, default=1.0)
    parser.add_argument("--damage-type", choices=("untyped", "physical", "poison", "disease", "bleed", "magical", "flame", "frost", "shock"), default="flame")
    parser.add_argument("--target-resistance", type=float, default=18_200.0)
    parser.add_argument("--allow-role-mismatch", action="store_true", help="Allow a non-DD saved build for pipeline diagnostics only.")
    parser.add_argument("--provider-encounter", default=None, help="Optional canonical encounter id. When supplied, evaluate Phase 11 provider responsibilities through the configured default raid-coverage overlay.")
    parser.add_argument("--provider-roster-build", action="append", default=[], help="Additional saved build name in the provider roster. Repeat for each companion build; the optimized --build is always included exactly once.")
    return parser


if __name__ == "__main__":
    arguments = _parser().parse_args()
    damage_type = None if arguments.damage_type == "untyped" else arguments.damage_type
    raise SystemExit(
        audit_saved_dd_candidates(
            database_path=arguments.database,
            builds_path=arguments.builds,
            build_name=arguments.build,
            active_bar=arguments.active_bar,
            resource=ResourceType(arguments.resource),
            duration_seconds=arguments.duration,
            event=DDDamageEvent(
                base_value=arguments.base_value,
                scaling_coefficient=arguments.scaling_coefficient,
                damage_type=damage_type,
            ),
            target_resistance=arguments.target_resistance,
            allow_role_mismatch=arguments.allow_role_mismatch,
            provider_encounter=arguments.provider_encounter,
            provider_roster_build_names=tuple(arguments.provider_roster_build),
        )
    )
