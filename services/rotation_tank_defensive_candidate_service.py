from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
    RotationTankDefensiveObligationService,
)


_DEFENSIVE_KINDS = frozenset({RotationActionKind.BLOCK, RotationActionKind.DODGE})


@dataclass(frozen=True)
class RotationTankDefensiveActionClaim:
    """Exact caller-owned defensive action placement for one tank obligation.

    The claim is deliberately narrower than a timing window: it chooses one exact
    action kind, timestamp, sequence, and optional bar. This service never chooses
    a response time from an encounter window and never displaces an occupied action
    slot on the caller's behalf.
    """

    obligation_id: str
    action_kind: RotationActionKind
    action_time_seconds: float
    action_sequence: int
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        obligation_id = str(self.obligation_id or "").strip()
        if not obligation_id:
            raise ValueError("tank defensive action claim obligation_id is required")
        object.__setattr__(self, "obligation_id", obligation_id)

        kind = (
            self.action_kind
            if isinstance(self.action_kind, RotationActionKind)
            else RotationActionKind(str(self.action_kind))
        )
        if kind not in _DEFENSIVE_KINDS:
            raise ValueError("tank defensive action claim must be block or dodge")
        object.__setattr__(self, "action_kind", kind)

        time_seconds = float(self.action_time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError(
                "tank defensive action claim time must be finite and non-negative"
            )
        object.__setattr__(self, "action_time_seconds", time_seconds)

        sequence = int(self.action_sequence)
        if sequence < 0:
            raise ValueError("tank defensive action claim sequence cannot be negative")
        object.__setattr__(self, "action_sequence", sequence)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank defensive action claim bar must be front or back")
            object.__setattr__(self, "bar", bar)

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class RotationTankDefensiveCandidateProjection:
    candidate: GeneratedRotationCandidate | None
    inserted_claims: tuple[RotationTankDefensiveActionClaim, ...] = ()
    preserved_obligation_ids: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.candidate is not None and not self.unresolved


class RotationTankDefensiveCandidateService:
    """Preserve or insert exact defensive responses without inventing placement.

    Existing scheduled responses satisfy obligations unchanged. Missing responses
    may be added only from explicit exact action claims. A claim never displaces an
    existing action at the same ``(time_seconds, sequence)`` slot, because deciding
    what should move is strategy/scheduler policy rather than evidence projection.
    """

    def __init__(
        self,
        obligation_service: RotationTankDefensiveObligationService | None = None,
    ) -> None:
        self.obligation_service = obligation_service or RotationTankDefensiveObligationService()

    def project(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        obligations: tuple[RotationTankDefensiveObligation, ...],
        claims: tuple[RotationTankDefensiveActionClaim, ...] = (),
    ) -> RotationTankDefensiveCandidateProjection:
        if not obligations:
            return RotationTankDefensiveCandidateProjection(
                candidate=None,
                unresolved=(
                    "tank defensive candidate generation unavailable: no explicit source-backed obligation supplied",
                ),
            )

        obligation_by_id: dict[str, RotationTankDefensiveObligation] = {}
        for obligation in obligations:
            if obligation.obligation_id in obligation_by_id:
                raise ValueError(
                    f"duplicate tank defensive obligation id: {obligation.obligation_id}"
                )
            obligation_by_id[obligation.obligation_id] = obligation

        existing_slots = {
            (float(action.time_seconds), int(action.sequence)): action
            for action in candidate.plan.actions
        }
        working_actions = list(candidate.plan.actions)
        inserted: list[RotationTankDefensiveActionClaim] = []
        unresolved: list[str] = []

        for claim in claims:
            obligation = obligation_by_id.get(claim.obligation_id)
            if obligation is None:
                unresolved.append(
                    f"{claim.obligation_id}: defensive action claim references unknown obligation"
                )
                continue

            validation_error = self._claim_validation_error(
                plan=candidate.plan,
                obligation=obligation,
                claim=claim,
            )
            if validation_error is not None:
                unresolved.append(validation_error)
                continue

            slot = (float(claim.action_time_seconds), int(claim.action_sequence))
            occupied = existing_slots.get(slot)
            claim_bar = claim.bar if claim.bar is not None else obligation.bar
            if occupied is not None:
                same_action = (
                    occupied.kind is claim.action_kind
                    and (claim_bar is None or occupied.bar == claim_bar)
                )
                if same_action:
                    continue
                unresolved.append(
                    f"{claim.obligation_id}: defensive claim slot {claim.action_time_seconds:g}s "
                    f"sequence {claim.action_sequence} is occupied by {occupied.kind.value}"
                )
                continue

            action = RotationAction(
                time_seconds=claim.action_time_seconds,
                sequence=claim.action_sequence,
                kind=claim.action_kind,
                bar=claim_bar,
            )
            working_actions.append(action)
            existing_slots[slot] = action
            inserted.append(claim)

        if unresolved:
            return RotationTankDefensiveCandidateProjection(
                candidate=None,
                inserted_claims=tuple(inserted),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        plan = RotationPlan(
            character_name=candidate.plan.character_name,
            build_name=candidate.plan.build_name,
            duration_seconds=candidate.plan.duration_seconds,
            actions=tuple(working_actions),
            assumptions=tuple(candidate.plan.assumptions)
            + (
                "explicit tank defensive action claims may add exact block/dodge responses without displacing occupied rotation slots",
            ),
            unresolved=candidate.plan.unresolved,
        )
        projected = GeneratedRotationCandidate(
            candidate_id=candidate.candidate_id,
            plan=plan,
            refresh_leads=candidate.refresh_leads,
            action_claims=candidate.action_claims,
        )

        evidence = self.obligation_service.evaluate_candidate(
            candidate=projected,
            obligations=obligations,
        )
        if evidence.satisfied is not True:
            return RotationTankDefensiveCandidateProjection(
                candidate=None,
                inserted_claims=tuple(inserted),
                unresolved=tuple(evidence.reasons)
                or ("tank defensive candidate remains unresolved after explicit claims",),
            )

        preserved = tuple(
            obligation.obligation_id
            for obligation in obligations
            if not any(
                claim.obligation_id == obligation.obligation_id for claim in inserted
            )
        )
        return RotationTankDefensiveCandidateProjection(
            candidate=projected,
            inserted_claims=tuple(inserted),
            preserved_obligation_ids=preserved,
        )

    @staticmethod
    def _claim_validation_error(
        *,
        plan: RotationPlan,
        obligation: RotationTankDefensiveObligation,
        claim: RotationTankDefensiveActionClaim,
    ) -> str | None:
        if claim.action_kind not in obligation.allowed_actions:
            return (
                f"{claim.obligation_id}: claimed {claim.action_kind.value} is not an allowed defensive response"
            )
        if not (
            obligation.window_start_seconds
            <= claim.action_time_seconds
            <= obligation.window_end_seconds
        ):
            return (
                f"{claim.obligation_id}: defensive claim at {claim.action_time_seconds:g}s falls outside "
                f"the {obligation.window_start_seconds:g}-{obligation.window_end_seconds:g}s obligation window"
            )
        if claim.action_time_seconds > plan.duration_seconds:
            return (
                f"{claim.obligation_id}: defensive claim occurs after rotation plan duration"
            )
        if obligation.bar is not None and claim.bar not in {None, obligation.bar}:
            return (
                f"{claim.obligation_id}: defensive claim bar {claim.bar} does not match required {obligation.bar} bar"
            )
        return None


__all__ = [
    "RotationTankDefensiveActionClaim",
    "RotationTankDefensiveCandidateProjection",
    "RotationTankDefensiveCandidateService",
]
