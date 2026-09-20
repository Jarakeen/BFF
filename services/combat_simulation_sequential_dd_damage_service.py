from __future__ import annotations

"""Sequential target-Health feedback for canonical DD Combat Simulation.

This module owns only simulated target Health progression between already-resolved
rotation actions. It does not own damage formulas, execute thresholds, mitigation,
or skill semantics. Those remain with the canonical Rotation DD providers.
"""

from dataclasses import dataclass

from minmax.combat_state_snapshot import CombatantSnapshot, CombatStateSnapshot
from minmax.rotation_plan import RotationPlan
from models.combat_simulation import CombatSimulationOutgoingDamage, CombatSimulationTargetState
from services.rotation_candidate_dd_role_output_service import (
    DD_DAMAGE_ACTION_KINDS,
    RotationActionDamageEvidence,
    RotationActionDamageEvidenceProvider,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


@dataclass(frozen=True)
class CombatSimulationSequentialDamageProjection:
    damage: tuple[CombatSimulationOutgoingDamage, ...]
    evidence: tuple[tuple[float, int, RotationActionDamageEvidence], ...] = ()
    unresolved: tuple[str, ...] = ()

    def evidence_provider(self) -> RotationActionDamageEvidenceProvider:
        return _ProjectedDamageEvidenceProvider(self.evidence)


class _ProjectedDamageEvidenceProvider:
    def __init__(
        self,
        evidence: tuple[tuple[float, int, RotationActionDamageEvidence], ...],
    ) -> None:
        self._evidence = {
            (float(time_seconds), int(sequence)): item
            for time_seconds, sequence, item in evidence
        }

    def evaluate_action(self, *, candidate, action) -> RotationActionDamageEvidence:
        del candidate
        key = (float(action.time_seconds), int(action.sequence))
        item = self._evidence.get(key)
        if item is not None:
            return item
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=("sequential combat-simulation damage evidence is unavailable",),
        )


class CombatSimulationTargetHealthLedger:
    """Mutable execution-local Health ledger exposed only through snapshots."""

    def __init__(
        self,
        *,
        target_state: CombatSimulationTargetState,
        target_identity: str,
        player_identity: str,
    ) -> None:
        target = str(target_identity or "").strip()
        player = str(player_identity or "").strip() or "simulation_player"
        combatant = target_state.combatant(target)
        if combatant is None:
            raise ValueError(
                f"combat simulation damage target is not present in target state: {target!r}"
            )
        if combatant.current_health is None or combatant.maximum_health is None:
            raise ValueError(
                "combat simulation target Health feedback requires current and maximum Health"
            )
        self.target_identity = target
        self.player_identity = player
        self.current_health = float(combatant.current_health)
        self.maximum_health = float(combatant.maximum_health)

    def snapshot_at(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> CombatStateSnapshot:
        del sequence
        return CombatStateSnapshot(
            time_seconds=float(time_seconds),
            player=CombatantSnapshot(identity=self.player_identity),
            targets=(
                CombatantSnapshot(
                    identity=self.target_identity,
                    current_health=self.current_health,
                    maximum_health=self.maximum_health,
                ),
            ),
        )

    def apply_damage(self, amount: float) -> tuple[float, float, float]:
        attempted = max(0.0, float(amount))
        before = self.current_health
        applied = min(attempted, before)
        self.current_health = max(0.0, before - applied)
        return before, applied, self.current_health


class CombatSimulationSequentialDDDamageService:
    """Evaluate damage actions in schedule order with live target Health feedback."""

    def project(
        self,
        *,
        plan: RotationPlan,
        candidate: GeneratedRotationCandidate,
        action_damage_evidence_provider: RotationActionDamageEvidenceProvider,
        target_state: CombatSimulationTargetState,
        target_identity: str,
        player_identity: str,
        ledger: CombatSimulationTargetHealthLedger | None = None,
    ) -> CombatSimulationSequentialDamageProjection:
        if candidate.plan != plan:
            raise ValueError(
                "sequential combat-simulation candidate plan does not match simulation plan"
            )

        if ledger is None:
            ledger = CombatSimulationTargetHealthLedger(
                target_state=target_state,
                target_identity=target_identity,
                player_identity=player_identity,
            )
        elif ledger.target_identity != str(target_identity or "").strip():
            raise ValueError(
                "sequential combat-simulation Health ledger target does not match requested target"
            )
        damage: list[CombatSimulationOutgoingDamage] = []
        evidence_rows: list[tuple[float, int, RotationActionDamageEvidence]] = []
        unresolved: list[str] = []

        actions = tuple(
            sorted(
                (
                    action
                    for action in plan.actions
                    if action.kind in DD_DAMAGE_ACTION_KINDS
                ),
                key=lambda action: (
                    float(action.time_seconds),
                    int(action.sequence),
                ),
            )
        )

        for action in actions:
            evidence = action_damage_evidence_provider.evaluate_action(
                candidate=candidate,
                action=action,
            )
            if (
                evidence.time_seconds != action.time_seconds
                or evidence.sequence != action.sequence
            ):
                raise ValueError(
                    "sequential combat-simulation damage evidence mismatch: "
                    f"expected ({action.time_seconds:g}s, {action.sequence}), "
                    f"got ({evidence.time_seconds:g}s, {evidence.sequence})"
                )

            evidence_rows.append(
                (float(action.time_seconds), int(action.sequence), evidence)
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

            ledger.apply_damage(float(evidence.damage_value))
            damage.append(
                CombatSimulationOutgoingDamage(
                    time_seconds=float(action.time_seconds),
                    sequence=int(action.sequence),
                    source=str(action.name or action.kind.value),
                    recipient=ledger.target_identity,
                    amount=float(evidence.damage_value),
                )
            )

        return CombatSimulationSequentialDamageProjection(
            damage=tuple(damage),
            evidence=tuple(evidence_rows),
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
    "CombatSimulationSequentialDamageProjection",
    "CombatSimulationSequentialDDDamageService",
    "CombatSimulationTargetHealthLedger",
]
