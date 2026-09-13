from __future__ import annotations

from dataclasses import replace

from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class RotationGenerateConditionalOutputContextProvider:
    """Decorate live Generate context with optional exact-event condition evidence.

    The wrapped application provider remains authoritative for build, encounter,
    recovery, demand, and role evidence. This adapter only asks the page for an
    optional ``canonical_runtime_output_condition_context_resolver_factory`` hook.
    When absent, the wrapped context is returned unchanged. When present, the
    factory is copied into the selected-encounter evidence inputs without
    interpreting any condition names or spatial semantics.
    """

    def __init__(self, provider) -> None:
        resolver = getattr(provider, "context_for", None)
        if not callable(resolver):
            raise TypeError("conditional output context provider requires context_for(page)")
        self.provider = provider

    def context_for(self, page) -> RotationGenerateCanonicalContext:
        context = self.provider.context_for(page)
        if not isinstance(context, RotationGenerateCanonicalContext):
            raise TypeError("wrapped Generate provider returned unsupported context type")

        hook = getattr(
            page,
            "canonical_runtime_output_condition_context_resolver_factory",
            None,
        )
        if not callable(hook):
            return context

        factory = hook()
        if factory is None:
            return context
        if not callable(factory):
            raise TypeError(
                "canonical runtime output condition context hook must return a resolver factory"
            )

        evidence_inputs = replace(
            context.evidence_inputs,
            runtime_output_condition_context_resolver_factory=factory,
        )
        return replace(context, evidence_inputs=evidence_inputs)


__all__ = ["RotationGenerateConditionalOutputContextProvider"]
