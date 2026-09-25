from __future__ import annotations

"""Assemble finite runtime attempt evidence with supplemental external histories."""

from dataclasses import dataclass
from itertools import product

from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult:
    choices: tuple[ExtremeSustainedDPSRuntimeExternalHistoryChoice, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(row, ExtremeSustainedDPSRuntimeExternalHistoryChoice)
            for row in self.choices
        ):
            raise TypeError(
                "runtime external-history assembly choices must contain canonical histories"
            )
        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError(
                "runtime external-history assembly candidate_count must be a non-negative integer"
            )
        if self.candidate_count != len(self.choices):
            raise ValueError(
                "runtime external-history assembly candidate_count must equal choice count"
            )
        if not isinstance(self.denominator_proven, bool):
            raise TypeError(
                "runtime external-history assembly denominator_proven must be boolean"
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
                "runtime external-history assembly denominator cannot be proven with no choices or unresolved evidence"
            )
        object.__setattr__(self, "choices", tuple(self.choices))
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "unresolved", unresolved)


class ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService:
    """Cross finite attempt evidence with finite supplemental history choices."""

    @classmethod
    def build(
        cls,
        *,
        attempt_frontier: ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
        supplemental_histories: tuple[
            ExtremeSustainedDPSRuntimeExternalHistoryChoice,
            ...,
        ] = (),
        supplemental_denominator_proven: bool,
        source: str,
    ) -> ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult:
        unresolved: list[str] = list(attempt_frontier.unresolved)
        if not attempt_frontier.denominator_proven:
            unresolved.append(
                "Runtime attempt evidence denominator is not proven complete"
            )
        if not supplemental_denominator_proven:
            unresolved.append(
                "Supplemental external runtime-history denominator is not proven complete"
            )

        supplemental = tuple(supplemental_histories)
        if not supplemental:
            supplemental = (
                ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                    history_id="supplemental:none",
                    entries=(),
                    evidence=("No supplemental external runtime entries",),
                ),
            )

        seen: set[str] = set()
        valid_supplemental: list[ExtremeSustainedDPSRuntimeExternalHistoryChoice] = []
        for history in supplemental:
            if history.history_id in seen:
                unresolved.append(
                    f"Duplicate supplemental runtime-history identity: {history.history_id}"
                )
                continue
            seen.add(history.history_id)
            if history.unresolved:
                unresolved.extend(
                    f"{history.history_id}: {item}"
                    for item in history.unresolved
                )
            valid_supplemental.append(history)

        choices: list[ExtremeSustainedDPSRuntimeExternalHistoryChoice] = []
        for attempts, supplemental_choice in product(
            attempt_frontier.choices,
            tuple(valid_supplemental),
        ):
            history_id = (
                f"{attempts.choice_id}|{supplemental_choice.history_id}"
            )
            choices.append(
                ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                    history_id=history_id,
                    entries=(
                        *tuple(attempts.attempts),
                        *tuple(supplemental_choice.entries),
                    ),
                    evidence=(
                        *tuple(attempts.evidence),
                        *tuple(supplemental_choice.evidence),
                    ),
                )
            )

        deduped = tuple(dict.fromkeys(unresolved))
        complete = bool(
            choices
            and attempt_frontier.denominator_proven
            and supplemental_denominator_proven
            and not deduped
        )
        return ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult(
            choices=tuple(choices),
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Attempt-evidence choices: {attempt_frontier.candidate_count}",
                f"Supplemental history choices: {len(valid_supplemental)}",
                f"Combined external runtime histories: {len(choices)}",
                f"Supplemental runtime-history denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Combined external runtime-history denominator is proven complete"
                    if complete
                    else "Combined external runtime-history denominator remains open"
                ),
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult",
    "ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService",
]
