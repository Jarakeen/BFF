from __future__ import annotations

"""Bridge canonical Rotation DD action evidence into combat-simulation damage.

This service owns no ESO damage formulas. It converts already-resolved per-action
Rotation damage evidence into explicit post-mitigation outgoing-damage records that
the deterministic combat simulator can apply to a known combatant Health state.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationPlan
from models.combat_simulation import CombatSimulationOutgoingDamage
from services.rotation_candidate_dd_role_output_service import (
    DD_DAMAGE_ACTION_KINDS,
    RotationActionDamageEvidenceProvider,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


@dataclass(frozen=True)
class CombatSimulationOutgoingDamageProjection:
    damage: tuple[CombatSimulationOutgoingDamage, ...]
    resolved_action_keys: tuple[tuple[float, int], ...] = ()
    unresolved: tuple[str, ...] = ()


class CombatSimulationOutgoingDamageService:
    """Project canonical scheduled-action damage into explicit target damage."""

    def __init__(
        self,
        *,
        action_damage_evidence_provider: RotationActionDamageEvidenceProvider,
    ) -> None:
        self.action_damage_evidence_provider = action_damage_evidence_provider

    def project(
        self,
        *,
        plan: RotationPlan,
        target_identity: str,
        candidate: GeneratedRotationCandidate | None = None,
    ) -> CombatSimulationOutgoingDamageProjection:
        target = str(target_identity or "").strip()
        if not target:
            raise ValueError("combat simulation outgoing-damage target identity is required")

        if candidate is None:
            candidate = GeneratedRotationCandidate(
                candidate_id="combat-simulation",
                plan=plan,
                refresh_leads=(),
                action_claims=(),
            )
        elif candidate.plan != plan:
            raise ValueError(
                "combat simulation damage candidate plan does not match simulation plan"
            )

        projected: list[CombatSimulationOutgoingDamage] = []
        resolved: list[tuple[float, int]] = []
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind not in DD_DAMAGE_ACTION_KINDS:
                continue

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

            identity = self._action_identity(action)
            if evidence.unresolved:
                unresolved.extend(
                    f"{identity}: {message}"
                    for message in evidence.unresolved
                    if str(message).strip()
                )
                continue
            if evidence.damage_value is None:
                unresolved.append(f"{identity}: damage consequence unavailable")
                continue

            resolved.append((float(action.time_seconds), int(action.sequence)))
            if float(evidence.damage_value) <= 0.0:
                continue
            projected.append(
                CombatSimulationOutgoingDamage(
                    time_seconds=float(action.time_seconds),
                    sequence=int(action.sequence),
                    source=str(action.name or action.kind.value),
                    recipient=target,
                    amount=float(evidence.damage_value),
                )
            )

        return CombatSimulationOutgoingDamageProjection(
            damage=tuple(projected),
            resolved_action_keys=tuple(resolved),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _action_identity(action) -> str:
        name = f" {action.name}" if action.name else ""
        return (
            f"{action.time_seconds:g}s #{action.sequence} "
            f"{action.kind.value}{name}"
        )


__all__ = [
    "CombatSimulationOutgoingDamageProjection",
    "CombatSimulationOutgoingDamageService",
]
