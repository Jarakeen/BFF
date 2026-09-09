from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from engine.config import get_data_dir
from services.build_service import BuildService
from services.team_provider_rotation_workload_service import (
    TeamProviderRotationWorkload,
    TeamProviderRotationWorkloadComparison,
)
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadAlternativeRequest,
    TeamProviderWorkloadCandidateResult,
    TeamProviderWorkloadCandidateService,
)
from services.team_provider_workload_decision_service import (
    TeamProviderWorkloadDecisionResult,
    TeamProviderWorkloadDecisionService,
)
from services.team_provider_workload_explanation_service import (
    TeamProviderWorkloadExplanationService,
)
from services.team_provider_workload_policy_service import (
    TeamProviderWorkloadPolicy,
    TeamProviderWorkloadPolicyResult,
    TeamProviderWorkloadPolicyService,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_COMP_REFRESH = None
_ORIGINAL_OPTIMIZATION_INIT = None
_ORIGINAL_OPTIMIZATION_UPDATE = None


def _install_workload_card(page) -> None:
    page.provider_workload_card = FoundryCard("Provider Rotation Workload", "↻")
    page.provider_workload_card.setProperty("providerWorkloadCard", True)
    page.provider_workload_text = QLabel()
    page.provider_workload_text.setWordWrap(True)
    page.provider_workload_text.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    page.provider_workload_text.setProperty("providerWorkloadEvidence", True)
    page.provider_workload_card.addWidget(page.provider_workload_text)
    page.workspace_layout.addWidget(page.provider_workload_card)
    page._provider_rotation_workloads = ()
    page._provider_rotation_workload_comparison = None
    page._provider_workload_candidate_result = None
    page._provider_workload_decision_result = None
    page._provider_workload_policy = None
    page._provider_workload_policy_result = None
    page._provider_workload_candidate_service = TeamProviderWorkloadCandidateService(
        get_data_dir() / "eso.db"
    )
    _render_provider_workload(page)


def _render_materialized_provider_workload_decision(
    decision_result: TeamProviderWorkloadDecisionResult,
    *,
    candidate_result: TeamProviderWorkloadCandidateResult,
    policy_result: TeamProviderWorkloadPolicyResult | None = None,
    comparison: TeamProviderRotationWorkloadComparison | None = None,
) -> str:
    if not decision_result.decisions:
        return TeamProviderWorkloadExplanationService.render_panel(())

    selected_ids = set(policy_result.preferred_ids if policy_result is not None else ())
    sections = [
        TeamProviderWorkloadExplanationService._render_decision(
            item,
            policy_applied=policy_result is not None,
            selected_by_policy=item.alternative_id in selected_ids,
        )
        for item in decision_result.decisions
    ]
    if policy_result is not None:
        sections.append(
            TeamProviderWorkloadExplanationService.render_policy_result(policy_result)
        )

    if comparison is not None:
        workloads = candidate_result.workloads
        if comparison.baseline not in workloads or comparison.candidate not in workloads:
            raise ValueError(
                "provider workload comparison must reference displayed workloads"
            )
        sections.append(
            TeamProviderWorkloadExplanationService._render_comparison(comparison)
        )
    return "\n\n".join(sections)


def _render_provider_workload(page) -> None:
    label = getattr(page, "provider_workload_text", None)
    if label is None:
        return
    candidate_result = getattr(page, "_provider_workload_candidate_result", None)
    decision_result = getattr(page, "_provider_workload_decision_result", None)
    if candidate_result is not None:
        if decision_result is None:
            raise ValueError(
                "provider workload candidates require a materialized decision result"
            )
        label.setText(
            _render_materialized_provider_workload_decision(
                decision_result,
                candidate_result=candidate_result,
                policy_result=getattr(page, "_provider_workload_policy_result", None),
                comparison=getattr(page, "_provider_rotation_workload_comparison", None),
            )
        )
    else:
        label.setText(
            TeamProviderWorkloadExplanationService.render_panel(
                tuple(getattr(page, "_provider_rotation_workloads", ()) or ()),
                comparison=getattr(
                    page,
                    "_provider_rotation_workload_comparison",
                    None,
                ),
            )
        )


def _set_provider_workload_evidence(
    page,
    workloads: tuple[TeamProviderRotationWorkload, ...],
    *,
    comparison: TeamProviderRotationWorkloadComparison | None = None,
) -> None:
    normalized = tuple(workloads or ())
    if any(not isinstance(item, TeamProviderRotationWorkload) for item in normalized):
        raise TypeError("provider workload card requires canonical workload results")
    if comparison is not None and not isinstance(
        comparison,
        TeamProviderRotationWorkloadComparison,
    ):
        raise TypeError("provider workload comparison has the wrong result type")
    page._provider_rotation_workloads = normalized
    page._provider_rotation_workload_comparison = comparison
    page._provider_workload_candidate_result = None
    page._provider_workload_decision_result = None
    page._provider_workload_policy = None
    page._provider_workload_policy_result = None
    _render_provider_workload(page)


def _set_provider_workload_candidates(
    page,
    result: TeamProviderWorkloadCandidateResult,
    *,
    comparison: TeamProviderRotationWorkloadComparison | None = None,
    policy: TeamProviderWorkloadPolicy | None = None,
) -> None:
    if not isinstance(result, TeamProviderWorkloadCandidateResult):
        raise TypeError("provider workload candidates have the wrong result type")
    if comparison is not None and not isinstance(
        comparison, TeamProviderRotationWorkloadComparison
    ):
        raise TypeError("provider workload comparison has the wrong result type")
    if policy is not None and not isinstance(policy, TeamProviderWorkloadPolicy):
        raise TypeError("provider workload policy has the wrong result type")

    decision_result = TeamProviderWorkloadDecisionService.analyze(result)
    policy_result = (
        TeamProviderWorkloadPolicyService.select(decision_result, policy)
        if policy is not None
        else None
    )
    page._provider_workload_candidate_result = result
    page._provider_workload_decision_result = decision_result
    page._provider_rotation_workloads = result.workloads
    page._provider_rotation_workload_comparison = comparison
    page._provider_workload_policy = policy
    page._provider_workload_policy_result = policy_result
    _render_provider_workload(page)


def _set_provider_workload_policy(
    page,
    policy: TeamProviderWorkloadPolicy | None,
) -> None:
    if policy is not None and not isinstance(policy, TeamProviderWorkloadPolicy):
        raise TypeError("provider workload policy has the wrong result type")
    decision_result = getattr(page, "_provider_workload_decision_result", None)
    if policy is not None and decision_result is None:
        raise ValueError("provider workload policy requires projected candidate evidence")
    page._provider_workload_policy = policy
    page._provider_workload_policy_result = (
        TeamProviderWorkloadPolicyService.select(decision_result, policy)
        if policy is not None
        else None
    )
    _render_provider_workload(page)


def _clear_provider_workload_evidence(page) -> None:
    page._provider_rotation_workloads = ()
    page._provider_rotation_workload_comparison = None
    page._provider_workload_candidate_result = None
    page._provider_workload_decision_result = None
    page._provider_workload_policy = None
    page._provider_workload_policy_result = None
    _render_provider_workload(page)


def _comp_selected_saved_builds(page):
    """Resolve only exact saved candidates currently applied to Comp chairs."""

    roster = BuildService(get_data_dir() / "builds.json").load().Members
    resolved = []
    seen: set[tuple[str, str]] = set()
    for candidate in getattr(page, "_comp_applied_candidates", {}).values():
        if getattr(candidate, "source_kind", "") != "saved_build":
            continue
        candidate_name = str(getattr(candidate, "name", "") or "").strip().casefold()
        candidate_owner = str(
            getattr(candidate, "source_name", "") or ""
        ).strip().casefold()
        matches = [
            build
            for build in roster
            if str(getattr(build, "BuildName", "") or "").strip().casefold()
            == candidate_name
            and str(
                getattr(build, "Name", "")
                or getattr(build, "Gamertag", "")
                or ""
            ).strip().casefold()
            == candidate_owner
        ]
        if len(matches) != 1:
            continue
        build = matches[0]
        key = (
            str(getattr(build, "Name", "") or "").strip().casefold(),
            str(getattr(build, "BuildName", "") or "").strip().casefold(),
        )
        if key not in seen:
            seen.add(key)
            resolved.append(build)
    return tuple(resolved)


def _optimization_selected_saved_builds(page):
    from ui.team_optimization_canonical_analysis_support import (
        _selected_builds_and_recruits,
    )

    builds, _recruits = _selected_builds_and_recruits(page)
    return builds


def _generate_provider_workload_candidates(
    page,
    *,
    selected_builds,
    rotation_plans,
    progression_by_identity,
    alternatives: tuple[TeamProviderWorkloadAlternativeRequest, ...],
    policy: TeamProviderWorkloadPolicy | None = None,
) -> TeamProviderWorkloadCandidateResult:
    result = page._provider_workload_candidate_service.generate(
        selected_builds=tuple(selected_builds),
        rotation_plans=tuple(rotation_plans),
        progression_by_identity=progression_by_identity,
        alternatives=tuple(alternatives),
    )
    _set_provider_workload_candidates(page, result, policy=policy)
    return result


def _generate_comp_provider_workload_candidates(
    page, *, rotation_plans, progression_by_identity, alternatives, policy=None
) -> TeamProviderWorkloadCandidateResult:
    return _generate_provider_workload_candidates(
        page,
        selected_builds=_comp_selected_saved_builds(page),
        rotation_plans=rotation_plans,
        progression_by_identity=progression_by_identity,
        alternatives=alternatives,
        policy=policy,
    )


def _generate_optimization_provider_workload_candidates(
    page, *, rotation_plans, progression_by_identity, alternatives, policy=None
) -> TeamProviderWorkloadCandidateResult:
    return _generate_provider_workload_candidates(
        page,
        selected_builds=_optimization_selected_saved_builds(page),
        rotation_plans=rotation_plans,
        progression_by_identity=progression_by_identity,
        alternatives=alternatives,
        policy=policy,
    )


def _comp_init_with_provider_workload(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_workload_card(self)


def _comp_refresh_with_provider_invalidation(self, *args) -> None:
    _clear_provider_workload_evidence(self)
    assert _ORIGINAL_COMP_REFRESH is not None
    _ORIGINAL_COMP_REFRESH(self, *args)


def _optimization_init_with_provider_workload(self, parent=None) -> None:
    assert _ORIGINAL_OPTIMIZATION_INIT is not None
    _ORIGINAL_OPTIMIZATION_INIT(self, parent)
    _install_workload_card(self)


def _optimization_update_with_provider_invalidation(self) -> None:
    _clear_provider_workload_evidence(self)
    assert _ORIGINAL_OPTIMIZATION_UPDATE is not None
    _ORIGINAL_OPTIMIZATION_UPDATE(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_COMP_INIT, _ORIGINAL_COMP_REFRESH
    global _ORIGINAL_OPTIMIZATION_INIT, _ORIGINAL_OPTIMIZATION_UPDATE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_COMP_REFRESH = CompBuilderPage._refresh_coverage
    CompBuilderPage.__init__ = _comp_init_with_provider_workload
    CompBuilderPage._refresh_coverage = _comp_refresh_with_provider_invalidation
    CompBuilderPage.set_provider_workload_evidence = _set_provider_workload_evidence
    CompBuilderPage.set_provider_workload_candidates = _set_provider_workload_candidates
    CompBuilderPage.set_provider_workload_policy = _set_provider_workload_policy
    CompBuilderPage.generate_provider_workload_candidates = (
        _generate_comp_provider_workload_candidates
    )
    CompBuilderPage.clear_provider_workload_evidence = _clear_provider_workload_evidence

    _ORIGINAL_OPTIMIZATION_INIT = OptimizationPage.__init__
    _ORIGINAL_OPTIMIZATION_UPDATE = OptimizationPage._update_team_analysis
    OptimizationPage.__init__ = _optimization_init_with_provider_workload
    OptimizationPage._update_team_analysis = _optimization_update_with_provider_invalidation
    OptimizationPage.set_provider_workload_evidence = _set_provider_workload_evidence
    OptimizationPage.set_provider_workload_candidates = _set_provider_workload_candidates
    OptimizationPage.set_provider_workload_policy = _set_provider_workload_policy
    OptimizationPage.generate_provider_workload_candidates = (
        _generate_optimization_provider_workload_candidates
    )
    OptimizationPage.clear_provider_workload_evidence = _clear_provider_workload_evidence
    _INSTALLED = True


__all__ = ["install"]
