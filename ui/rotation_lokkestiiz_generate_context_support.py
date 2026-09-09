from __future__ import annotations

from dataclasses import replace

from services.rotation_lokkestiiz_horn_candidate_obligation import (
    RotationLokkestiizHornCandidateObligation,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    LokkestiizLandingClockEvidence,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class RotationLokkestiizGenerateContextSupport:
    """Install the Lokkestiiz Horn-at-landing hard gate into Generate context.

    This composer changes no encounter or build policy. It only carries explicit
    runtime evidence into the existing candidate-specific hard-obligation seam. A
    caller must still provide observed landing clocks, starting Ultimate, the
    resolved Horn cost, and whether scheduled Light/Heavy Attacks are proven damage
    triggers. Existing cadence evaluation evidence is preserved.
    """

    def apply_horn_gate(
        self,
        context: RotationGenerateCanonicalContext,
        *,
        landing_clocks: LokkestiizLandingClockEvidence,
        starting_ultimate: float,
        horn_cost: float,
        assume_scheduled_attacks_damage: bool,
    ) -> RotationGenerateCanonicalContext:
        evaluation = (
            context.cadence_evaluation_context
            or RotationSupportCadenceEvaluationContext()
        )
        if evaluation.candidate_hard_obligation_resolver is not None:
            raise ValueError(
                "Lokkestiiz Horn gate cannot replace an existing candidate hard-obligation resolver"
            )

        horn_obligation = RotationLokkestiizHornCandidateObligation(
            landing_clocks=landing_clocks,
            starting_ultimate=starting_ultimate,
            horn_cost=horn_cost,
            assume_scheduled_attacks_damage=assume_scheduled_attacks_damage,
        )
        return replace(
            context,
            cadence_evaluation_context=replace(
                evaluation,
                candidate_hard_obligation_resolver=horn_obligation,
            ),
        )


__all__ = ["RotationLokkestiizGenerateContextSupport"]
