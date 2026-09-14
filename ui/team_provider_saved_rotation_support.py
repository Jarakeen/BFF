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


_INSTALLED = False
_ORIGINAL_COMP_GENERATE = None
_ORIGINAL_OPTIMIZATION_GENERATE = None


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
        from ui.team_provider_workload_support import _comp_selected_saved_builds

        rotation_plans = _saved_rotation_plans(_comp_selected_saved_builds(page))
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
        from ui.team_provider_workload_support import _optimization_selected_saved_builds

        rotation_plans = _saved_rotation_plans(_optimization_selected_saved_builds(page))
    return _ORIGINAL_OPTIMIZATION_GENERATE(
        page,
        rotation_plans=rotation_plans,
        progression_by_identity=progression_by_identity,
        alternatives=alternatives,
        policy=policy,
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_GENERATE, _ORIGINAL_OPTIMIZATION_GENERATE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_COMP_GENERATE = CompBuilderPage.generate_provider_workload_candidates
    _ORIGINAL_OPTIMIZATION_GENERATE = (
        OptimizationPage.generate_provider_workload_candidates
    )
    CompBuilderPage.generate_provider_workload_candidates = (
        _comp_generate_with_saved_rotations
    )
    OptimizationPage.generate_provider_workload_candidates = (
        _optimization_generate_with_saved_rotations
    )
    _INSTALLED = True


__all__ = ["install"]
