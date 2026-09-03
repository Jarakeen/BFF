from __future__ import annotations

from dataclasses import dataclass, replace

from .build_calculation_context import (
    BuildCalculationContext,
    CombatEnvironment,
)
from .build_candidate import BuildCandidate
from .character_progression import AttributeAllocation, CharacterProgression
from .combat_state import CombatState, IncomingAttackState
from .context_factory import BuildCalculationContextFactory


@dataclass(frozen=True)
class BuildCandidateContextResult:
    """Phase 12 result of resolving one candidate through Phase 2 static math.

    ``context`` is absent whenever the candidate was already ineligible for
    evaluation.  Any unresolved evidence emitted by the existing context
    factory remains explicit here instead of being converted into defaults.
    """

    candidate: BuildCandidate
    context: BuildCalculationContext | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.context is not None and not self.unresolved


def progression_for_candidate(
    candidate: BuildCandidate,
    baseline_progression: CharacterProgression,
) -> CharacterProgression:
    """Preserve character-owned progression while applying candidate attributes."""

    build = candidate.candidate_build
    return replace(
        baseline_progression,
        attributes=AttributeAllocation(
            health=int(build.AttributeHealth or 0),
            magicka=int(build.AttributeMagicka or 0),
            stamina=int(build.AttributeStamina or 0),
        ),
    )


def build_candidate_context(
    *,
    candidate: BuildCandidate,
    baseline_progression: CharacterProgression,
    context_factory: BuildCalculationContextFactory,
    environment: CombatEnvironment = CombatEnvironment.PVE,
    combat_state: CombatState = CombatState(),
    incoming_attack: IncomingAttackState = IncomingAttackState(),
    target_type: str = "monster",
    target_count: int = 1,
    target_resistance: float | None = None,
    fight_duration: float | None = None,
    active_bar: str = "front",
) -> BuildCandidateContextResult:
    """Resolve a candidate with the existing canonical calculation stack.

    Phase 12 owns orchestration only.  Static ESO math remains in
    ``BuildCalculationContextFactory`` and its existing repositories/resolvers.
    """

    if not candidate.is_evaluable:
        unresolved = candidate.unresolved or (
            f"Candidate is not evaluable: {candidate.evaluation_state.value}",
        )
        return BuildCandidateContextResult(
            candidate=candidate,
            context=None,
            unresolved=unresolved,
        )

    build = candidate.candidate_build
    progression = progression_for_candidate(candidate, baseline_progression)
    context = context_factory.build(
        character_id=candidate.character_id,
        build_id=candidate.candidate_id,
        build=build,
        progression=progression,
        environment=environment,
        combat_state=combat_state,
        incoming_attack=incoming_attack,
        target_type=target_type,
        target_count=target_count,
        target_resistance=target_resistance,
        fight_duration=fight_duration,
        active_bar=active_bar,
    )

    return BuildCandidateContextResult(
        candidate=candidate,
        context=context,
        unresolved=tuple(context.unresolved_gear_effects),
    )
