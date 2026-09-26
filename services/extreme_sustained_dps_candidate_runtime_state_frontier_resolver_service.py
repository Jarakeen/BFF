from __future__ import annotations

"""Resolve Objective #32 runtime_state separately for each finalized generated branch."""

from dataclasses import dataclass
from typing import Callable

from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierResult,
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevance,
)
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingResult,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


CandidateEvidenceResolver = Callable[[object], object]


@dataclass(frozen=True)
class ExtremeSustainedDPSCandidateRuntimeStateResolution:
    frontier: object
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    relevance: ExtremeSustainedDPSRuntimeEffectRelevance | None = None
    scaling: ExtremeSustainedDPSRuntimeEffectScalingResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple):
            raise TypeError("candidate runtime-state resolution evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("candidate runtime-state resolution unresolved evidence must be a tuple")
        if self.relevance is not None and not isinstance(
            self.relevance, ExtremeSustainedDPSRuntimeEffectRelevance
        ):
            raise TypeError("candidate runtime-state relevance must be canonical when supplied")
        if self.scaling is not None and not isinstance(
            self.scaling, ExtremeSustainedDPSRuntimeEffectScalingResult
        ):
            raise TypeError("candidate runtime-state scaling must be canonical when supplied")


class ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService:
    """Build one candidate-scoped runtime_state frontier from the final pipeline witness."""

    def __init__(
        self,
        *,
        scenario_frontier: ExtremeSustainedDPSRuntimeScenarioFrontierService,
        occurrence_provider_resolver: CandidateEvidenceResolver | None = None,
        supplemental_event_resolver: CandidateEvidenceResolver | None = None,
        supplemental_event_denominator_proven: bool = False,
        supplemental_history_resolver: CandidateEvidenceResolver | None = None,
        supplemental_history_denominator_proven: bool = False,
        weapon_poison_consequence_resolver_resolver: CandidateEvidenceResolver | None = None,
        source: str = "Objective #32 candidate runtime scenario",
    ) -> None:
        if scenario_frontier is None:
            raise ValueError(
                "candidate runtime-state resolver requires scenario frontier service"
            )
        if not callable(getattr(scenario_frontier, "build_from_candidate", None)):
            raise TypeError(
                "candidate runtime-state resolver requires scenario frontier build_from_candidate()"
            )

        resolvers = {
            "occurrence_provider_resolver": occurrence_provider_resolver,
            "supplemental_event_resolver": supplemental_event_resolver,
            "supplemental_history_resolver": supplemental_history_resolver,
            "weapon_poison_consequence_resolver_resolver": (
                weapon_poison_consequence_resolver_resolver
            ),
        }
        for label, resolver in resolvers.items():
            if resolver is not None and not callable(resolver):
                raise TypeError(
                    f"candidate runtime-state {label} must be callable when provided"
                )

        if not isinstance(supplemental_event_denominator_proven, bool):
            raise TypeError(
                "candidate runtime-state supplemental_event_denominator_proven must be boolean"
            )
        if not isinstance(supplemental_history_denominator_proven, bool):
            raise TypeError(
                "candidate runtime-state supplemental_history_denominator_proven must be boolean"
            )

        self.scenario_frontier = scenario_frontier
        self.occurrence_provider_resolver = occurrence_provider_resolver
        self.supplemental_event_resolver = supplemental_event_resolver
        self.supplemental_event_denominator_proven = (
            supplemental_event_denominator_proven
        )
        self.supplemental_history_resolver = supplemental_history_resolver
        self.supplemental_history_denominator_proven = (
            supplemental_history_denominator_proven
        )
        self.weapon_poison_consequence_resolver_resolver = (
            weapon_poison_consequence_resolver_resolver
        )
        self.source = str(source or "").strip() or "Objective #32 candidate runtime scenario"

    @staticmethod
    def _final_candidate(state: object):
        finalized_potion = getattr(state, "finalized_potion", None)
        candidate = getattr(finalized_potion, "candidate", None)
        if candidate is not None:
            return candidate
        runtime = getattr(state, "runtime", None)
        return getattr(runtime, "current_candidate", None)

    @staticmethod
    def _assembled_build(state: object):
        late = getattr(state, "late", None)
        assembled = getattr(late, "assembled", None)
        return None if assembled is None else getattr(assembled, "build", None)

    @staticmethod
    def _resolve_optional(resolver, state, default):
        if resolver is None:
            return default
        value = resolver(state)
        return default if value is None else value

    def resolve(
        self,
        state: object,
    ) -> ExtremeSustainedDPSCandidateRuntimeStateResolution:
        complete = getattr(state, "complete", False)
        if not isinstance(complete, bool):
            raise TypeError("candidate runtime-state pipeline complete flag must be boolean")
        if not complete:
            raise ValueError(
                "candidate runtime-state resolution requires complete finalized pipeline state"
            )

        candidate = self._final_candidate(state)
        build = self._assembled_build(state)
        if candidate is None or build is None:
            missing = []
            if candidate is None:
                missing.append("final generated candidate")
            if build is None:
                missing.append("assembled build")
            raise ValueError(
                "candidate runtime-state resolution is missing "
                + ", ".join(missing)
            )

        occurrence_provider = self._resolve_optional(
            self.occurrence_provider_resolver,
            state,
            None,
        )
        supplemental_events = self._resolve_optional(
            self.supplemental_event_resolver,
            state,
            (),
        )
        if not isinstance(supplemental_events, tuple):
            raise TypeError("candidate runtime-state supplemental events must be a tuple")
        supplemental_histories = self._resolve_optional(
            self.supplemental_history_resolver,
            state,
            (),
        )
        if not isinstance(supplemental_histories, tuple):
            raise TypeError("candidate runtime-state supplemental histories must be a tuple")
        if not all(
            isinstance(row, ExtremeSustainedDPSRuntimeExternalHistoryChoice)
            for row in supplemental_histories
        ):
            raise ValueError(
                "candidate runtime-state supplemental history resolver returned invalid choice type"
            )

        weapon_poison_consequence_resolver = self._resolve_optional(
            self.weapon_poison_consequence_resolver_resolver,
            state,
            None,
        )

        result: ExtremeSustainedDPSRuntimeScenarioFrontierResult = (
            self.scenario_frontier.build_from_candidate(
                candidate=candidate,
                player_build=build,
                effects=None,
                occurrence_provider=occurrence_provider,
                target_identity=str(getattr(state, "target_identity", "") or "").strip() or None,
                supplemental_events=supplemental_events,
                supplemental_event_denominator_proven=(
                    self.supplemental_event_denominator_proven
                ),
                supplemental_histories=supplemental_histories,
                supplemental_denominator_proven=(
                    self.supplemental_history_denominator_proven
                ),
                source=self.source,
                weapon_poison_consequence_resolver=(
                    weapon_poison_consequence_resolver
                ),
            )
        )
        if not isinstance(result, ExtremeSustainedDPSRuntimeScenarioFrontierResult):
            raise TypeError("candidate runtime-state scenario frontier must return canonical result")
        return ExtremeSustainedDPSCandidateRuntimeStateResolution(
            frontier=result.frontier,
            evidence=(
                f"Candidate runtime_state resolved for {getattr(candidate, 'candidate_id', '(unknown)')}",
                *tuple(result.evidence),
            ),
            unresolved=tuple(result.unresolved),
            relevance=result.relevance,
            scaling=result.scaling,
        )


__all__ = [
    "CandidateEvidenceResolver",
    "ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService",
    "ExtremeSustainedDPSCandidateRuntimeStateResolution",
]
