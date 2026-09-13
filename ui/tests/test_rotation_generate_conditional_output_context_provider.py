from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext
from ui.rotation_generate_conditional_output_context_provider import (
    RotationGenerateConditionalOutputContextProvider,
)
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


def _context() -> RotationGenerateCanonicalContext:
    return RotationGenerateCanonicalContext(
        evidence_inputs=RotationSelectedEncounterEvidenceInputs(
            demand_policies=(),
            evaluator_resolver=None,
            scorecard_resolver=None,
            resource=ResourceType.MAGICKA,
            maximum_amount=30000,
            trigger_fraction=0.30,
        ),
        character_id="character-1",
    )


class _Provider:
    def __init__(self, context=None) -> None:
        self.context = context if context is not None else _context()
        self.calls = []

    def context_for(self, page):
        self.calls.append(page)
        return self.context


def test_missing_page_hook_returns_wrapped_context_unchanged() -> None:
    wrapped = _Provider()
    provider = RotationGenerateConditionalOutputContextProvider(wrapped)
    page = SimpleNamespace()

    context = provider.context_for(page)

    assert context is wrapped.context
    assert wrapped.calls == [page]
    assert context.evidence_inputs.runtime_output_condition_context_resolver_factory is None


def test_page_hook_none_returns_wrapped_context_unchanged() -> None:
    wrapped = _Provider()
    provider = RotationGenerateConditionalOutputContextProvider(wrapped)
    page = SimpleNamespace(
        canonical_runtime_output_condition_context_resolver_factory=lambda: None
    )

    context = provider.context_for(page)

    assert context is wrapped.context


def test_page_hook_factory_is_copied_into_evidence_inputs_without_other_changes() -> None:
    wrapped = _Provider()
    provider = RotationGenerateConditionalOutputContextProvider(wrapped)

    def factory(_plan):
        return lambda _event: frozenset({"condition_a"})

    page = SimpleNamespace(
        canonical_runtime_output_condition_context_resolver_factory=lambda: factory
    )

    context = provider.context_for(page)

    assert context is not wrapped.context
    assert context.character_id == wrapped.context.character_id
    assert context.evidence_inputs is not wrapped.context.evidence_inputs
    assert (
        context.evidence_inputs.runtime_output_condition_context_resolver_factory
        is factory
    )
    assert context.evidence_inputs.resource is ResourceType.MAGICKA
    assert context.evidence_inputs.maximum_amount == 30000
    assert context.evidence_inputs.trigger_fraction == 0.30


def test_non_callable_hook_result_is_rejected() -> None:
    provider = RotationGenerateConditionalOutputContextProvider(_Provider())
    page = SimpleNamespace(
        canonical_runtime_output_condition_context_resolver_factory=lambda: object()
    )

    with pytest.raises(TypeError, match="resolver factory"):
        provider.context_for(page)


def test_wrapped_provider_must_return_canonical_context() -> None:
    provider = RotationGenerateConditionalOutputContextProvider(_Provider(context=object()))

    with pytest.raises(TypeError, match="unsupported context type"):
        provider.context_for(SimpleNamespace())
