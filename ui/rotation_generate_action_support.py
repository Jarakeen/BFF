from __future__ import annotations

from types import MethodType
from typing import Protocol

from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class RotationGenerateCanonicalContextProvider(Protocol):
    """Resolve the exact canonical Generate context from current page state."""

    def context_for(self, page) -> RotationGenerateCanonicalContext: ...


class RotationGenerateActionSupport:
    """Route Generate Rotation through plain or encounter-aware execution explicitly.

    Installing this support does not opt a page into canonical generation. The legacy
    deterministic generator remains active until a caller supplies either a static
    ``RotationGenerateCanonicalContext`` or a context provider. Providers are resolved
    at click time so selected build, encounter, and explicit policy controls cannot go
    stale after the page is constructed.

    Once configured, Generate resolves evidence for the exact selected encounter and
    either runs the canonical/cadence orchestration path or reports the blocking
    evidence. Explicit role evidence is forwarded unchanged. When authoritative
    plan-evidence inputs or a canonical composer are configured, the router composes
    role evidence from the selected saved build and resolved encounter bundle. It never
    derives healer reliability or assignment exceptions from display state. It never
    silently falls back to the plain generator for a configured encounter-aware request.
    """

    def install(self, page) -> None:
        page.rotation_generate_canonical_context = None
        page.rotation_generate_canonical_context_provider = None
        page.rotation_generate_action_support = self
        page.set_rotation_generate_canonical_context = MethodType(
            lambda bound_page, context: self.set_context(bound_page, context),
            page,
        )
        page.set_rotation_generate_canonical_context_provider = MethodType(
            lambda bound_page, provider: self.set_context_provider(bound_page, provider),
            page,
        )
        page.clear_rotation_generate_canonical_context = MethodType(
            lambda bound_page: self.clear_context(bound_page),
            page,
        )
        page.clear_rotation_generate_canonical_context_provider = MethodType(
            lambda bound_page: self.clear_context_provider(bound_page),
            page,
        )

        # The base dashboard connected Generate before the canonical selector was
        # installed. Replace that connection with this explicit router.
        try:
            page.generate_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        page.generate_button.clicked.connect(lambda: self.generate(page))

    @staticmethod
    def set_context(page, context: RotationGenerateCanonicalContext) -> None:
        if not isinstance(context, RotationGenerateCanonicalContext):
            raise TypeError("rotation generate canonical context has an unsupported type")
        page.rotation_generate_canonical_context_provider = None
        page.rotation_generate_canonical_context = context

    @staticmethod
    def set_context_provider(
        page,
        provider: RotationGenerateCanonicalContextProvider,
    ) -> None:
        resolver = getattr(provider, "context_for", None)
        if not callable(resolver):
            raise TypeError(
                "rotation generate canonical context provider must expose context_for(page)"
            )
        page.rotation_generate_canonical_context = None
        page.rotation_generate_canonical_context_provider = provider

    @staticmethod
    def clear_context(page) -> None:
        page.rotation_generate_canonical_context = None

    @staticmethod
    def clear_context_provider(page) -> None:
        page.rotation_generate_canonical_context_provider = None

    def generate(self, page) -> None:
        context = getattr(page, "rotation_generate_canonical_context", None)
        provider = getattr(page, "rotation_generate_canonical_context_provider", None)
        if context is None and provider is not None:
            try:
                context = provider.context_for(page)
            except (OSError, ValueError) as exc:
                page.status.warning(
                    f"Encounter-aware rotation generation blocked: {exc}"
                )
                return
            if not isinstance(context, RotationGenerateCanonicalContext):
                raise TypeError(
                    "rotation generate canonical context provider returned an unsupported type"
                )

        if context is None:
            RotationDashboardPage.generate_rotation(page)
            return

        try:
            bundle = page.selected_encounter_evidence_bundle(context.evidence_inputs)
            player_build = None
            if (
                context.role_evidence_inputs is not None
                or context.role_evidence_composer is not None
            ):
                player_build = page._selected_build()
                if player_build is None:
                    raise ValueError(
                        "select a saved build before composing canonical role evidence"
                    )
            role_evidence = context.role_evidence_for(
                player_build=player_build,
                evidence_bundle=bundle,
                content_type=getattr(bundle, "content_type", ""),
            )
            result = page.run_canonical_cadence_orchestration(
                bundle,
                role_evidence=role_evidence,
                cadence_obligations=context.cadence_obligations,
                cadence_priorities=context.cadence_priorities,
                cadence_evaluation_context=context.cadence_evaluation_context,
                cadence_max_iterations=context.cadence_max_iterations,
                character_id=context.character_id,
            )
        except (OSError, ValueError) as exc:
            page.status.warning(f"Encounter-aware rotation generation blocked: {exc}")
            return

        if result.final_plan is not None and result.cadence_evidence is None:
            encounter_id = page.selected_encounter_id()
            scope = f" for {encounter_id}" if encounter_id else ""
            page.status.info(f"Canonical rotation generated{scope}.")



def install_rotation_generate_action(page) -> RotationGenerateActionSupport:
    support = RotationGenerateActionSupport()
    support.install(page)
    return support


__all__ = [
    "RotationGenerateActionSupport",
    "RotationGenerateCanonicalContextProvider",
    "install_rotation_generate_action",
]
