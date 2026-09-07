from __future__ import annotations

from .healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from .healer_heavy_attack_runtime_candidates import HeavyAttackDecisionWindow
from .healer_recovery_heavy_pressure import HealerRecoveryHeavyPressure
from .healer_wait_decision_provider import HealerHeavyAttackCandidate
from .heavy_attack_opportunity import HeavyAttackOpportunityEvidence, HeavyAttackPurpose


def build_recovery_heavy_attack_candidate(
    *,
    incentive: HealerHeavyAttackBuildIncentive,
    pressure: HealerRecoveryHeavyPressure,
    window: HeavyAttackDecisionWindow,
) -> HealerHeavyAttackCandidate | None:
    """Convert proven sustain pressure into one recovery-heavy candidate.

    Static build discovery proves that the active bar has recovery value from a
    fully charged heavy. The pressure layer proves that recovery is worth
    considering now. The decision window supplies channel/refresh/encounter
    evidence. This function still does not calculate the amount restored.
    """

    if incentive.kind is not HeavyAttackBuildIncentiveKind.RECOVERY_VALUE:
        raise ValueError("recovery heavy candidate requires a recovery-value incentive")
    if incentive.bar != window.bar:
        return None
    if not pressure.recommended:
        return None

    return HealerHeavyAttackCandidate(
        bar=incentive.bar,
        evidence=HeavyAttackOpportunityEvidence(
            weapon=incentive.weapon,
            purpose=HeavyAttackPurpose.RECOVERY,
            available_window_seconds=window.available_window_seconds,
            required_window_seconds=window.required_window_seconds,
            encounter_allows_channel=window.encounter_allows_channel,
            higher_priority_action_ready=window.higher_priority_action_ready,
            refresh_due_before_completion=window.refresh_due_before_completion,
            needed_resource=pressure.resource,
            current_resource=float(pressure.current_amount),
            maximum_resource=float(pressure.maximum_amount),
            recovery_trigger_fraction=float(pressure.trigger_fraction),
            reserve_shortfall=int(pressure.reserve_shortfall),
        ),
    )
