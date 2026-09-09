import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_shared_workload_card_is_installed_after_comp_maker_polish():
    source = (ROOT / "ui" / "team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    polish = source.index("install_comp_builder_polish()")
    workload = source.index("install_team_provider_workload_support()")
    assert polish < workload


def test_workload_support_targets_both_surfaces_and_invalidates_stale_results():
    source = (ROOT / "ui" / "team_provider_workload_support.py").read_text(
        encoding="utf-8"
    )

    assert 'FoundryCard("Provider Rotation Workload", "↻")' in source
    assert "CompBuilderPage.set_provider_workload_evidence" in source
    assert "OptimizationPage.set_provider_workload_evidence" in source
    assert "CompBuilderPage.generate_provider_workload_candidates" in source
    assert "OptimizationPage.generate_provider_workload_candidates" in source
    assert "CompBuilderPage.set_provider_workload_policy" in source
    assert "OptimizationPage.set_provider_workload_policy" in source
    assert "_comp_selected_saved_builds(page)" in source
    assert "_optimization_selected_saved_builds(page)" in source
    assert "CompBuilderPage._refresh_coverage = _comp_refresh_with_provider_invalidation" in source
    assert (
        "OptimizationPage._update_team_analysis = "
        "_optimization_update_with_provider_invalidation"
    ) in source
    assert "page._provider_workload_decision_result = None" in source
    assert "page._provider_workload_policy_result = None" in source
    assert "setStyleSheet" not in source


def test_workload_card_starts_with_honest_boundary_and_rejects_wrong_evidence():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from ui.team_provider_workload_support import (
        _install_workload_card,
        _set_provider_workload_evidence,
    )

    app = QApplication.instance() or QApplication([])
    page = QWidget()
    page.workspace_layout = QVBoxLayout(page)

    _install_workload_card(page)

    assert page.provider_workload_card.property("providerWorkloadCard") is True
    assert "No canonical provider rotation workload" in page.provider_workload_text.text()
    with pytest.raises(TypeError, match="canonical workload results"):
        _set_provider_workload_evidence(page, (object(),))
    page.deleteLater()
    app.processEvents()


def test_policy_renders_from_materialized_decision_and_clears_stale_state(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from services.team_provider_workload_candidate_service import (
        TeamProviderWorkloadCandidateRejection,
        TeamProviderWorkloadCandidateResult,
    )
    from services.team_provider_workload_decision_service import (
        TeamProviderWorkloadDecisionService,
    )
    from services.team_provider_workload_policy_service import (
        TeamProviderWorkloadPolicy,
        TeamProviderWorkloadPolicyDimension,
        TeamProviderWorkloadPolicyPriority,
    )
    from ui.team_provider_workload_support import (
        _install_workload_card,
        _render_provider_workload,
        _set_provider_workload_candidates,
        _set_provider_workload_evidence,
        _set_provider_workload_policy,
    )

    app = QApplication.instance() or QApplication([])
    page = QWidget()
    page.workspace_layout = QVBoxLayout(page)
    _install_workload_card(page)

    result = TeamProviderWorkloadCandidateResult(
        projections=(),
        rejected=(
            TeamProviderWorkloadCandidateRejection(
                alternative_id="blocked provider",
                effect_key="major_slayer",
                blockers=("no exact rotation plan is attached",),
            ),
        ),
    )
    policy = TeamProviderWorkloadPolicy(
        policy_id="healer encounter policy",
        encounter_key="trial boss",
        role_key="healer",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
        ),
    )

    _set_provider_workload_candidates(page, result, policy=policy)

    decision_result = page._provider_workload_decision_result
    policy_result = page._provider_workload_policy_result
    assert decision_result is not None
    assert policy_result is not None
    assert page._provider_workload_policy is policy

    def fail_reanalysis(_result):
        raise AssertionError("shared UI must render the materialized decision result")

    monkeypatch.setattr(TeamProviderWorkloadDecisionService, "analyze", fail_reanalysis)
    _render_provider_workload(page)
    _set_provider_workload_policy(page, policy)

    assert page._provider_workload_decision_result is decision_result
    assert page._provider_workload_policy_result is not None
    rendered = page.provider_workload_text.text()
    assert "BLOCKED PROVIDER • major_slayer • REJECTED" in rendered
    assert "POLICY • healer encounter policy" in rendered
    assert "No frontier alternatives were available for policy selection." in rendered

    _set_provider_workload_evidence(page, ())

    assert page._provider_workload_decision_result is None
    assert page._provider_workload_policy is None
    assert page._provider_workload_policy_result is None
    assert "POLICY • healer encounter policy" not in page.provider_workload_text.text()
    assert "No canonical provider rotation workload" in page.provider_workload_text.text()
    page.deleteLater()
    app.processEvents()


def test_policy_requires_candidate_evidence_and_rejects_wrong_type():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from services.team_provider_workload_policy_service import (
        TeamProviderWorkloadPolicy,
        TeamProviderWorkloadPolicyDimension,
        TeamProviderWorkloadPolicyPriority,
    )
    from ui.team_provider_workload_support import (
        _install_workload_card,
        _set_provider_workload_policy,
    )

    app = QApplication.instance() or QApplication([])
    page = QWidget()
    page.workspace_layout = QVBoxLayout(page)
    _install_workload_card(page)

    with pytest.raises(TypeError, match="policy has the wrong result type"):
        _set_provider_workload_policy(page, object())

    policy = TeamProviderWorkloadPolicy(
        policy_id="requires evidence",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PROVIDER_GCD_SECONDS
            ),
        ),
    )
    with pytest.raises(ValueError, match="requires projected candidate evidence"):
        _set_provider_workload_policy(page, policy)

    page.deleteLater()
    app.processEvents()
