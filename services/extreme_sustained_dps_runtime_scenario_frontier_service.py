from __future__ import annotations

"""Scenario-facing builder for the canonical Objective #32 runtime_state frontier."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService,
)
from services.extreme_sustained_dps_runtime_external_history_assembly_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService,
)
from services.extreme_sustained_dps_runtime_external_history_frontier_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult,
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeScenarioFrontierResult:
    runtime: ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def frontier(self):
        return self.runtime.frontier


class ExtremeSustainedDPSRuntimeScenarioFrontierService:
    """Compose all finite runtime-state evidence layers for one finalized plan."""

    def __init__(
        self,
        *,
        external_history_frontier: (
            ExtremeSustainedDPSRuntimeExternalHistoryFrontierService | None
        ) = None,
    ) -> None:
        self.external_history_frontier = (
            external_history_frontier
            or ExtremeSustainedDPSRuntimeExternalHistoryFrontierService()
        )

    def build(
        self,
        *,
        plan,
        player_build: PlayerBuild,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
        event_denominator_proven: bool,
        supplemental_histories: tuple[
            ExtremeSustainedDPSRuntimeExternalHistoryChoice,
            ...,
        ] = (),
        supplemental_denominator_proven: bool,
        source: str,
        initial_bar: str = "front",
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeScenarioFrontierResult:
        attempts = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
            events=tuple(events),
            effects=tuple(effects),
            event_denominator_proven=bool(event_denominator_proven),
            source=f"{source}: runtime event skeletons",
        )
        assembled = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
            attempt_frontier=attempts,
            supplemental_histories=tuple(supplemental_histories),
            supplemental_denominator_proven=bool(
                supplemental_denominator_proven
            ),
            source=f"{source}: supplemental runtime history",
        )
        runtime = self.external_history_frontier.build(
            plan=plan,
            player_build=player_build,
            external_histories=tuple(assembled.choices),
            denominator_proven=bool(assembled.denominator_proven),
            source=source,
            initial_bar=initial_bar,
            omitted_scope=tuple(omitted_scope),
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *tuple(attempts.unresolved),
                    *tuple(assembled.unresolved),
                    *tuple(runtime.unresolved),
                )
            )
        )
        return ExtremeSustainedDPSRuntimeScenarioFrontierResult(
            runtime=runtime,
            evidence=(
                *tuple(attempts.evidence),
                *tuple(assembled.evidence),
                *tuple(runtime.evidence),
                (
                    "Objective #32 runtime_state scenario frontier is closure-ready"
                    if runtime.frontier.denominator_proven
                    and not runtime.frontier.omitted_scope
                    and not unresolved
                    else "Objective #32 runtime_state scenario frontier remains open"
                ),
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeScenarioFrontierResult",
    "ExtremeSustainedDPSRuntimeScenarioFrontierService",
]
