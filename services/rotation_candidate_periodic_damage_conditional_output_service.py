from __future__ import annotations

"""Apply reviewed runtime output conditions after periodic event scheduling.

The periodic scheduler owns source-time event production only. This bridge sits above
that scheduler and filters each exact projected event through the shared rotation
runtime output eligibility service. It deliberately does not calculate geometry,
target position, cadence, or any skill-specific mechanic.
"""

from dataclasses import replace

from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeProjection,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionContextResolver,
    RotationRuntimeOutputEligibilityService,
)


class RotationCandidatePeriodicDamageConditionalOutputService:
    """Filter scheduled periodic output through exact-event condition evidence.

    Components with no reviewed output-condition rule pass through unchanged.
    Reviewed conditional components fail closed when exact-event ``ConditionContext``
    is unavailable. Known-unsatisfied events are omitted; unresolved condition facts
    are preserved on the projection entry so downstream damage evidence cannot claim
    a complete value.
    """

    def __init__(
        self,
        projection_service: RotationCandidatePeriodicDamageRuntimeProjectionService,
        *,
        output_eligibility_service: RotationRuntimeOutputEligibilityService | None = None,
        condition_context_resolver: (
            RotationRuntimeOutputConditionContextResolver | None
        ) = None,
    ) -> None:
        self.projection_service = projection_service
        self.output_eligibility_service = (
            output_eligibility_service or RotationRuntimeOutputEligibilityService()
        )
        self.condition_context_resolver = condition_context_resolver

    def project(
        self,
        *,
        plan,
        semantics: tuple[RotationPeriodicDamageRuntimeSemantics, ...],
    ) -> RotationPeriodicDamageRuntimeProjection:
        projection = self.projection_service.project(
            plan=plan,
            semantics=semantics,
        )

        filtered_entries = []
        for entry in projection.entries:
            action_name = str(entry.action.name or "").strip()
            if not action_name:
                filtered_entries.append(
                    replace(
                        entry,
                        events=(),
                        unresolved=tuple(
                            dict.fromkeys(
                                (
                                    *entry.unresolved,
                                    "periodic conditional output requires canonical parent skill identity",
                                )
                            )
                        ),
                    )
                )
                continue

            filtered = self.output_eligibility_service.filter_events(
                skill_entity_id=action_name,
                coefficient_number=entry.coefficient_number,
                events=entry.events,
                condition_context_resolver=self.condition_context_resolver,
            )
            filtered_entries.append(
                replace(
                    entry,
                    events=filtered.events,
                    evidence=tuple(
                        dict.fromkeys((*entry.evidence, *filtered.evidence))
                    ),
                    unresolved=tuple(
                        dict.fromkeys((*entry.unresolved, *filtered.unresolved))
                    ),
                )
            )

        return RotationPeriodicDamageRuntimeProjection(
            entries=tuple(filtered_entries),
            unresolved=projection.unresolved,
        )


__all__ = ["RotationCandidatePeriodicDamageConditionalOutputService"]
