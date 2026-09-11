from types import SimpleNamespace

from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generate_action_support import RotationGenerateActionSupport
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class _Status:
    def __init__(self) -> None:
        self.infos = []
        self.warnings = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _Page:
    def __init__(self, context=None) -> None:
        self.rotation_generate_canonical_context = context
        self.status = _Status()
        self.bundle_calls = []
        self.run_calls = []
        self.bundle = object()
        self.result = SimpleNamespace(final_plan="final-plan", cadence_evidence=None)

    def selected_encounter_evidence_bundle(self, inputs):
        self.bundle_calls.append(inputs)
        return self.bundle

    def run_canonical_cadence_orchestration(self, bundle, **kwargs):
        self.run_calls.append((bundle, kwargs))
        return self.result

    def selected_encounter_id(self):
        return "sunspire_lokkestiiz"


def _context(*, role_evidence="role-evidence") -> RotationGenerateCanonicalContext:
    return RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
        role_evidence=role_evidence,  # type: ignore[arg-type]
        cadence_obligations=("obligation",),  # type: ignore[arg-type]
        cadence_priorities="priorities",  # type: ignore[arg-type]
        cadence_evaluation_context="evaluation",  # type: ignore[arg-type]
        cadence_max_iterations=5,
        character_id="magrat-id",
    )


def test_generate_without_canonical_context_preserves_plain_dashboard_path(monkeypatch) -> None:
    support = RotationGenerateActionSupport()
    page = _Page(context=None)
    calls = []

    monkeypatch.setattr(
        RotationDashboardPage,
        "generate_rotation",
        lambda supplied_page: calls.append(supplied_page),
    )

    support.generate(page)

    assert calls == [page]
    assert page.bundle_calls == []
    assert page.run_calls == []


def test_generate_with_context_resolves_selected_encounter_and_runs_full_orchestration() -> None:
    support = RotationGenerateActionSupport()
    context = _context()
    page = _Page(context=context)

    support.generate(page)

    assert page.bundle_calls == [context.evidence_inputs]
    assert len(page.run_calls) == 1
    bundle, kwargs = page.run_calls[0]
    assert bundle is page.bundle
    assert kwargs == {
        "role_evidence": "role-evidence",
        "cadence_obligations": ("obligation",),
        "cadence_priorities": "priorities",
        "cadence_evaluation_context": "evaluation",
        "cadence_max_iterations": 5,
        "character_id": "magrat-id",
    }
    assert page.status.warnings == []
    assert page.status.infos == [
        "Canonical rotation generated for sunspire_lokkestiiz."
    ]


def test_generate_context_without_role_evidence_preserves_none_explicitly() -> None:
    support = RotationGenerateActionSupport()
    context = _context(role_evidence=None)
    page = _Page(context=context)

    support.generate(page)

    _, kwargs = page.run_calls[0]
    assert kwargs["role_evidence"] is None


def test_configured_encounter_failure_is_reported_without_plain_fallback(monkeypatch) -> None:
    support = RotationGenerateActionSupport()
    page = _Page(context=_context())
    plain_calls = []

    monkeypatch.setattr(
        RotationDashboardPage,
        "generate_rotation",
        lambda supplied_page: plain_calls.append(supplied_page),
    )

    def blocked(_inputs):
        raise ValueError("reviewed target window is missing")

    page.selected_encounter_evidence_bundle = blocked

    support.generate(page)

    assert plain_calls == []
    assert page.run_calls == []
    assert page.status.infos == []
    assert page.status.warnings == [
        "Encounter-aware rotation generation blocked: reviewed target window is missing"
    ]


def test_set_and_clear_context_are_explicit_opt_in_controls() -> None:
    support = RotationGenerateActionSupport()
    page = _Page(context=None)
    context = _context()

    support.set_context(page, context)
    assert page.rotation_generate_canonical_context is context

    support.clear_context(page)
    assert page.rotation_generate_canonical_context is None
