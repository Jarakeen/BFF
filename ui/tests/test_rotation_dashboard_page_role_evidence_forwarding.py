from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CadenceCard:
    def __init__(self) -> None:
        self.clears = 0

    def clear_report(self) -> None:
        self.clears += 1


class _Status:
    def __init__(self) -> None:
        self.warnings = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _DirectPageState:
    def __init__(self) -> None:
        self.build = object()
        self.request = object()
        self.rotation_canonical_candidates = _CanonicalCandidates()
        self.last_canonical_candidate_result = None
        self.last_canonical_render_evidence = None
        self.last_cadence_progression_run = None
        self.last_cadence_progression_render_evidence = None
        self.last_canonical_cadence_orchestration_result = None
        self.cadence_progression_card = _CadenceCard()

    def _selected_build(self):
        return self.build

    def canonical_generation_request(self):
        return self.request


def _bundle():
    return SimpleNamespace(
        ready=True,
        unresolved=(),
        blocking_knowledge_gaps=(),
        evaluator_resolver="evaluator",
        scorecard_resolver="scorecard",
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        content_type="trial",
        restoration_resolver=None,
        demands=("demand",),
        options=("option",),
        wait_decision_factory="wait",
        requirements=("requirement",),
        passives=("passive",),
        reserve_assessment_resolver="reserve",
        max_iterations=6,
        baseline_id="baseline",
        coverage_report="coverage",
    )


def test_page_direct_candidate_evaluation_forwards_role_evidence() -> None:
    page = _DirectPageState()
    role_evidence = object()

    result = CanonicalRotationDashboardPage.evaluate_canonical_candidates(
        page,
        evaluator_resolver="evaluator",
        scorecard_resolver="scorecard",
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        role_evidence=role_evidence,
    )

    assert result is page.rotation_canonical_candidates.result
    assert page.rotation_canonical_candidates.calls[0]["role_evidence"] is role_evidence


def test_page_evidence_bundle_forwards_role_evidence_into_direct_evaluation() -> None:
    role_evidence = object()

    class _BundlePage:
        def __init__(self) -> None:
            self.calls = []

        def evaluate_canonical_candidates(self, **kwargs):
            self.calls.append(kwargs)
            return "bundle-result"

    page = _BundlePage()
    result = CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(
        page,
        _bundle(),
        role_evidence=role_evidence,
        character_id="magrat-id",
    )

    assert result == "bundle-result"
    assert page.calls[0]["role_evidence"] is role_evidence
    assert page.calls[0]["character_id"] == "magrat-id"


def test_page_evidence_bundle_fills_blank_role_content_type_from_encounter() -> None:
    role_evidence = RotationCanonicalRoleEvidence(
        plan_evidence_provider=object(),  # type: ignore[arg-type]
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        reliable_group_healing=True,
    )

    class _BundlePage:
        def __init__(self) -> None:
            self.calls = []

        def evaluate_canonical_candidates(self, **kwargs):
            self.calls.append(kwargs)
            return "bundle-result"

    page = _BundlePage()
    result = CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(
        page,
        _bundle(),
        role_evidence=role_evidence,
    )

    assert result == "bundle-result"
    forwarded = page.calls[0]["role_evidence"]
    assert forwarded is not role_evidence
    assert forwarded.content_type == "trial"
    assert forwarded.reliable_group_healing is True
    assert role_evidence.content_type == ""


def test_page_cadence_orchestration_forwards_role_evidence() -> None:
    role_evidence = object()
    orchestration_result = SimpleNamespace(
        canonical_result="canonical-result",
        canonical_evidence=None,
        cadence_run=None,
        cadence_evidence=None,
    )

    class _Orchestrator:
        def __init__(self) -> None:
            self.calls = []

        def run(self, **kwargs):
            self.calls.append(kwargs)
            return orchestration_result

    class _CadencePage:
        def __init__(self) -> None:
            self.build = object()
            self.request = object()
            self.rotation_canonical_cadence_orchestration = _Orchestrator()
            self.last_canonical_cadence_orchestration_result = None
            self.last_canonical_candidate_result = None
            self.last_canonical_render_evidence = None
            self.last_cadence_progression_run = None
            self.last_cadence_progression_render_evidence = None
            self.cadence_progression_card = _CadenceCard()
            self.status = _Status()

        def _selected_build(self):
            return self.build

        def canonical_generation_request(self):
            return self.request

    page = _CadencePage()
    result = CanonicalRotationDashboardPage.run_canonical_cadence_orchestration(
        page,
        _bundle(),
        role_evidence=role_evidence,
        character_id="magrat-id",
    )

    assert result is orchestration_result
    call = page.rotation_canonical_cadence_orchestration.calls[0]
    assert call["role_evidence"] is role_evidence
    assert call["character_id"] == "magrat-id"
    assert page.last_canonical_candidate_result == "canonical-result"
