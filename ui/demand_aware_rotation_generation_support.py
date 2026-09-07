from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationResult,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


@dataclass(frozen=True)
class DemandAwareRotationGenerationRequest:
    """Explicit demand-aware inputs layered over the existing Phase 13 request."""

    base_request: RotationGenerationRequest
    priorities: AbilityPriorityList
    demands: tuple[RotationDemandWindow, ...]
    demand_refresh_leads: tuple[DemandRefreshLead, ...] = ()


class DemandAwareRotationGenerationSupport:
    """Generate through the existing Phase 13 stack with encounter demand context.

    This wrapper is intentionally additive. Existing dashboard callers remain on
    ``RotationGenerationSupport``. Callers that have a fully resolved priority list
    with encounter-demand overrides can opt into this path without teaching the
    base request to infer role semantics or encounter timing.
    """

    def __init__(self, base: RotationGenerationSupport | None = None) -> None:
        self.base = base or RotationGenerationSupport()

    def generate(self, *, build, request: DemandAwareRotationGenerationRequest):
        return self.generate_with_evidence(build=build, request=request).plan

    def generate_with_evidence(
        self,
        *,
        build,
        request: DemandAwareRotationGenerationRequest,
    ) -> RotationGenerationResult:
        if request.base_request.stabilize_recovery_heavies:
            return self._generate_stabilized(build=build, request=request)
        return self._generate_once(build=build, request=request)

    def _definition_request(
        self,
        request: DemandAwareRotationGenerationRequest,
    ) -> RotationGenerationRequest:
        return replace(
            request.base_request,
            ability_priorities=tuple(request.priorities.entries),
        )

    def _generate_once(
        self,
        *,
        build,
        request: DemandAwareRotationGenerationRequest,
    ) -> RotationGenerationResult:
        base_request = self._definition_request(request)
        definition = self.base.build_definition(build=build, request=base_request)
        wait_decision = self.base._wait_decision(build=build, request=base_request)
        seed_plan = self.base.planner.build_plan(definition, build)

        refinement = self.base.duration_refinement.refine(
            seed_plan,
            priorities=request.priorities,
            wait_decision=wait_decision,
            demands=tuple(request.demands),
            demand_refresh_leads=tuple(request.demand_refresh_leads),
        )

        final_plan = refinement.plan
        ultimate_projection = None
        selected_ultimate_bar = str(base_request.ultimate_bar or "").strip().casefold()
        if selected_ultimate_bar:
            ultimate_projection = self.base.ultimate_service.apply_generation(
                build=build,
                plan=final_plan,
                ultimate_bar=selected_ultimate_bar,
                starting_ultimate=float(base_request.starting_ultimate),
                use_scheduled_combat_attacks=bool(
                    base_request.use_scheduled_combat_attacks_for_ultimate
                ),
            )
            final_plan = ultimate_projection.plan
            evidence = self.base.duration_evidence.build(final_plan)
        else:
            evidence = self.base.duration_evidence.from_projection(
                refinement.duration_projection
            )

        return RotationGenerationResult(
            plan=final_plan,
            duration_evidence=evidence,
            ultimate_projection=ultimate_projection,
        )

    def _generate_stabilized(
        self,
        *,
        build,
        request: DemandAwareRotationGenerationRequest,
    ) -> RotationGenerationResult:
        base_request = request.base_request
        maximum = base_request.recovery_maximum_amount
        trigger = base_request.recovery_trigger_fraction
        restore = base_request.recovery_restoration_resolver
        if maximum is None or int(maximum) <= 0:
            raise ValueError(
                "recovery-heavy stabilization requires a positive recovery_maximum_amount"
            )
        if trigger is None or not 0 <= float(trigger) <= 1:
            raise ValueError(
                "recovery-heavy stabilization requires recovery_trigger_fraction between 0 and 1"
            )
        if restore is None:
            raise ValueError(
                "recovery-heavy stabilization requires a verified recovery_restoration_resolver"
            )

        generated_results: list[RotationGenerationResult] = []

        def generate(pressure_resolver):
            iteration_base = replace(
                base_request,
                stabilize_recovery_heavies=False,
                recovery_pressure_resolver=pressure_resolver,
            )
            iteration_request = replace(request, base_request=iteration_base)
            result = self._generate_once(build=build, request=iteration_request)
            generated_results.append(result)
            return result.plan

        stabilization: RotationRecoveryHeavyStabilizationResult = (
            self.base.recovery_stabilization.stabilize(
                build=build,
                generate=generate,
                resource=base_request.recovery_stabilization_resource,
                maximum_amount=int(maximum),
                trigger_fraction=float(trigger),
                restoration_resolver=restore,
                reserve_assessment_resolver=base_request.recovery_reserve_assessment_resolver,
                max_iterations=int(base_request.recovery_stabilization_max_iterations),
            )
        )
        if not generated_results:
            raise RuntimeError("recovery-heavy stabilization produced no generation pass")

        final_generated = generated_results[-1]
        return RotationGenerationResult(
            plan=stabilization.plan,
            duration_evidence=final_generated.duration_evidence,
            ultimate_projection=final_generated.ultimate_projection,
            recovery_stabilization=stabilization,
        )
