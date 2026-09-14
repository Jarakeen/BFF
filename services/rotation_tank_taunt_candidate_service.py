from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
    RotationTankTauntObligationService,
)


_TAUNT_ACTION_KINDS = frozenset({RotationActionKind.SKILL, RotationActionKind.ULTIMATE})


@dataclass(frozen=True)
class RotationTankTauntActionClaim:
    """Exact caller-owned placement for one taunt application requirement."""

    requirement_id: str
    action_time_seconds: float
    action_sequence: int
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        requirement_id = str(self.requirement_id or "").strip()
        if not requirement_id:
            raise ValueError("tank taunt action claim requirement_id is required")
        object.__setattr__(self, "requirement_id", requirement_id)

        kind = (
            self.action_kind
            if isinstance(self.action_kind, RotationActionKind)
            else RotationActionKind(str(self.action_kind))
        )
        if kind not in _TAUNT_ACTION_KINDS:
            raise ValueError("tank taunt action claim must be a skill or ultimate")
        object.__setattr__(self, "action_kind", kind)

        time_seconds = float(self.action_time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("tank taunt action claim time must be finite and non-negative")
        object.__setattr__(self, "action_time_seconds", time_seconds)

        sequence = int(self.action_sequence)
        if sequence < 0:
            raise ValueError("tank taunt action claim sequence cannot be negative")
        object.__setattr__(self, "action_sequence", sequence)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank taunt action claim bar must be front or back")
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
class RotationTankTauntCandidateProjection:
    candidate: GeneratedRotationCandidate | None
    inserted_claims: tuple[RotationTankTauntActionClaim, ...] = ()
    preserved_requirement_ids: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.candidate is not None and not self.unresolved


class RotationTankTauntCandidateService:
    """Preserve or insert exact source-backed taunt applications.

    This service never chooses a taunt skill, timing, refresh cadence, target, or
    replacement action. The requirement owns the exact source skill and application
    window; an optional claim may place that exact skill only in an unoccupied slot.

    New casts also require structural saved-build slot evidence. A claim cannot make
    a build cast a skill or Ultimate that is not actually slotted, and an ambiguous
    two-bar source remains unresolved unless the requirement/claim selects a bar.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        obligation_service: RotationTankTauntObligationService | object | None = None,
    ) -> None:
        self.obligation_service = obligation_service or RotationTankTauntObligationService(
            database_path
        )

    def project(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        requirements: tuple[RotationTankTauntApplicationRequirement, ...],
        claims: tuple[RotationTankTauntActionClaim, ...] = (),
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
    ) -> RotationTankTauntCandidateProjection:
        if not requirements:
            return RotationTankTauntCandidateProjection(
                candidate=None,
                unresolved=(
                    "tank taunt candidate generation unavailable: no explicit source-backed requirement supplied",
                ),
            )

        requirement_by_id: dict[str, RotationTankTauntApplicationRequirement] = {}
        assessments = {}
        for requirement in requirements:
            if requirement.requirement_id in requirement_by_id:
                raise ValueError(
                    f"duplicate tank taunt requirement id: {requirement.requirement_id}"
                )
            requirement_by_id[requirement.requirement_id] = requirement
            assessments[requirement.requirement_id] = self.obligation_service.assess(
                plan=candidate.plan,
                requirement=requirement,
            )

        already_satisfied = {
            requirement_id
            for requirement_id, assessment in assessments.items()
            if bool(getattr(assessment, "resolved", False))
            and bool(getattr(assessment, "satisfied", False))
        }

        slot_by_key: dict[tuple[RotationActionKind, str], RotationActionSlotRequirement] = {}
        for slot_requirement in slot_requirements:
            key = (
                slot_requirement.action_kind,
                slot_requirement.action_name.casefold(),
            )
            if key in slot_by_key:
                raise ValueError(
                    "duplicate saved-build slot requirement for "
                    f"{slot_requirement.action_name!r}"
                )
            slot_by_key[key] = slot_requirement

        existing_slots = {
            (float(action.time_seconds), int(action.sequence)): action
            for action in candidate.plan.actions
        }
        working_actions = list(candidate.plan.actions)
        inserted: list[RotationTankTauntActionClaim] = []
        unresolved: list[str] = []

        for claim in claims:
            requirement = requirement_by_id.get(claim.requirement_id)
            if requirement is None:
                unresolved.append(
                    f"{claim.requirement_id}: taunt action claim references unknown requirement"
                )
                continue
            if claim.requirement_id in already_satisfied:
                continue

            validation_error = self._claim_validation_error(
                plan=candidate.plan,
                requirement=requirement,
                claim=claim,
            )
            if validation_error is not None:
                unresolved.append(validation_error)
                continue

            slot_requirement = slot_by_key.get(
                (claim.action_kind, requirement.source_skill_name.casefold())
            )
            if slot_requirement is None:
                unresolved.append(
                    f"{claim.requirement_id}: saved-build slot evidence does not prove "
                    f"{requirement.source_skill_name} is slotted as {claim.action_kind.value}"
                )
                continue

            requested_bar = claim.bar if claim.bar is not None else requirement.bar
            if requested_bar is None:
                if len(slot_requirement.allowed_bars) != 1:
                    unresolved.append(
                        f"{claim.requirement_id}: {requirement.source_skill_name} is slotted on "
                        "multiple bars and no exact taunt claim bar was supplied"
                    )
                    continue
                claim_bar = slot_requirement.allowed_bars[0]
            else:
                claim_bar = requested_bar
                if claim_bar not in slot_requirement.allowed_bars:
                    unresolved.append(
                        f"{claim.requirement_id}: {requirement.source_skill_name} is not slotted "
                        f"on the claimed {claim_bar} bar"
                    )
                    continue

            slot = (float(claim.action_time_seconds), int(claim.action_sequence))
            occupied = existing_slots.get(slot)
            if occupied is not None:
                same_action = (
                    occupied.kind is claim.action_kind
                    and str(occupied.name or "").strip().casefold()
                    == requirement.source_skill_name.casefold()
                    and occupied.bar == claim_bar
                )
                if same_action:
                    continue
                unresolved.append(
                    f"{claim.requirement_id}: taunt claim slot {claim.action_time_seconds:g}s "
                    f"sequence {claim.action_sequence} is occupied by {occupied.kind.value}"
                )
                continue

            action = RotationAction(
                time_seconds=claim.action_time_seconds,
                sequence=claim.action_sequence,
                kind=claim.action_kind,
                name=requirement.source_skill_name,
                bar=claim_bar,
            )
            working_actions.append(action)
            existing_slots[slot] = action
            inserted.append(claim)

        if unresolved:
            return RotationTankTauntCandidateProjection(
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
                "explicit tank taunt action claims may add exact source-backed taunt applications only when saved-build slot evidence proves the source is executable on that bar",
            ),
            unresolved=candidate.plan.unresolved,
        )
        projected = GeneratedRotationCandidate(
            candidate_id=candidate.candidate_id,
            plan=plan,
            refresh_leads=candidate.refresh_leads,
            action_claims=candidate.action_claims,
        )

        post_unresolved: list[str] = []
        for requirement in requirements:
            assessment = self.obligation_service.assess(
                plan=projected.plan,
                requirement=requirement,
            )
            if not bool(getattr(assessment, "resolved", False)):
                messages = tuple(getattr(assessment, "unresolved", ())) or (
                    f"{requirement.requirement_id}: taunt source identity unresolved",
                )
                post_unresolved.extend(str(message) for message in messages)
                continue
            if not bool(getattr(assessment, "satisfied", False)):
                applications = tuple(getattr(assessment, "applications", ()))
                post_unresolved.append(
                    f"{requirement.requirement_id}: scheduled {len(applications)} of "
                    f"{requirement.minimum_applications} required taunt applications"
                )

        if post_unresolved:
            return RotationTankTauntCandidateProjection(
                candidate=None,
                inserted_claims=tuple(inserted),
                unresolved=tuple(dict.fromkeys(post_unresolved)),
            )

        preserved = tuple(
            requirement.requirement_id
            for requirement in requirements
            if requirement.requirement_id in already_satisfied
            or not any(
                claim.requirement_id == requirement.requirement_id for claim in inserted
            )
        )
        return RotationTankTauntCandidateProjection(
            candidate=projected,
            inserted_claims=tuple(inserted),
            preserved_requirement_ids=preserved,
        )

    @staticmethod
    def _claim_validation_error(
        *,
        plan: RotationPlan,
        requirement: RotationTankTauntApplicationRequirement,
        claim: RotationTankTauntActionClaim,
    ) -> str | None:
        if not (
            requirement.window_start_seconds
            <= claim.action_time_seconds
            <= requirement.window_end_seconds
        ):
            return (
                f"{claim.requirement_id}: taunt claim at {claim.action_time_seconds:g}s falls outside "
                f"the {requirement.window_start_seconds:g}-{requirement.window_end_seconds:g}s application window"
            )
        if claim.action_time_seconds > plan.duration_seconds:
            return f"{claim.requirement_id}: taunt claim occurs after rotation plan duration"
        if requirement.bar is not None and claim.bar not in {None, requirement.bar}:
            return (
                f"{claim.requirement_id}: taunt claim bar {claim.bar} does not match required {requirement.bar} bar"
            )
        return None


__all__ = [
    "RotationTankTauntActionClaim",
    "RotationTankTauntCandidateProjection",
    "RotationTankTauntCandidateService",
]
