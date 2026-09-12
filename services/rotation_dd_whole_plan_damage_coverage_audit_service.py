from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind
from services.rotation_candidate_dd_role_output_service import (
    DD_DAMAGE_ACTION_KINDS,
    RotationActionDamageEvidenceProvider,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


@dataclass(frozen=True)
class RotationDDDamageCoverageBlocker:
    """One repeated unresolved DD damage consequence grouped by semantic cause."""

    action_kind: RotationActionKind
    action_name: str | None
    reason: str
    occurrences: tuple[tuple[float, int], ...]

    @property
    def occurrence_count(self) -> int:
        return len(self.occurrences)


@dataclass(frozen=True)
class RotationDDWholePlanDamageCoverageAudit:
    """Countable whole-plan DD consequence coverage for one exact candidate."""

    candidate_id: str
    total_damage_actions: int
    resolved_damage_actions: int
    unresolved_damage_actions: int
    blockers: tuple[RotationDDDamageCoverageBlocker, ...]

    @property
    def complete(self) -> bool:
        return self.unresolved_damage_actions == 0


class RotationDDWholePlanDamageCoverageAuditService:
    """Audit whether every scheduled DD damage action has canonical consequence evidence.

    This service does not calculate damage or reinterpret unresolved diagnostics. It
    asks the same authoritative action-damage provider used by whole-plan DD output,
    counts resolved versus unresolved scheduled damage actions, and groups repeated
    blockers by action kind, canonical action name, and exact provider reason.

    Grouping preserves every occurrence timestamp/sequence so a repeated evidence gap
    becomes countable without losing where it occurs in the final plan. Unknown damage
    remains unknown; missing provider evidence is never converted to zero damage.
    """

    def __init__(
        self,
        *,
        action_damage_evidence_provider: RotationActionDamageEvidenceProvider,
    ) -> None:
        self.action_damage_evidence_provider = action_damage_evidence_provider

    def audit(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationDDWholePlanDamageCoverageAudit:
        total = 0
        resolved = 0
        grouped: dict[
            tuple[RotationActionKind, str | None, str],
            list[tuple[float, int]],
        ] = {}

        for action in candidate.plan.actions:
            if action.kind not in DD_DAMAGE_ACTION_KINDS:
                continue
            total += 1

            evidence = self.action_damage_evidence_provider.evaluate_action(
                candidate=candidate,
                action=action,
            )
            if (
                evidence.time_seconds != action.time_seconds
                or evidence.sequence != action.sequence
            ):
                raise ValueError(
                    "rotation action damage evidence mismatch: "
                    f"expected ({action.time_seconds:g}s, {action.sequence}), "
                    f"got ({evidence.time_seconds:g}s, {evidence.sequence})"
                )

            reasons = tuple(evidence.unresolved)
            if not reasons and evidence.damage_value is None:
                reasons = ("damage consequence unavailable",)

            if not reasons:
                resolved += 1
                continue

            action_name = str(action.name).strip() if action.name else None
            for reason in reasons:
                key = (action.kind, action_name, str(reason).strip())
                grouped.setdefault(key, []).append(
                    (float(action.time_seconds), int(action.sequence))
                )

        blockers = tuple(
            RotationDDDamageCoverageBlocker(
                action_kind=kind,
                action_name=name,
                reason=reason,
                occurrences=tuple(occurrences),
            )
            for (kind, name, reason), occurrences in grouped.items()
        )
        return RotationDDWholePlanDamageCoverageAudit(
            candidate_id=candidate.candidate_id,
            total_damage_actions=total,
            resolved_damage_actions=resolved,
            unresolved_damage_actions=total - resolved,
            blockers=blockers,
        )


__all__ = [
    "RotationDDDamageCoverageBlocker",
    "RotationDDWholePlanDamageCoverageAudit",
    "RotationDDWholePlanDamageCoverageAuditService",
]
