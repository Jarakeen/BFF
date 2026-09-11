from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from ui.rotation_canonical_cadence_orchestration_support import (
    RotationCanonicalCadenceOrchestrationSupport,
)
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(candidate_result="candidate-result")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CadenceCard:
    def clear_report(self) -> None:
        pass


class _PageState:
    def __init__(self) -> None:
        self.build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
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
        return object()


class _CanonicalRender:
    def build(self, _candidate_result):
        return None


def test_dashboard_page_defaults_heavy_restoration_to_canonical_pipeline() -> None:
    page = _PageState()

    result = CanonicalRotationDashboardPage.evaluate_canonical_candidates(
        page,
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
    )

    assert result is page.rotation_canonical_candidates.result
    assert len(page.rotation_canonical_candidates.calls) == 1
    assert page.rotation_canonical_candidates.calls[0]["restoration_resolver"] is None


def test_cadence_orchestration_preserves_canonical_heavy_restoration_default() -> None:
    canonical = _CanonicalCandidates()
    support = RotationCanonicalCadenceOrchestrationSupport(
        canonical_candidates=canonical,
        canonical_render=_CanonicalRender(),
    )
    bundle = SimpleNamespace(
        ready=True,
        unresolved=(),
        blocking_knowledge_gaps=(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=None,
        demands=(),
        options=(),
        wait_decision_factory=None,
        requirements=(),
        passives=(),
        reserve_assessment_resolver=None,
        max_iterations=6,
        baseline_id="baseline",
        coverage_report=None,
    )

    result = support.run(
        player_build=PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer"),
        generation_request=object(),
        evidence_bundle=bundle,
    )

    assert result.canonical_evidence is None
    assert len(canonical.calls) == 1
    assert canonical.calls[0]["restoration_resolver"] is None
