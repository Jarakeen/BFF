from __future__ import annotations

from dataclasses import dataclass

from .team_provider_effect_eligibility_service import (
    EncounterEligibilityWindow,
    TeamProviderEffectEligibilityRule,
    TeamProviderEffectEligibilityService,
    TeamProviderEligibleUptimeResult,
)
from .team_provider_temporal_coverage_service import TeamProviderTimedApplication
from .team_provider_uptime_policy_service import (
    TeamProviderUptimeAssessment,
    TeamProviderUptimePolicy,
    TeamProviderUptimePolicyService,
)


@dataclass(frozen=True)
class TeamProviderEffectUptimeAssessment:
    """Policy assessment plus the exact encounter-time denominator that produced it."""

    eligibility: TeamProviderEligibleUptimeResult
    policy_assessment: TeamProviderUptimeAssessment

    @property
    def target_met(self) -> bool:
        return self.policy_assessment.target_met


class TeamProviderEffectUptimeAssessmentService:
    """Bridge effect-purpose eligibility windows into scoped uptime policy scoring.

    Callers supply explicit encounter/runtime windows and an effect eligibility rule.
    The service computes the observed ratio only across useful seconds, then evaluates
    that ratio against the encounter-scoped target. This prevents Comp/Optimization
    from comparing a full-fight percentage to a damageable-time target by accident.
    """

    @staticmethod
    def _canonical(value: object) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", " ").split())

    @classmethod
    def assess(
        cls,
        policy: TeamProviderUptimePolicy,
        *,
        eligibility_rule: TeamProviderEffectEligibilityRule,
        windows: tuple[EncounterEligibilityWindow, ...],
        applications: tuple[TeamProviderTimedApplication, ...],
    ) -> TeamProviderEffectUptimeAssessment:
        if cls._canonical(policy.effect_key) != cls._canonical(eligibility_rule.effect_key):
            raise ValueError("policy and eligibility_rule must describe the same effect")

        eligibility = TeamProviderEffectEligibilityService.evaluate(
            eligibility_rule,
            windows=windows,
            applications=applications,
        )
        if eligibility.eligible_seconds <= 0:
            raise ValueError(
                "cannot assess provider uptime without at least one explicit eligible encounter window"
            )

        policy_assessment = TeamProviderUptimePolicyService.assess(
            policy,
            observed_ratio=eligibility.coverage_ratio,
        )
        return TeamProviderEffectUptimeAssessment(
            eligibility=eligibility,
            policy_assessment=policy_assessment,
        )
