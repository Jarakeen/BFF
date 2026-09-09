from types import SimpleNamespace

import pytest

from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _Orchestrator:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _DurationCard:
    def __init__(self) -> None:
        self.values = []

    def set_evidence(self, evidence) -> None:
        self.values.append(evidence)


class _CadenceCard:
    def __init__(self) -> None:
        self.reports = []
        self.clear_calls = 0

    def set_report(self, report) -> None:
        self.reports.append(report)

    def clear_report(self) -> None:
        self.clear_calls += 1


class _Status:
    def __init__(self) -> None:
        self.info_messages = []
        self.warning_messages = []

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def warning(self, message: str) -> None:
        self.warning_messages.append(message)


class _Page:
    def __init__(self, result, *, build=object()) -> None:
        self.build = build
        self.request = object()
        self.rotation_canonical_cadence_orchestration = _Orchestrator(result)
        self.last_canonical_cadence_orchestration_result = None
        self.last_canonical_candidate_result = None
        self.last_canonical_render_evidence = None
        self.last_cadence_progression_run = None
        self.last_cadence_progression_render_evidence = None
        self.duration_evidence_card = _DurationCard()
        self.cadence_progression_card = _CadenceCard()
        self.status = _Status()
        self.plans = []
        self.sustain = []

    def _selected_build(self):
        return self.build

    def canonical_generation_request(self):
        return self.request

    def set_rotation_plan(self, plan) -> None:
        self.plans.append(plan)

    def set_sustain_projection(self, projection) -> None:
        self.sustain.append(projection)


def test_page_renders_final_cadence_evidence_from_orchestrated_run() -> None:
    report = SimpleNamespace(
        advanced_steps=2,
        iterations=3,
        stop_summary="No further eligible local cadence improvement was found.",
    )
    canonical_result = object()
    canonical_evidence = SimpleNamespace(
        plan="canonical-plan",
        duration_evidence="canonical-duration",
        sustain_projection="canonical-sustain",
    )
    cadence_run = object()
    cadence_evidence = SimpleNamespace(
        plan="cadence-plan",
        duration_evidence="cadence-duration",
        sustain_projection="cadence-sustain",
        report=report,
    )
    result = SimpleNamespace(
        canonical_result=canonical_result,
        canonical_evidence=canonical_evidence,
        cadence_run=cadence_run,
        cadence_evidence=cadence_evidence,
    )
    page = _Page(result)
    bundle = object()
    obligations = (object(), object())
    priorities = object()
    context = object()

    returned = CanonicalRotationDashboardPage.run_canonical_cadence_orchestration(
        page,
        bundle,  # type: ignore[arg-type]
        cadence_obligations=obligations,  # type: ignore[arg-type]
        cadence_priorities=priorities,  # type: ignore[arg-type]
        cadence_evaluation_context=context,  # type: ignore[arg-type]
        cadence_max_iterations=5,
        character_id="magrat-id",
    )

    assert returned is result
    assert page.rotation_canonical_cadence_orchestration.calls == [
        {
            "player_build": page.build,
            "generation_request": page.request,
            "evidence_bundle": bundle,
            "cadence_obligations": obligations,
            "cadence_priorities": priorities,
            "cadence_evaluation_context": context,
            "cadence_max_iterations": 5,
            "character_id": "magrat-id",
        }
    ]
    assert page.last_canonical_cadence_orchestration_result is result
    assert page.last_canonical_candidate_result is canonical_result
    assert page.last_canonical_render_evidence is canonical_evidence
    assert page.last_cadence_progression_run is cadence_run
    assert page.last_cadence_progression_render_evidence is cadence_evidence
    assert page.plans == ["cadence-plan"]
    assert page.duration_evidence_card.values == ["cadence-duration"]
    assert page.sustain == ["cadence-sustain"]
    assert page.cadence_progression_card.reports == [report]
    assert "2 accepted improvement(s) across 3 iteration(s)" in page.status.info_messages[0]


def test_page_renders_canonical_winner_when_cadence_is_not_applied() -> None:
    canonical_result = object()
    canonical_evidence = SimpleNamespace(
        plan="canonical-plan",
        duration_evidence="canonical-duration",
        sustain_projection="canonical-sustain",
    )
    result = SimpleNamespace(
        canonical_result=canonical_result,
        canonical_evidence=canonical_evidence,
        cadence_run=None,
        cadence_evidence=None,
    )
    page = _Page(result)

    returned = CanonicalRotationDashboardPage.run_canonical_cadence_orchestration(
        page,
        object(),  # type: ignore[arg-type]
    )

    assert returned is result
    assert page.plans == ["canonical-plan"]
    assert page.duration_evidence_card.values == ["canonical-duration"]
    assert page.sustain == ["canonical-sustain"]
    assert page.cadence_progression_card.clear_calls == 1
    assert page.cadence_progression_card.reports == []
    assert page.last_cadence_progression_run is None
    assert page.last_cadence_progression_render_evidence is None


def test_page_keeps_existing_display_when_orchestration_has_no_selectable_winner() -> None:
    result = SimpleNamespace(
        canonical_result=object(),
        canonical_evidence=None,
        cadence_run=None,
        cadence_evidence=None,
    )
    page = _Page(result)

    returned = CanonicalRotationDashboardPage.run_canonical_cadence_orchestration(
        page,
        object(),  # type: ignore[arg-type]
    )

    assert returned is result
    assert page.plans == []
    assert page.duration_evidence_card.values == []
    assert page.sustain == []
    assert page.cadence_progression_card.clear_calls == 1
    assert len(page.status.warning_messages) == 1
    assert "no selectable rotation" in page.status.warning_messages[0].casefold()


def test_page_requires_selected_build_before_orchestration() -> None:
    page = _Page(object(), build=None)

    with pytest.raises(ValueError, match="select a saved build"):
        CanonicalRotationDashboardPage.run_canonical_cadence_orchestration(
            page,
            object(),  # type: ignore[arg-type]
        )

    assert page.rotation_canonical_cadence_orchestration.calls == []
