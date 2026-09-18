from __future__ import annotations

"""Stable Phase 14 Rotation runtime bridge.

This service exposes already-reviewed Rotation engine behavior to the owned Phase 14
page without monkey-patching UI objects or depending on the legacy dashboard shape.
"""

from dataclasses import dataclass, replace

from engine.config import get_data_dir
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from services.rotation_sustain_service import RotationSustainProjection
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


@dataclass(frozen=True)
class Phase14RotationRuntimeResult:
    generation: RotationGenerationResult
    resource: ResourceType
    recovery_projection: RotationSustainProjection | None = None


class Phase14RotationRuntimeService:
    """Call stable Rotation engine seams directly from the Phase 14 page."""

    def __init__(
        self,
        *,
        generation: RotationGenerationSupport | None = None,
        static_context: RotationStaticBuildContextService | None = None,
        heavy_sustain: RotationHeavySustainProjectionService | None = None,
        character_adapter: SavedBuildCharacterAdapter | None = None,
    ) -> None:
        self.generation = generation or RotationGenerationSupport()
        self.static_context = static_context or RotationStaticBuildContextService()
        self.heavy_sustain = heavy_sustain or RotationHeavySustainProjectionService(
            progression_adapter=self.static_context.progression_adapter
        )
        self.character_adapter = character_adapter or SavedBuildCharacterAdapter(
            get_data_dir() / "eso.db"
        )

    @staticmethod
    def _initial_bar(build: PlayerBuild) -> str:
        front = tuple(getattr(build, "FrontBarSkills", ()) or ())[:5]
        return "front" if any(str(skill or "").strip() for skill in front) else "back"

    def _resource(
        self,
        *,
        build: PlayerBuild,
        static_context,
        initial_bar: str,
        explicit: ResourceType | None,
    ) -> ResourceType:
        if explicit is not None:
            return explicit
        magicka = static_context.maximum_amount_for(initial_bar, ResourceType.MAGICKA)
        stamina = static_context.maximum_amount_for(initial_bar, ResourceType.STAMINA)
        return ResourceType.MAGICKA if magicka >= stamina else ResourceType.STAMINA

    def generate(
        self,
        *,
        build: PlayerBuild,
        request: RotationGenerationRequest,
        heavy_behavior: str,
        reserve_fraction: float,
        explicit_resource: ResourceType | None = None,
    ) -> Phase14RotationRuntimeResult:
        """Generate one plan, optionally using the reviewed recovery-heavy fixed point.

        Required-effect healer Heavy Attacks remain available through the baseline
        generator even when recovery stabilization is disabled. Resource-pressure
        Heavy Attacks are enabled only for the two explicit sustain behaviors.
        """

        behavior = str(heavy_behavior or "").strip()
        initial_bar = self._initial_bar(build)
        static_context = self.static_context.resolve(build)

        if not static_context.contexts:
            # Baseline generation remains useful when full static sustain context is
            # unavailable. Fail closed only for recovery-heavy stabilization.
            result = self.generation.generate_with_evidence(
                build=build,
                request=request,
            )
            fallback_resource = explicit_resource or ResourceType.MAGICKA
            return Phase14RotationRuntimeResult(
                generation=result,
                resource=fallback_resource,
                recovery_projection=None,
            )

        resource = self._resource(
            build=build,
            static_context=static_context,
            initial_bar=initial_bar,
            explicit=explicit_resource,
        )

        if behavior not in {"Use when needed", "Prefer safe windows"}:
            result = self.generation.generate_with_evidence(
                build=build,
                request=request,
            )
            return Phase14RotationRuntimeResult(
                generation=result,
                resource=resource,
                recovery_projection=None,
            )

        maximum_amount = static_context.maximum_amount_for(initial_bar, resource)
        if maximum_amount <= 0:
            raise ValueError("sustain Heavy Attacks require a positive resource maximum")

        trigger_fraction = float(reserve_fraction)
        if not 0.0 <= trigger_fraction <= 1.0:
            raise ValueError("resource reserve must be between 0% and 100%")

        adaptation = self.character_adapter.adapt(
            build,
            character_id=str(
                getattr(static_context.progression, "character_id", "") or ""
            ).strip() or None,
        )
        if adaptation.build is None:
            detail = "; ".join(adaptation.unresolved) or "canonical build adaptation failed"
            raise ValueError("sustain Heavy Attacks unavailable: " + detail)
        character_build = adaptation.build

        generated_results: list[RotationGenerationResult] = []

        def generate(pressure_resolver):
            iteration_request = replace(
                request,
                stabilize_recovery_heavies=False,
                recovery_pressure_resolver=pressure_resolver,
            )
            result = self.generation.generate_with_evidence(
                build=build,
                request=iteration_request,
            )
            generated_results.append(result)
            return result.plan

        def restoration_factory(plan):
            completion = self.heavy_sustain.completion_evidence_from_verified_reservations(
                plan
            )
            return self.heavy_sustain.restoration_resolver_for_plan(
                character_build=character_build,
                sustain_build=build,
                plan=plan,
                resource=resource,
                initial_bar=initial_bar,
                completion_evidence=completion,
            )

        stabilization = self.generation.recovery_stabilization.stabilize(
            build=build,
            generate=generate,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver_factory=restoration_factory,
            max_iterations=6,
            calculation_context=static_context.context_for(initial_bar),
            maximum_event_resolver=(
                lambda plan, tracked_resource: static_context.maximum_events_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
            displayed_recovery_resolver_factory=(
                lambda plan, tracked_resource: static_context.displayed_recovery_resolver_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
        )
        if not generated_results:
            raise RuntimeError(
                "sustain Heavy Attack stabilization produced no generation pass"
            )

        final_generated = generated_results[-1]
        generation = RotationGenerationResult(
            plan=stabilization.plan,
            duration_evidence=final_generated.duration_evidence,
            ultimate_projection=final_generated.ultimate_projection,
            recovery_stabilization=stabilization,
        )
        return Phase14RotationRuntimeResult(
            generation=generation,
            resource=resource,
            recovery_projection=stabilization.replay.final_projection,
        )


__all__ = [
    "Phase14RotationRuntimeResult",
    "Phase14RotationRuntimeService",
]
