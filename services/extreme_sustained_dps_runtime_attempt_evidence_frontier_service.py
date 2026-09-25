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

    def __post_init__(self) -> None:
        choice_id = str(self.choice_id or "").strip()
        if not choice_id:
            raise ValueError("runtime attempt evidence choice requires choice_id")
        if any(
            not isinstance(row, RuntimeEffectEventAttempt)
            for row in self.attempts
        ):
            raise TypeError(
                "runtime attempt evidence choice attempts must contain RuntimeEffectEventAttempt records"
            )
        object.__setattr__(self, "choice_id", choice_id)
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(
            self,
            "evidence",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.evidence
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier:
    choices: tuple[ExtremeSustainedDPSRuntimeAttemptEvidenceChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(row, ExtremeSustainedDPSRuntimeAttemptEvidenceChoice)
            for row in self.choices
        ):
            raise TypeError(
                "runtime attempt evidence frontier choices must contain canonical choices"
            )
        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError(
                "runtime attempt evidence candidate_count must be a non-negative integer"
            )
        if self.candidate_count != len(self.choices):
            raise ValueError(
                "runtime attempt evidence candidate_count must equal choice count"
            )
        if not isinstance(self.denominator_proven, bool):
            raise TypeError(
                "runtime attempt evidence denominator_proven must be boolean"
            )
        evidence = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.evidence
                if str(item).strip()
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in self.unresolved
                if str(item).strip()
            )
        )
        if self.denominator_proven and (not self.choices or unresolved):
            raise ValueError(
                "runtime attempt evidence denominator cannot be proven with no choices or unresolved evidence"
            )
        object.__setattr__(self, "choices", tuple(self.choices))
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)


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
                    and 0.0 <= float(effect.chance) < 1.0
                }
            )
        )
        if not thresholds:
            return (None,)
        # Eligibility changes only when roll crosses one of these thresholds.
        # 0.0 represents [0, first_threshold); each exact threshold represents
        # [threshold, next_threshold). Roll 1.0 is unnecessary and would also
        # incorrectly fail a nominal 100% effect if shared across variants.
        return tuple(dict.fromkeys((0.0, *thresholds)))

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
        fixed_attempts: tuple[RuntimeEffectEventAttempt, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier:
        unresolved: list[str] = []
        if not event_denominator_proven:
            unresolved.append(
                "Runtime event skeleton denominator is not proven complete"
            )
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
        combinations = product(*per_event) if per_event else ((),)
        for index, combination in enumerate(combinations):
            choices.append(
                ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                    choice_id=f"runtime-attempt-evidence:{index}",
                    attempts=(
                        *tuple(fixed_attempts),
                        *tuple(combination),
                    ),
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
                f"Fixed source-bound runtime attempts supplied: {len(fixed_attempts)}",
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
