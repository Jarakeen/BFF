from __future__ import annotations

from dataclasses import dataclass, field

from minmax.rotation_plan import RotationPlan
from services.rotation_lokkestiiz_horn_readiness_service import (
    RotationLokkestiizHornReadinessService,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    LokkestiizLandingClockEvidence,
)


@dataclass(frozen=True)
class RotationLokkestiizHornCandidateObligation:
    """Candidate-specific hard-obligation resolver for Horn-at-landing readiness.

    Each completed rotation plan is evaluated independently because its own
    Light/Heavy Attack schedule determines base-combat Ultimate generation. Returned
    evidence plugs into ``RotationSupportCadenceEvaluationContext`` as
    candidate-specific unresolved evidence, which the canonical ranking layer already
    treats as a hard failure.
    """

    landing_clocks: LokkestiizLandingClockEvidence
    starting_ultimate: float
    horn_cost: float
    assume_scheduled_attacks_damage: bool
    readiness_service: RotationLokkestiizHornReadinessService = field(
        default_factory=RotationLokkestiizHornReadinessService,
        compare=False,
        repr=False,
    )

    def __call__(self, plan: RotationPlan) -> tuple[str, ...]:
        result = self.readiness_service.evaluate(
            plan=plan,
            landing_clocks=self.landing_clocks,
            starting_amount=self.starting_ultimate,
            horn_cost=self.horn_cost,
            assume_scheduled_attacks_damage=self.assume_scheduled_attacks_damage,
        )
        if result.ready:
            return ()
        return result.unresolved


__all__ = ["RotationLokkestiizHornCandidateObligation"]
