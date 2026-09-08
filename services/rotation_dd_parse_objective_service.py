from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from services.rotation_candidate_scorecard_service import RotationCandidateScorecard


DEFAULT_TRIAL_DUMMY_HEALTH = 21_000_000.0


class RotationDDParseProjectionState(str, Enum):
    """Whether a damage projection spans the self-consistent parse horizon."""

    READY = "ready"
    NEEDS_LONGER_PROJECTION = "needs_longer_projection"
    NEEDS_SHORTER_PROJECTION = "needs_shorter_projection"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RotationDDParseObjective:
    """Damage-first objective for a stationary trial-dummy parse.

    The target health is deliberately caller-overridable. The default models the
    user's 21M trial-dummy workflow, but this contract does not pretend every
    target or patch uses the same health value.

    A parse candidate must first satisfy the ordinary Rotation Maker hard
    obligations. Among legal candidates, the desired horizon is the time required
    for that candidate's own projected sustained DPS to defeat the target. Because
    changing the horizon can change sustain, proc, potion, Ultimate, and execute
    behavior, callers are expected to re-project until the requested horizon and
    the observed kill-time estimate converge.
    """

    target_health: float = DEFAULT_TRIAL_DUMMY_HEALTH
    convergence_tolerance_seconds: float = 0.5

    def __post_init__(self) -> None:
        health = float(self.target_health)
        tolerance = float(self.convergence_tolerance_seconds)
        if not math.isfinite(health) or health <= 0:
            raise ValueError("DD parse target health must be finite and positive")
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError(
                "DD parse convergence tolerance must be finite and non-negative"
            )
        object.__setattr__(self, "target_health", health)
        object.__setattr__(self, "convergence_tolerance_seconds", tolerance)


@dataclass(frozen=True)
class RotationDDParseCandidateEvidence:
    candidate_id: str
    scorecard: RotationCandidateScorecard
    projected_duration_seconds: float
    projected_total_damage: float | None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("DD parse candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", candidate_id)

        duration = float(self.projected_duration_seconds)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("DD parse projected duration must be finite and positive")
        object.__setattr__(self, "projected_duration_seconds", duration)

        if self.projected_total_damage is not None:
            damage = float(self.projected_total_damage)
            if not math.isfinite(damage) or damage < 0:
                raise ValueError(
                    "DD parse projected total damage must be finite and non-negative"
                )
            object.__setattr__(self, "projected_total_damage", damage)

        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )


@dataclass(frozen=True)
class RotationDDParseAssessment:
    candidate_id: str
    state: RotationDDParseProjectionState
    projected_duration_seconds: float
    projected_total_damage: float | None
    projected_dps: float | None
    estimated_kill_time_seconds: float | None
    next_horizon_seconds: float | None
    selectable: bool
    reasons: tuple[str, ...]


class RotationDDParseObjectiveService:
    """Assess whether a legal DD parse projection is damage-horizon complete.

    This service does not calculate ESO damage. It consumes explicit projected
    total-damage evidence from the existing/future combat consequence path and
    keeps that evidence distinct from static single-event damage. This prevents a
    Phase 12 comparison value from being mislabeled as rotation DPS.
    """

    def assess(
        self,
        *,
        objective: RotationDDParseObjective,
        evidence: RotationDDParseCandidateEvidence,
    ) -> RotationDDParseAssessment:
        if not evidence.scorecard.supplied_obligations_satisfied:
            return RotationDDParseAssessment(
                candidate_id=evidence.candidate_id,
                state=RotationDDParseProjectionState.INELIGIBLE,
                projected_duration_seconds=evidence.projected_duration_seconds,
                projected_total_damage=evidence.projected_total_damage,
                projected_dps=None,
                estimated_kill_time_seconds=None,
                next_horizon_seconds=None,
                selectable=False,
                reasons=("candidate fails Rotation Maker hard obligations",),
            )

        unresolved = tuple(evidence.unresolved)
        if evidence.projected_total_damage is None:
            unresolved = unresolved + ("projected rotation damage is unavailable",)
        if unresolved:
            return RotationDDParseAssessment(
                candidate_id=evidence.candidate_id,
                state=RotationDDParseProjectionState.UNRESOLVED,
                projected_duration_seconds=evidence.projected_duration_seconds,
                projected_total_damage=evidence.projected_total_damage,
                projected_dps=None,
                estimated_kill_time_seconds=None,
                next_horizon_seconds=None,
                selectable=False,
                reasons=unresolved,
            )

        total_damage = float(evidence.projected_total_damage or 0.0)
        projected_dps = total_damage / evidence.projected_duration_seconds
        if projected_dps <= 0:
            return RotationDDParseAssessment(
                candidate_id=evidence.candidate_id,
                state=RotationDDParseProjectionState.INELIGIBLE,
                projected_duration_seconds=evidence.projected_duration_seconds,
                projected_total_damage=total_damage,
                projected_dps=projected_dps,
                estimated_kill_time_seconds=None,
                next_horizon_seconds=None,
                selectable=False,
                reasons=("verified projected DPS cannot defeat a positive-health target",),
            )

        kill_time = objective.target_health / projected_dps
        horizon_delta = kill_time - evidence.projected_duration_seconds
        tolerance = objective.convergence_tolerance_seconds

        if abs(horizon_delta) <= tolerance:
            return RotationDDParseAssessment(
                candidate_id=evidence.candidate_id,
                state=RotationDDParseProjectionState.READY,
                projected_duration_seconds=evidence.projected_duration_seconds,
                projected_total_damage=total_damage,
                projected_dps=projected_dps,
                estimated_kill_time_seconds=kill_time,
                next_horizon_seconds=kill_time,
                selectable=True,
                reasons=(
                    "legal candidate and projected kill horizon converged within tolerance",
                ),
            )

        state = (
            RotationDDParseProjectionState.NEEDS_LONGER_PROJECTION
            if horizon_delta > 0
            else RotationDDParseProjectionState.NEEDS_SHORTER_PROJECTION
        )
        direction = "longer" if horizon_delta > 0 else "shorter"
        return RotationDDParseAssessment(
            candidate_id=evidence.candidate_id,
            state=state,
            projected_duration_seconds=evidence.projected_duration_seconds,
            projected_total_damage=total_damage,
            projected_dps=projected_dps,
            estimated_kill_time_seconds=kill_time,
            next_horizon_seconds=kill_time,
            selectable=False,
            reasons=(
                f"re-project the candidate over a {direction} self-consistent kill horizon",
            ),
        )

    @staticmethod
    def rank_ready(
        assessments: tuple[RotationDDParseAssessment, ...],
    ) -> tuple[RotationDDParseAssessment, ...]:
        """Rank only converged legal parse candidates by sustainable projected DPS."""

        ready = tuple(
            item
            for item in assessments
            if item.state is RotationDDParseProjectionState.READY and item.selectable
        )
        return tuple(
            sorted(
                ready,
                key=lambda item: (
                    -(item.projected_dps or 0.0),
                    item.estimated_kill_time_seconds or math.inf,
                    item.candidate_id.casefold(),
                ),
            )
        )
