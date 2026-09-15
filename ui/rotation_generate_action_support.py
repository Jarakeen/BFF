from __future__ import annotations

from dataclasses import is_dataclass, replace
from types import MethodType
from typing import Protocol

from minmax.resource_costs import ResourceType
from services.rotation_runtime_triggered_intent_service import (
    RotationRuntimeTriggeredIntentService,
)
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

    The application provider installed by the Rotation workspace exposes advanced
    encounter-aware controls for recovery and DD target resistance. Those controls are
    optional UI policy inputs, not prerequisites for the baseline Rotation Maker. When
    they are left incomplete, Generate stays on the plain deterministic path. Once the
    advanced policy is explicitly complete, the strict canonical path remains fail-closed
    and never invents missing mechanics or evaluation facts.

    Once canonical generation is active, Generate resolves evidence for the exact
    selected encounter and either runs the canonical/cadence orchestration path or
    reports the blocking evidence. Shared bundle readiness is checked before
    role-specific evidence is composed so missing encounter/build policy cannot be
    misreported as a role-output failure. Explicit role evidence is forwarded unchanged.

    When the context owns an effective-build snapshot, that exact frozen build is used
    for role composition and orchestration. Rotation never re-resolves Team/Boss/Raid
    Plan build ownership; those decisions belong to the caller that produced the snapshot.
    Raid Plan runtime-triggered responsibilities are projected into pending execution
    intent and attached to the returned orchestration result without changing its
    seconds-based final plan. Legacy/static contexts preserve their historical call shape.
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

        # These are small action-row controls, so keep them visually consistent
        # with the Foundry's pill/chip treatment rather than full-size rectangles.
        for button in (page.generate_button, page.clear_plan_button):
            button.setProperty("compact", True)
            button.setMinimumHeight(26)
            button.style().unpolish(button)
            button.style().polish(button)

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

    @staticmethod
    def _live_application_provider(provider):
        """Find the live application provider through transparent provider decorators.

        Rotation's production context is intentionally decorated by optional evidence
        adapters. Those wrappers must not accidentally opt baseline Generate into the
        strict advanced path merely because their class name differs from the wrapped
        application provider.
        """

        current = provider
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if current.__class__.__name__ == "RotationGenerateApplicationContextProvider":
                return current
            current = getattr(current, "provider", None)
        return None

    @classmethod
    def _advanced_application_context_ready(cls, page, provider) -> bool:
        """Return whether the workspace explicitly opted into strict canonical Generate.

        Generic/static context providers keep their historical behavior. This guard only
        applies to the live application provider used by the Rotation workspace, even
        when that provider is wrapped by transparent evidence decorators. Recovery policy
        is an optional advanced stabilization feature; DD target resistance is optional
        advanced damage evidence. Leaving either unset must not disable the baseline
        Rotation Maker.
        """

        application_provider = cls._live_application_provider(provider)
        if application_provider is None:
            return True

        recovery_policy = getattr(page, "canonical_recovery_policy", None)
        if not callable(recovery_policy):
            return True
        policy = recovery_policy() or {}
        resource = policy.get("resource")
        trigger_fraction = policy.get("trigger_fraction")
        if not isinstance(resource, ResourceType) or trigger_fraction is None:
            return False

        build_getter = getattr(page, "_selected_build", None)
        build = build_getter() if callable(build_getter) else None
        role = "_".join(
            str(getattr(build, "Role", "") or "")
            .strip()
            .casefold()
            .replace("-", " ")
            .split()
        )
        if role in {"dd", "dps", "damage", "damage_dealer"}:
            dd_policy_provider = getattr(page, "canonical_dd_evaluation_policy", None)
            if callable(dd_policy_provider):
                dd_policy = dd_policy_provider() or {}
                if dd_policy.get("target_resistance") is None:
                    return False

        return True

    @staticmethod
    def _runtime_triggered_intents_for_context(context: RotationGenerateCanonicalContext):
        responsibilities = tuple(
            getattr(context, "raid_plan_triggered_responsibilities", ()) or ()
        )
        if not responsibilities:
            return ()
        plan_id = str(getattr(context, "raid_plan_id", "") or "").strip()
        seat_id = str(getattr(context, "raid_plan_seat_id", "") or "").strip()
        if not plan_id or not seat_id:
            raise ValueError(
                "Raid Plan triggered responsibilities require bound plan and seat identity"
            )
        return RotationRuntimeTriggeredIntentService().project(
            plan_id=plan_id,
            seat_id=seat_id,
            responsibilities=responsibilities,
        )

    @staticmethod
    def _attach_runtime_triggered_intents(page, result, intents):
        pending = tuple(intents)
        if not pending:
            return result
        if is_dataclass(result):
            result = replace(result, runtime_triggered_intents=pending)
        else:
            setattr(result, "runtime_triggered_intents", pending)
        if hasattr(page, "last_canonical_cadence_orchestration_result"):
            page.last_canonical_cadence_orchestration_result = result
        return result

    def generate(self, page) -> None:
        refresh_provider_scope = getattr(
            page, "_refresh_rotation_tank_provider_scope", None
        )
        if callable(refresh_provider_scope):
            refresh_provider_scope()

        context = getattr(page, "rotation_generate_canonical_context", None)
        provider = getattr(page, "rotation_generate_canonical_context_provider", None)
        if context is None and provider is not None:
            if not self._advanced_application_context_ready(page, provider):
                RotationDashboardPage.generate_rotation(page)
                return
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
            self._require_ready_bundle(bundle)
            fallback_build = None
            build_getter = getattr(page, "_selected_build", None)
            if callable(build_getter):
                fallback_build = build_getter()
            player_build = context.player_build_for(fallback_build)
            if player_build is None:
                raise ValueError(
                    "select a saved build or supply an effective build snapshot before canonical rotation generation"
                )
            role_evidence = context.role_evidence_for(
                player_build=player_build,
                evidence_bundle=bundle,
                content_type=getattr(bundle, "content_type", ""),
            )
            runtime_triggered_intents = self._runtime_triggered_intents_for_context(context)
            orchestration_kwargs = {
                "role_evidence": role_evidence,
                "cadence_obligations": context.cadence_obligations,
                "cadence_priorities": context.cadence_priorities,
                "cadence_evaluation_context": context.cadence_evaluation_context,
                "cadence_max_iterations": context.cadence_max_iterations,
                "character_id": context.character_id,
            }
            if context.effective_build is not None:
                orchestration_kwargs["player_build"] = player_build
            result = page.run_canonical_cadence_orchestration(
                bundle,
                **orchestration_kwargs,
            )
            result = self._attach_runtime_triggered_intents(
                page,
                result,
                runtime_triggered_intents,
            )
        except (OSError, ValueError) as exc:
            page.status.warning(f"Encounter-aware rotation generation blocked: {exc}")
            return

        if result.final_plan is None:
            reasons = self._canonical_validation_reasons(result)
            if reasons:
                page.status.warning(
                    "Canonical rotation not selected: " + "; ".join(reasons)
                )
            return

        if result.cadence_evidence is None:
            encounter_id = page.selected_encounter_id()
            scope = f" for {encounter_id}" if encounter_id else ""
            page.status.info(f"Canonical rotation generated{scope}.")

    @staticmethod
    def _canonical_validation_reasons(result) -> tuple[str, ...]:
        canonical_result = getattr(result, "canonical_result", None)
        candidate_result = getattr(canonical_result, "candidate_result", None)
        validation = getattr(candidate_result, "validation", None)
        return tuple(
            dict.fromkeys(
                str(item).strip()
                for item in getattr(validation, "reasons", ())
                if str(item).strip()
            )
        )

    @staticmethod
    def _require_ready_bundle(bundle) -> None:
        if bool(getattr(bundle, "ready", True)):
            return
        details = [
            str(item).strip()
            for item in getattr(bundle, "unresolved", ())
            if str(item).strip()
        ]
        blocking_gaps = getattr(bundle, "blocking_knowledge_gaps", None)
        if blocking_gaps is None:
            blocking_gaps = tuple(
                gap
                for gap in getattr(bundle, "knowledge_gaps", ())
                if bool(getattr(gap, "blocking", True))
            )
        for gap in blocking_gaps:
            summary = str(getattr(gap, "summary", "") or "").strip()
            needed = str(getattr(gap, "needed_evidence", "") or "").strip()
            if summary and needed:
                details.append(f"{summary} Bring back: {needed}")
            elif summary:
                details.append(summary)
        detail = "; ".join(details) or "unspecified unresolved evidence"
        raise ValueError(
            "canonical rotation evidence bundle is not ready for Generate: " + detail
        )


def install_rotation_generate_action(page) -> RotationGenerateActionSupport:
    support = RotationGenerateActionSupport()
    support.install(page)
    return support


__all__ = [
    "RotationGenerateActionSupport",
    "RotationGenerateCanonicalContextProvider",
    "install_rotation_generate_action",
]
