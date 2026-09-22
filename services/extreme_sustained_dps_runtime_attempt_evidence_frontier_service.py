from __future__ import annotations

"""Finite equivalence classes for runtime chance-roll and condition evidence."""

from dataclasses import dataclass
from itertools import product

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_relationship import ConditionContext
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent, runtime_event_matches_effect_variant


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeAttemptEvidenceChoice:
    choice_id: str
    attempts: tuple[RuntimeEffectEventAttempt, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier:
    choices: tuple[ExtremeSustainedDPSRuntimeAttemptEvidenceChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService:
    """Enumerate every semantically distinct chance/condition realization.

    Event time, trigger, source, target, and sequence remain caller-owned scenario
    facts. For each supplied event this service derives finite chance-roll regions
    from the matching EffectVariant chance thresholds and finite condition contexts
    from matching EffectVariant condition identities.
    """

    @staticmethod
    def _matching(
        event: RuntimeEvent,
        effects: tuple[EffectVariant, ...],
    ) -> tuple[EffectVariant, ...]:
        return tuple(
            effect
            for effect in effects
            if runtime_event_matches_effect_variant(event, effect)
        )

    @classmethod
    def _chance_representatives(
        cls,
        event: RuntimeEvent,
        effects: tuple[EffectVariant, ...],
    ) -> tuple[float | None, ...]:
        matching = cls._matching(event, effects)
        thresholds = tuple(
            sorted(
                {
                    float(effect.chance)
                    for effect in matching
                    if effect.chance is not None
                    and 0.0 < float(effect.chance) < 1.0
                }
            )
        )
        if not thresholds:
            return (None,)
        # Eligibility changes only when roll crosses one of these thresholds.
        # 0.0 represents [0, first_threshold); each exact threshold represents
        # [threshold, next_threshold). Roll 1.0 is unnecessary and would also
        # incorrectly fail a nominal 100% effect if shared across variants.
        return (0.0, *thresholds)

    @classmethod
    def _condition_contexts(
        cls,
        event: RuntimeEvent,
        effects: tuple[EffectVariant, ...],
    ) -> tuple[ConditionContext, ...]:
        matching = cls._matching(event, effects)
        conditions = tuple(
            sorted(
                {
                    str(effect.condition).strip()
                    for effect in matching
                    if str(effect.condition or "").strip()
                }
            )
        )
        if not conditions:
            return (frozenset(),)

        rows: list[ConditionContext] = []
        for mask in product((False, True), repeat=len(conditions)):
            rows.append(
                frozenset(
                    condition
                    for condition, enabled in zip(conditions, mask)
                    if enabled
                )
            )
        return tuple(rows)

    @classmethod
    def build(
        cls,
        *,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
        event_denominator_proven: bool,
        source: str,
    ) -> ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier:
        unresolved: list[str] = []
        if not event_denominator_proven:
            unresolved.append(
                "Runtime event skeleton denominator is not proven complete"
            )
        if not events:
            unresolved.append("Runtime event skeleton family is empty")

        per_event: list[tuple[RuntimeEffectEventAttempt, ...]] = []
        per_event_counts: list[int] = []
        for event in events:
            rolls = cls._chance_representatives(event, effects)
            contexts = cls._condition_contexts(event, effects)
            attempts = tuple(
                RuntimeEffectEventAttempt(
                    event=event,
                    chance_roll=roll,
                    condition_context=context,
                )
                for roll in rolls
                for context in contexts
            )
            per_event.append(attempts)
            per_event_counts.append(len(attempts))

        choices: list[ExtremeSustainedDPSRuntimeAttemptEvidenceChoice] = []
        if per_event:
            for index, combination in enumerate(product(*per_event)):
                choices.append(
                    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                        choice_id=f"runtime-attempt-evidence:{index}",
                        attempts=tuple(combination),
                        evidence=(
                            "Chance rolls are finite representatives of canonical proc-chance threshold regions",
                            "Condition contexts are explicit subsets of relevant named conditions",
                        ),
                    )
                )

        deduped = tuple(dict.fromkeys(unresolved))
        complete = bool(choices and event_denominator_proven and not deduped)
        return ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
            choices=tuple(choices),
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Runtime event skeletons supplied: {len(events)}",
                f"Canonical runtime effects considered: {len(effects)}",
                f"Per-event evidence realization counts: {tuple(per_event_counts)}",
                f"Finite runtime attempt evidence choices: {len(choices)}",
                f"Runtime event denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Chance/condition runtime attempt evidence denominator is proven finite"
                    if complete
                    else "Chance/condition runtime attempt evidence denominator remains open"
                ),
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeAttemptEvidenceChoice",
    "ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier",
    "ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService",
]
