from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from engine.config import get_data_dir
from services.btv_benchmark_evidence_service import (
    BTVBenchmarkCorpus,
    BTVBenchmarkEvidenceService,
    UPTIME_DENOMINATOR_UNKNOWN,
)
from services.canonical_build_bridge import CanonicalBuildBridge
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
    page._provider_btv_benchmark_corpus = None
    page._provider_btv_uptime_denominator_basis = UPTIME_DENOMINATOR_UNKNOWN
    page._provider_workload_candidate_service = TeamProviderWorkloadCandidateService(
        get_data_dir() / "eso.db"
    )
    _render_provider_workload(page)


def _select_btv_calibration_observation(corpus: BTVBenchmarkCorpus, effect_key: str):
    target = BTVBenchmarkEvidenceService.select_target_observation(
        corpus,
        effect_key=effect_key,
        page="insights",
    )
    if target is not None:
        return target

    candidates = tuple(
        row
        for row in corpus.find(effect_key=effect_key, page="insights")
        if row.player_role is None and row.theoretical_max_ratio is not None
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        sources = ", ".join(row.source_file for row in candidates)
        raise ValueError(
            f"ambiguous BTV theoretical calibration for {effect_key!r}: {sources}"
        )
    return candidates[0]


def _provider_btv_assessments(page, workloads):
    corpus = getattr(page, "_provider_btv_benchmark_corpus", None)
    if corpus is None:
        return {}

    denominator = getattr(
        page,
        "_provider_btv_uptime_denominator_basis",
        UPTIME_DENOMINATOR_UNKNOWN,
    )
    assessments = {}
    for workload in tuple(workloads or ()):
        temporal = workload.temporal_coverage_result
        if temporal is None:
            continue
        observation = _select_btv_calibration_observation(corpus, workload.effect_key)
        if observation is None:
            continue
        assessments[workload.alternative_id] = (
            BTVBenchmarkEvidenceService.assess_temporal_result(
                observation,
                temporal,
                temporal_uptime_denominator_basis=denominator,
            )
        )
    return assessments


def _render_materialized_provider_workload_decision(
    decision_result: TeamProviderWorkloadDecisionResult,
    *,
    candidate_result: TeamProviderWorkloadCandidateResult,
    policy_result: TeamProviderWorkloadPolicyResult | None = None,
    comparison: TeamProviderRotationWorkloadComparison | None = None,
    benchmark_assessments=None,
) -> str:
    if not decision_result.decisions:
        return TeamProviderWorkloadExplanationService.render_panel(())

    calibration_by_id = dict(benchmark_assessments or {})
    selected_ids = set(policy_result.preferred_ids if policy_result is not None else ())
    sections = [
        TeamProviderWorkloadExplanationService._render_decision(
            item,
            policy_applied=policy_result is not None,
            selected_by_policy=item.alternative_id in selected_ids,
            benchmark_assessment=calibration_by_id.get(item.alternative_id),
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
        benchmark_assessments = _provider_btv_assessments(
            page,
            candidate_result.workloads,
        )
        label.setText(
            _render_materialized_provider_workload_decision(
                decision_result,
                candidate_result=candidate_result,
                policy_result=getattr(page, "_provider_workload_policy_result", None),
                comparison=getattr(page, "_provider_rotation_workload_comparison", None),
                benchmark_assessments=benchmark_assessments,
            )
        )
    else:
        workloads = tuple(getattr(page, "_provider_rotation_workloads", ()) or ())
        label.setText(
            TeamProviderWorkloadExplanationService.render_panel(
                workloads,
                comparison=getattr(
                    page,
                    "_provider_rotation_workload_comparison",
                    None,
                ),
                benchmark_assessments=_provider_btv_assessments(page, workloads),
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


def _set_provider_btv_benchmark_corpus(
    page,
    corpus: BTVBenchmarkCorpus | None,
    *,
    uptime_denominator_basis: str = UPTIME_DENOMINATOR_UNKNOWN,
) -> None:
    if corpus is not None and not isinstance(corpus, BTVBenchmarkCorpus):
        raise TypeError("provider BTV benchmark evidence requires a BTVBenchmarkCorpus")
    page._provider_btv_benchmark_corpus = corpus
    page._provider_btv_uptime_denominator_basis = uptime_denominator_basis
    _render_provider_workload(page)


def _clear_provider_btv_benchmark_corpus(page) -> None:
    page._provider_btv_benchmark_corpus = None
    page._provider_btv_uptime_denominator_basis = UPTIME_DENOMINATOR_UNKNOWN
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
    """Resolve exact saved builds from canonical CompPlanState."""

    state = getattr(page, "_comp_plan_state", None)
    if state is None:
        return ()

    data_dir = get_data_dir()
    roster = CanonicalBuildBridge(
        data_dir / "builds.json",
    ).load().Members
    builds_by_id = {
        str(getattr(build, "BuildId", "") or "").strip(): build
        for build in roster
        if str(getattr(build, "BuildId", "") or "").strip()
    }

    resolved = []
    seen: set[str] = set()
    for chair in tuple(getattr(state, "chairs", ()) or ()):
        if str(getattr(chair, "build_source_kind", "") or "").strip().casefold() != "saved_build":
            continue
        build_id = str(getattr(chair, "selected_build_id", "") or "").strip()
        if not build_id or build_id in seen:
            continue
        build = builds_by_id.get(build_id)
        if build is None:
            continue
        seen.add(build_id)
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
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_COMP_REFRESH = CompBuilderPage._refresh_coverage
    CompBuilderPage.__init__ = _comp_init_with_provider_workload
    CompBuilderPage._refresh_coverage = _comp_refresh_with_provider_invalidation
    CompBuilderPage.set_provider_workload_evidence = _set_provider_workload_evidence
    CompBuilderPage.set_provider_workload_candidates = _set_provider_workload_candidates
    CompBuilderPage.set_provider_workload_policy = _set_provider_workload_policy
    CompBuilderPage.set_provider_btv_benchmark_corpus = _set_provider_btv_benchmark_corpus
    CompBuilderPage.clear_provider_btv_benchmark_corpus = _clear_provider_btv_benchmark_corpus
    CompBuilderPage.generate_provider_workload_candidates = (
        _generate_comp_provider_workload_candidates
    )
    CompBuilderPage.clear_provider_workload_evidence = _clear_provider_workload_evidence

    # Phase 14 Team Optimization is plan-scoped and read-only. Provider workload
    # remains reusable service logic, but its legacy Optimization widgets and
    # constructor/update hooks are not installed during normal startup.
    _INSTALLED = True


__all__ = ["install"]
