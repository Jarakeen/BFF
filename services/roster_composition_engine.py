from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_relationship import ConditionContext, EffectRelationship
from minmax.character_build.effect_layer import BarId
from minmax.encounter_evaluation import EncounterEvaluation, EncounterEvaluator
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.roster_capability_resolver import (
    RosterCapabilityProvider,
    RosterCapabilityResolver,
)


@dataclass(frozen=True)
class RosterCompositionResult:
    """Complete Phase 5 composition result for one roster/encounter pair."""

    capabilities: dict[str, tuple[RosterCapabilityProvider, ...]]
    evaluation: EncounterEvaluation

    @property
    def covered_count(self) -> int:
        return len(self.evaluation.satisfied)

    @property
    def problem_count(self) -> int:
        return len(self.evaluation.problems)

    @property
    def is_fully_covered(self) -> bool:
        return self.evaluation.is_fully_covered


class RosterCompositionEngine:
    """
    Production orchestration boundary for roster composition analysis.

    The service intentionally owns the sequence:

        CharacterBuilds
            -> roster capabilities
            -> encounter evaluation
            -> recommendation intents

    It does not mutate builds, choose a replacement build, or optimize a
    provider assignment. Those are later decision layers built on this
    authoritative result.
    """

    def __init__(
        self,
        capability_resolver: RosterCapabilityResolver | None = None,
        evaluator: EncounterEvaluator | None = None,
    ) -> None:
        self.capability_resolver = capability_resolver or RosterCapabilityResolver()
        self.evaluator = evaluator or EncounterEvaluator()

    def evaluate(
        self,
        characters: Iterable[CharacterBuild],
        active_bars: dict[str, BarId],
        requirement_set: EncounterRequirementSet,
        *,
        relationships: Iterable[EffectRelationship] = (),
        condition_context: ConditionContext | None = None,
    ) -> RosterCompositionResult:
        """
        Resolve the roster and evaluate it against an encounter requirement set.

        The same condition context is forwarded to roster capability
        resolution and encounter requirement activation so the two halves of
        the analysis cannot silently disagree about the active encounter
        state.
        """
        character_list = tuple(characters)

        capabilities = self.capability_resolver.resolve(
            character_list,
            active_bars,
            relationships=relationships,
            condition_context=condition_context,
        )

        evaluation = self.evaluator.evaluate(
            requirement_set,
            capabilities,
            condition_context=condition_context,
        )

        return RosterCompositionResult(
            capabilities=capabilities,
            evaluation=evaluation,
        )
