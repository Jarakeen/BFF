from __future__ import annotations

"""Cartesian composition for independently proven finite runtime-attempt frontiers."""

from itertools import product

from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
)


class ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService:
    """Compose independent runtime-attempt denominators without losing provenance."""

    @staticmethod
    def compose(
        frontiers: tuple[ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier, ...],
        *,
        source: str,
    ) -> ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier:
        rows = tuple(frontiers)
        if not rows:
            return ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
                choices=(
                    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                        choice_id="runtime-attempt-composed:0",
                        attempts=(),
                        evidence=("No runtime-attempt frontiers required",),
                    ),
                ),
                candidate_count=1,
                denominator_proven=True,
                evidence=(
                    "Runtime-attempt frontiers composed: 0",
                    "Finite composed runtime-attempt choices: 1",
                ),
                unresolved=(),
            )

        unresolved: list[str] = []
        for index, frontier in enumerate(rows):
            unresolved.extend(
                f"frontier {index}: {item}"
                for item in tuple(frontier.unresolved)
                if str(item).strip()
            )
            if not frontier.denominator_proven:
                unresolved.append(
                    f"frontier {index}: runtime-attempt denominator is not proven complete"
                )
            if not frontier.choices:
                unresolved.append(
                    f"frontier {index}: runtime-attempt choice family is empty"
                )

        choices: list[ExtremeSustainedDPSRuntimeAttemptEvidenceChoice] = []
        if not any(not frontier.choices for frontier in rows):
            for index, combination in enumerate(
                product(*(frontier.choices for frontier in rows))
            ):
                choices.append(
                    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                        choice_id=f"runtime-attempt-composed:{index}",
                        attempts=tuple(
                            attempt
                            for choice in combination
                            for attempt in tuple(choice.attempts)
                        ),
                        evidence=tuple(
                            dict.fromkeys(
                                item
                                for choice in combination
                                for item in tuple(choice.evidence)
                                if str(item).strip()
                            )
                        ),
                    )
                )

        deduped_unresolved = tuple(dict.fromkeys(unresolved))
        complete = bool(
            choices
            and all(frontier.denominator_proven for frontier in rows)
            and not deduped_unresolved
        )
        return ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
            choices=tuple(choices),
            candidate_count=len(choices),
            denominator_proven=complete,
            evidence=(
                f"Runtime-attempt frontiers composed: {len(rows)}",
                f"Input runtime-attempt choice counts: {tuple(frontier.candidate_count for frontier in rows)}",
                f"Finite composed runtime-attempt choices: {len(choices)}",
                f"Runtime-attempt composition source: {str(source or '').strip() or 'caller-supplied proof'}",
                (
                    "Composed runtime-attempt denominator is proven finite"
                    if complete
                    else "Composed runtime-attempt denominator remains open"
                ),
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService",
]
