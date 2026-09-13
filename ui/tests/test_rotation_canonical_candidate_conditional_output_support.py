from __future__ import annotations

from ui.rotation_canonical_candidate_conditional_output_support import (
    RotationCanonicalCandidateConditionalOutputSupport,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class _Pipeline:
    def __init__(self) -> None:
        self.calls = []
        self.result = object()

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_conditional_output_adapter_injects_factory_without_mutating_shared_support(
    monkeypatch,
) -> None:
    pipeline = _Pipeline()
    support = object.__new__(RotationCanonicalCandidateConditionalOutputSupport)
    support.pipeline = pipeline

    observed = []

    def fake_base_run(self, **kwargs):
        observed.append((self, kwargs))
        return self.pipeline.run_effects(marker="base-call")

    monkeypatch.setattr(
        RotationCanonicalCandidateSupport,
        "run_effects",
        fake_base_run,
    )

    def resolver_factory(_plan):
        return lambda _event: frozenset()

    result = support.run_effects(
        runtime_output_condition_context_resolver_factory=resolver_factory,
        sentinel="value",
    )

    assert result is pipeline.result
    assert support.pipeline is pipeline
    assert len(observed) == 1
    bound_support, kwargs = observed[0]
    assert bound_support is not support
    assert kwargs == {"sentinel": "value"}
    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["marker"] == "base-call"
    assert (
        pipeline.calls[0]["runtime_output_condition_context_resolver_factory"]
        is resolver_factory
    )


def test_conditional_output_adapter_without_factory_uses_existing_canonical_path(
    monkeypatch,
) -> None:
    support = object.__new__(RotationCanonicalCandidateConditionalOutputSupport)
    support.pipeline = object()
    observed = []
    expected = object()

    def fake_base_run(self, **kwargs):
        observed.append((self, kwargs))
        return expected

    monkeypatch.setattr(
        RotationCanonicalCandidateSupport,
        "run_effects",
        fake_base_run,
    )

    result = support.run_effects(sentinel="unchanged")

    assert result is expected
    assert observed == [(support, {"sentinel": "unchanged"})]
