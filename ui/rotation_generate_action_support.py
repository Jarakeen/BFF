from __future__ import annotations

from types import MethodType

from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class RotationGenerateActionSupport:
    """Route Generate Rotation through plain or encounter-aware execution explicitly.

    Installing this support does not opt a page into canonical generation. The legacy
    deterministic generator remains active until a caller supplies a
    ``RotationGenerateCanonicalContext``. Once configured, Generate resolves evidence
    for the exact selected encounter and either runs the canonical/cadence orchestration
    path or reports the blocking evidence. Explicit role evidence is forwarded
    unchanged. When authoritative plan-evidence inputs are configured, the router
    composes role evidence from those inputs, the saved build's explicit role, and
    the selected encounter's persisted content type. It never derives healer
    reliability or assignment exceptions from display state. It never
    silently falls back to the plain generator for a configured encounter-aware request.
    """

    def install(self, page) -> None:
        page.rotation_generate_canonical_context = None
        page.rotation_generate_action_support = self
        page.set_rotation_generate_canonical_context = MethodType(
            lambda bound_page, context: self.set_context(bound_page, context),
            page,
        )
        page.clear_rotation_generate_canonical_context = MethodType(
            lambda bound_page: self.clear_context(bound_page),
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
        page.rotation_generate_canonical_context = context

    @staticmethod
    def clear_context(page) -> None:
        page.rotation_generate_canonical_context = None

    def generate(self, page) -> None:
        context = getattr(page, "rotation_generate_canonical_context", None)
        if context is None:
            RotationDashboardPage.generate_rotation(page)
            return

        try:
            bundle = page.selected_encounter_evidence_bundle(context.evidence_inputs)
            player_build = None
            if context.role_evidence_inputs is not None:
                player_build = page._selected_build()
                if player_build is None:
                    raise ValueError(
                        "select a saved build before composing canonical role evidence"
                    )
            role_evidence = context.role_evidence_for(
                player_build=player_build,
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
    "install_rotation_generate_action",
]
