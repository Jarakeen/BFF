from __future__ import annotations

"""Bridge build-owned saved RotationPlans into shared provider candidate generation.

The provider workload engine already consumes explicit canonical RotationPlans. This
UI integration only supplies those exact plans from build-owned rotation artifacts
when the caller does not provide an explicit plan set. Explicit caller evidence
always wins, including an explicitly empty tuple.
"""

from minmax.rotation_plan import RotationPlan
from engine.config import get_data_dir
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
)
from services.build_service import BuildService
from services.team_provider_assignment_workload_adapter_service import (
    TeamProviderAssignedWorkloadPolicy,
    TeamProviderAssignmentWorkloadAdapterService,
)
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateResult,
)


_INSTALLED = False
_ORIGINAL_COMP_GENERATE = None


def _identity(value: object) -> str:
    return str(value or "").strip().casefold()


def _saved_rotation_plans(selected_builds) -> tuple[RotationPlan, ...]:
    """Load exact build-owned saved plans for currently selected canonical builds."""
    build_service = BuildService(get_data_dir() / "builds.json")
    catalog_service = build_service.canonical.catalog_service
    artifacts = BuildRotationArtifactService(get_data_dir() / "build_rotations.json")

    plans: list[RotationPlan] = []
    for build in tuple(selected_builds or ()):
        build_id = resolve_canonical_build_id(catalog_service, build)
        if not build_id:
            continue
        try:
            plan = artifacts.get_rotation_plan(build_id)
        except ValueError as exc:
            character = str(getattr(build, "Name", "") or "Unnamed Character")
            build_name = str(getattr(build, "BuildName", "") or "Unnamed Build")
            raise ValueError(
                f"saved rotation for {character} / {build_name} is invalid: {exc}"
            ) from exc
        if plan is None:
            continue

        current_character = str(getattr(build, "Name", "") or "").strip()
        current_build = str(getattr(build, "BuildName", "") or "").strip()
        if not current_character or not current_build:
            continue

        # build_id is canonical identity; names are display metadata. If the user
        # renamed the character/build after saving, preserve the exact saved actions
        # while rebinding only the current display identity expected by candidate
        # generation. No mechanics, timing, assumptions, or unresolved evidence change.
        if (
            _identity(plan.character_name) != _identity(current_character)
            or _identity(plan.build_name) != _identity(current_build)
        ):
            plan = RotationPlan(
                character_name=current_character,
                build_name=current_build,
                duration_seconds=plan.duration_seconds,
                actions=plan.actions,
                assumptions=plan.assumptions,
                unresolved=plan.unresolved,
            )
        plans.append(plan)

    return tuple(plans)


def _comp_selected_builds(page):
    from ui.team_provider_workload_support import _comp_selected_saved_builds

    return _comp_selected_saved_builds(page)


def _optimization_selected_builds(page):
    from ui.team_provider_workload_support import _optimization_selected_saved_builds

    return _optimization_selected_saved_builds(page)


def _comp_generate_with_saved_rotations(
    page,
    *,
    rotation_plans=None,
    progression_by_identity,
    alternatives,
    policy=None,
):
    assert _ORIGINAL_COMP_GENERATE is not None
    if rotation_plans is None:
        rotation_plans = _saved_rotation_plans(_comp_selected_builds(page))
    return _ORIGINAL_COMP_GENERATE(
        page,
        rotation_plans=rotation_plans,
        progression_by_identity=progression_by_identity,
        alternatives=alternatives,
        policy=policy,
    )


def _optimization_generate_with_saved_rotations(
    page,
    *,
    rotation_plans=None,
    progression_by_identity,
    alternatives,
    policy=None,
):
    assert _ORIGINAL_OPTIMIZATION_GENERATE is not None
    if rotation_plans is None:
        rotation_plans = _saved_rotation_plans(_optimization_selected_builds(page))
    return _ORIGINAL_OPTIMIZATION_GENERATE(
        page,
        rotation_plans=rotation_plans,
        progression_by_identity=progression_by_identity,
        alternatives=alternatives,
        policy=policy,
    )


def _generate_assigned_provider_workload_candidates(
    page,
    *,
    selected_builds,
    assignments,
    effect_policies,
    workload_policies: tuple[TeamProviderAssignedWorkloadPolicy, ...],
    progression_by_identity,
    rotation_plans=None,
    policy=None,
) -> TeamProviderWorkloadCandidateResult:
    """Generate workload candidates from exact assignment and saved-plan evidence."""
    plans = (
        _saved_rotation_plans(selected_builds)
        if rotation_plans is None
        else tuple(rotation_plans)
    )
    projection = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=tuple(assignments),
        effect_policies=tuple(effect_policies),
        workload_policies=tuple(workload_policies),
        rotation_plans=plans,
    )

    generated = page.generate_provider_workload_candidates(
        rotation_plans=plans,
        progression_by_identity=progression_by_identity,
        alternatives=projection.alternatives,
        policy=policy,
    )
    if not projection.rejected:
        return generated

    merged = TeamProviderWorkloadCandidateResult(
        projections=generated.projections,
        rejected=projection.rejected + generated.rejected,
    )
    page.set_provider_workload_candidates(merged, policy=policy)
    return merged


def _generate_comp_assigned_provider_workload_candidates(
    page,
    *,
    assignments,
    effect_policies,
    workload_policies,
    progression_by_identity,
    rotation_plans=None,
    policy=None,
) -> TeamProviderWorkloadCandidateResult:
    return _generate_assigned_provider_workload_candidates(
        page,
        selected_builds=_comp_selected_builds(page),
        assignments=assignments,
        effect_policies=effect_policies,
        workload_policies=workload_policies,
        progression_by_identity=progression_by_identity,
        rotation_plans=rotation_plans,
        policy=policy,
    )


def _generate_optimization_assigned_provider_workload_candidates(
    page,
    *,
    assignments,
    effect_policies,
    workload_policies,
    progression_by_identity,
    rotation_plans=None,
    policy=None,
) -> TeamProviderWorkloadCandidateResult:
    return _generate_assigned_provider_workload_candidates(
        page,
        selected_builds=_optimization_selected_builds(page),
        assignments=assignments,
        effect_policies=effect_policies,
        workload_policies=workload_policies,
        progression_by_identity=progression_by_identity,
        rotation_plans=rotation_plans,
        policy=policy,
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_GENERATE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_GENERATE = CompBuilderPage.generate_provider_workload_candidates
    CompBuilderPage.generate_provider_workload_candidates = (
        _comp_generate_with_saved_rotations
    )
    CompBuilderPage.generate_assigned_provider_workload_candidates = (
        _generate_comp_assigned_provider_workload_candidates
    )

    # Phase 14 Team Optimization is plan-scoped and read-only. The old editable
    # Optimization provider-workload bridge remains compatibility-only and must not
    # be attached to OptimizationPage during normal startup.
    _INSTALLED = True


__all__ = ["install"]
