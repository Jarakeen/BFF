from types import SimpleNamespace

from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _CadenceRender:
    def __init__(self, evidence) -> None:
        self.evidence = evidence
        self.calls = []

    def build(self, run):
        self.calls.append(run)
        return self.evidence


class _DurationCard:
    def __init__(self) -> None:
        self.evidence = []

    def set_evidence(self, evidence) -> None:
        self.evidence.append(evidence)


class _Status:
    def __init__(self) -> None:
        self.messages = []

    def info(self, message: str) -> None:
        self.messages.append(message)


class _PageState:
    def __init__(self, evidence) -> None:
        self.rotation_cadence_progression_render = _CadenceRender(evidence)
        self.last_cadence_progression_run = None
        self.last_cadence_progression_render_evidence = None
        self.duration_evidence_card = _DurationCard()
        self.status = _Status()
        self.plans = []
        self.sustain = []

    def set_rotation_plan(self, plan) -> None:
        self.plans.append(plan)

    def set_sustain_projection(self, projection) -> None:
        self.sustain.append(projection)


def test_page_applies_one_final_cadence_progression_evidence_bundle() -> None:
    final_plan = object()
    final_sustain = object()
    duration = object()
    report = SimpleNamespace(
        advanced_steps=2,
        iterations=3,
        stop_summary="No eligible local cadence candidate improved the accepted rotation.",
    )
    evidence = SimpleNamespace(
        plan=final_plan,
        sustain_projection=final_sustain,
        duration_evidence=duration,
        report=report,
    )
    page = _PageState(evidence)
    run = object()

    rendered = CanonicalRotationDashboardPage.apply_cadence_progression_run(
        page,
        run,  # type: ignore[arg-type]
    )

    assert rendered is evidence
    assert page.rotation_cadence_progression_render.calls == [run]
    assert page.last_cadence_progression_run is run
    assert page.last_cadence_progression_render_evidence is evidence
    assert page.plans == [final_plan]
    assert page.duration_evidence_card.evidence == [duration]
    assert page.sustain == [final_sustain]
    assert page.status.messages == [
        "Cadence optimization: 2 accepted improvement(s) across 3 iteration(s). "
        "No eligible local cadence candidate improved the accepted rotation."
    ]


def test_page_status_uses_report_acceptance_count_not_proposed_step_count() -> None:
    report = SimpleNamespace(
        advanced_steps=1,
        iterations=2,
        stop_summary="The next promoted candidate repeated an already accepted executable schedule.",
    )
    evidence = SimpleNamespace(
        plan=object(),
        sustain_projection=object(),
        duration_evidence=object(),
        report=report,
    )
    page = _PageState(evidence)

    CanonicalRotationDashboardPage.apply_cadence_progression_run(
        page,
        object(),  # type: ignore[arg-type]
    )

    assert "1 accepted improvement(s)" in page.status.messages[0]
    assert "across 2 iteration(s)" in page.status.messages[0]
    assert "repeated an already accepted executable schedule" in page.status.messages[0]
