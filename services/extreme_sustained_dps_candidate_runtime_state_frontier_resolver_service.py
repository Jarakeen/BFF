from __future__ import annotations

"""Resolve Objective #32 runtime_state separately for each finalized generated branch."""

from dataclasses import dataclass
from typing import Callable

from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierResult,
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


CandidateEvidenceResolver = Callable[[object], object]


@dataclass(frozen=True)
class ExtremeSustainedDPSCandidateRuntimeStateResolution:
    frontier: object
    effects: tuple[object, ...]
    effect_denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


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
        source: str = "Objective #32 candidate runtime scenario",
    ) -> None:
        if scenario_frontier is None:
            raise ValueError(
                "candidate runtime-state resolver requires scenario frontier service"
            )
        self.scenario_frontier = scenario_frontier
        self.occurrence_provider_resolver = occurrence_provider_resolver
        self.supplemental_event_resolver = supplemental_event_resolver
        self.supplemental_event_denominator_proven = bool(
            supplemental_event_denominator_proven
        )
        self.supplemental_history_resolver = supplemental_history_resolver
        self.supplemental_history_denominator_proven = bool(
            supplemental_history_denominator_proven
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
        if not bool(getattr(state, "complete", False)):
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
        supplemental_events = tuple(
            self._resolve_optional(
                self.supplemental_event_resolver,
                state,
                (),
            )
        )
        supplemental_histories = tuple(
            self._resolve_optional(
                self.supplemental_history_resolver,
                state,
                (),
            )
        )
        if not all(
            isinstance(row, ExtremeSustainedDPSRuntimeExternalHistoryChoice)
            for row in supplemental_histories
        ):
            raise ValueError(
                "candidate runtime-state supplemental history resolver returned invalid choice type"
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
            )
        )
        effect_denominator_proven = bool(
            result.frontier.denominator_proven
            and not result.frontier.omitted_scope
            and not result.unresolved
        )
        effects = ()
        if result.frontier.choices:
            first_effects = tuple(result.frontier.choices[0].effects)
            if all(tuple(choice.effects) == first_effects for choice in result.frontier.choices):
                effects = first_effects
            else:
                effect_denominator_proven = False
        if not effect_denominator_proven:
            effects = ()

        return ExtremeSustainedDPSCandidateRuntimeStateResolution(
            frontier=result.frontier,
            effects=effects,
            effect_denominator_proven=effect_denominator_proven,
            evidence=(
                f"Candidate runtime_state resolved for {getattr(candidate, 'candidate_id', '(unknown)')}",
                *tuple(result.evidence),
            ),
            unresolved=tuple(result.unresolved),
        )


__all__ = [
    "CandidateEvidenceResolver",
    "ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService",
    "ExtremeSustainedDPSCandidateRuntimeStateResolution",
]
