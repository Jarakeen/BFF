from types import SimpleNamespace

from ui.rotation_generate_action_support import RotationGenerateActionSupport
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class _Status:
    def __init__(self) -> None:
        self.warnings = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _Composer:
    def __init__(self) -> None:
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("role composer must not run for a blocked shared bundle")


class _Page:
    def __init__(self, context, bundle) -> None:
        self.rotation_generate_canonical_context = context
        self.rotation_generate_canonical_context_provider = None
        self.bundle = bundle
        self.status = _Status()
        self.run_calls = []
        self.build = SimpleNamespace(Role="Healer")

    def selected_encounter_evidence_bundle(self, _inputs):
        return self.bundle

    def _selected_build(self):
        return self.build

    def run_canonical_cadence_orchestration(self, *args, **kwargs):
        self.run_calls.append((args, kwargs))
        raise AssertionError("blocked bundle must not enter orchestration")


def test_blocking_shared_bundle_stops_before_role_specific_composition() -> None:
    composer = _Composer()
    context = RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
        role_evidence_composer=composer,
    )
    gap = SimpleNamespace(
        blocking=True,
        summary="No explicit rotation demand policy is configured.",
        needed_evidence="Configure reviewed demand policy.",
    )
    bundle = SimpleNamespace(
        ready=False,
        unresolved=(),
        blocking_knowledge_gaps=(gap,),
    )
    page = _Page(context, bundle)

    RotationGenerateActionSupport().generate(page)

    assert composer.calls == []
    assert page.run_calls == []
    assert page.status.warnings == [
        "Encounter-aware rotation generation blocked: canonical rotation evidence bundle "
        "is not ready for Generate: No explicit rotation demand policy is configured. "
        "Bring back: Configure reviewed demand policy."
    ]
