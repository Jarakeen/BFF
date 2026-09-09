from __future__ import annotations

from dataclasses import dataclass
import re

from services.team_provider_uptime_policy_service import TeamProviderUptimePolicy


def _canonical_skill_id(value: object) -> str:
    text = str(value or "").strip().casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


@dataclass(frozen=True)
class RotationSupportRefreshCadenceCandidate:
    """One arithmetic cadence proposal for a refreshable support effect.

    This is candidate-generation evidence, not encounter policy. The caller still
    has to build and evaluate the resulting rotation against encounter eligibility,
    resource/sustain obligations, provider workload, and role policy.
    """

    candidate_key: str
    effect_key: str
    source_skill_id: str
    recast_interval_seconds: float
    projected_steady_state_uptime_ratio: float
    effective_duration_seconds: float
    target_ratio: float
    rationale: str


@dataclass(frozen=True)
class RotationSupportRefreshCadenceResult:
    effect_key: str
    source_skill_id: str
    candidates: tuple[RotationSupportRefreshCadenceCandidate, ...]
    unresolved: tuple[str, ...] = ()


class RotationSupportRefreshCadenceService:
    """Derive refresh-cadence candidates from explicit duration and uptime policy.

    For a continuously refreshable effect with effective duration ``d`` and a
    desired steady-state uptime ratio ``u``, the longest arithmetic recast interval
    that can meet that target is ``d / u``. The service also emits a full-coverage
    cadence at ``d`` so downstream rotation evaluation can compare the additional
    workload against the target-floor candidate.

    The calculation deliberately stops at candidate generation. It does not infer
    encounter windows, eligibility, target availability, sustain, role displacement,
    or a preferred winner. Those remain responsibilities of the existing Phase 13
    evaluation and policy layers.
    """

    @classmethod
    def derive(
        cls,
        *,
        policy: TeamProviderUptimePolicy,
        source_skill_id: str,
        effective_duration_seconds: float | None,
    ) -> RotationSupportRefreshCadenceResult:
        effect_key = cls._canonical_effect_key(policy.effect_key)
        skill_id = _canonical_skill_id(source_skill_id)
        if not skill_id:
            raise ValueError("source_skill_id is required")

        if effective_duration_seconds is None:
            return RotationSupportRefreshCadenceResult(
                effect_key=effect_key,
                source_skill_id=skill_id,
                candidates=(),
                unresolved=(
                    f"effective duration is unresolved for {skill_id!r}; refresh cadence was not guessed",
                ),
            )

        duration = float(effective_duration_seconds)
        if duration <= 0.0:
            raise ValueError("effective_duration_seconds must be greater than zero")

        target = float(policy.target_ratio)
        if target <= 0.0:
            return RotationSupportRefreshCadenceResult(
                effect_key=effect_key,
                source_skill_id=skill_id,
                candidates=(),
            )

        theoretical = policy.theoretical_max_ratio
        if theoretical is not None and float(theoretical) < 1.0 - 1e-9:
            return RotationSupportRefreshCadenceResult(
                effect_key=effect_key,
                source_skill_id=skill_id,
                candidates=(),
                unresolved=(
                    "uptime policy has a theoretical maximum below 100%; "
                    "encounter/runtime cycle evidence is required instead of a global refresh cadence",
                ),
            )

        full = cls._candidate(
            candidate_key="full_coverage",
            effect_key=effect_key,
            source_skill_id=skill_id,
            interval=duration,
            duration=duration,
            target=target,
            rationale="refresh at effective expiry for continuous arithmetic coverage",
        )

        target_interval = duration / target
        if abs(target_interval - duration) <= 1e-9:
            return RotationSupportRefreshCadenceResult(
                effect_key=effect_key,
                source_skill_id=skill_id,
                candidates=(full,),
            )

        floor = cls._candidate(
            candidate_key="target_floor",
            effect_key=effect_key,
            source_skill_id=skill_id,
            interval=target_interval,
            duration=duration,
            target=target,
            rationale=(
                "longest arithmetic recast interval that can meet the explicit "
                "steady-state uptime target before encounter/runtime evaluation"
            ),
        )
        return RotationSupportRefreshCadenceResult(
            effect_key=effect_key,
            source_skill_id=skill_id,
            candidates=(full, floor),
        )

    @staticmethod
    def _candidate(
        *,
        candidate_key: str,
        effect_key: str,
        source_skill_id: str,
        interval: float,
        duration: float,
        target: float,
        rationale: str,
    ) -> RotationSupportRefreshCadenceCandidate:
        projected = min(1.0, duration / interval)
        return RotationSupportRefreshCadenceCandidate(
            candidate_key=candidate_key,
            effect_key=effect_key,
            source_skill_id=source_skill_id,
            recast_interval_seconds=interval,
            projected_steady_state_uptime_ratio=projected,
            effective_duration_seconds=duration,
            target_ratio=target,
            rationale=rationale,
        )

    @staticmethod
    def _canonical_effect_key(value: object) -> str:
        text = str(value or "").strip().casefold().replace("-", " ")
        key = "_".join(text.split())
        if not key:
            raise ValueError("policy effect_key is required")
        return key


__all__ = [
    "RotationSupportRefreshCadenceCandidate",
    "RotationSupportRefreshCadenceResult",
    "RotationSupportRefreshCadenceService",
]
