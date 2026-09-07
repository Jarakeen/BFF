from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamProviderUptimePolicy:
    """Encounter-scoped uptime expectation for one team provider effect.

    Uptime targets are strategy/benchmark policy, not universal game mechanics.
    They may come from encounter research, ESO Logs analysis, BTVTools feedback,
    or a user-defined raid plan. ``theoretical_max_ratio`` is kept separate from
    ``target_ratio`` because some mechanics have hard cycle ceilings while others
    are merely difficult to maintain perfectly.
    """

    effect_key: str
    target_ratio: float
    encounter_key: str | None = None
    phase_key: str | None = None
    theoretical_max_ratio: float | None = None
    source: str = "strategy"
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.effect_key or "").strip():
            raise ValueError("effect_key is required")
        if not 0.0 <= float(self.target_ratio) <= 1.0:
            raise ValueError("target_ratio must be between 0 and 1")
        if self.theoretical_max_ratio is not None:
            theoretical = float(self.theoretical_max_ratio)
            if not 0.0 <= theoretical <= 1.0:
                raise ValueError("theoretical_max_ratio must be between 0 and 1")
            if float(self.target_ratio) > theoretical + 1e-9:
                raise ValueError(
                    "target_ratio cannot exceed theoretical_max_ratio; correct the policy source instead of silently clamping"
                )
        if not str(self.source or "").strip():
            raise ValueError("source is required")

    @property
    def target_percent(self) -> float:
        return float(self.target_ratio) * 100.0

    @property
    def theoretical_max_percent(self) -> float | None:
        if self.theoretical_max_ratio is None:
            return None
        return float(self.theoretical_max_ratio) * 100.0


@dataclass(frozen=True)
class TeamProviderUptimeAssessment:
    policy: TeamProviderUptimePolicy
    observed_ratio: float
    target_met: bool
    shortfall_ratio: float
    theoretical_headroom_ratio: float | None

    @property
    def observed_percent(self) -> float:
        return self.observed_ratio * 100.0

    @property
    def shortfall_percent(self) -> float:
        return self.shortfall_ratio * 100.0


class TeamProviderUptimePolicyService:
    """Assess observed provider uptime against scoped strategy evidence."""

    @staticmethod
    def assess(
        policy: TeamProviderUptimePolicy,
        *,
        observed_ratio: float,
    ) -> TeamProviderUptimeAssessment:
        observed = float(observed_ratio)
        if not 0.0 <= observed <= 1.0:
            raise ValueError("observed_ratio must be between 0 and 1")
        shortfall = max(0.0, float(policy.target_ratio) - observed)
        headroom = None
        if policy.theoretical_max_ratio is not None:
            headroom = max(0.0, float(policy.theoretical_max_ratio) - observed)
        return TeamProviderUptimeAssessment(
            policy=policy,
            observed_ratio=observed,
            target_met=observed + 1e-9 >= float(policy.target_ratio),
            shortfall_ratio=shortfall,
            theoretical_headroom_ratio=headroom,
        )
