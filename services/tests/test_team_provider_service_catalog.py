from __future__ import annotations

from services.service_catalog import (
    EvidenceClass,
    SERVICE_CATALOG,
    canonical_service_for,
)


def test_provider_uptime_measurement_and_policy_stay_separate() -> None:
    eligibility = canonical_service_for("team_provider_effect_eligibility")
    policy = canonical_service_for("team_provider_uptime_policy_assessment")
    assessment = canonical_service_for("team_provider_effect_uptime_assessment")

    assert eligibility is not None
    assert policy is not None
    assert assessment is not None
    assert eligibility.service_id == "team.provider.effect_eligibility"
    assert policy.service_id == "team.provider.uptime_policy"
    assert set(assessment.dependencies) == {
        eligibility.service_id,
        policy.service_id,
    }
    assert policy.evidence_class is EvidenceClass.POLICY
    assert "strategy or benchmark policy" in policy.notes


def test_provider_workload_policy_can_only_choose_frontier_survivors() -> None:
    decision = SERVICE_CATALOG.get("team.provider.workload_decision")
    policy = canonical_service_for("team_provider_workload_policy_selection")
    explanation = canonical_service_for("team_provider_workload_explanation")

    assert decision is not None
    assert policy is not None
    assert explanation is not None
    assert decision.service_id in policy.dependencies
    assert "frontier survivors" in policy.notes
    assert policy.service_id in explanation.dependencies
    assert explanation.ui_safe is True


def test_provider_marginal_value_keeps_objectives_separate() -> None:
    marginal = canonical_service_for("team_provider_marginal_named_effect_value")

    assert marginal is not None
    assert marginal.service_id == "team.provider.marginal_value"
    assert marginal.evidence_class is EvidenceClass.GAME_MECHANIC
    assert "never collapses unlike ESO objectives" in marginal.notes
