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
    RotationActionDamageOccurrence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


@dataclass(frozen=True)
class CombatSimulationSequentialDamageProjection:
    damage: tuple[CombatSimulationOutgoingDamage, ...]
    evidence: tuple[tuple[float, int, RotationActionDamageEvidence], ...] = ()
    unresolved: tuple[str, ...] = ()
    terminated_at_seconds: float | None = None
    terminated_at_sequence: int | None = None
    suppressed_action_keys: tuple[tuple[float, int], ...] = ()

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
        if int(combatant.current_health) <= 0:
            raise ValueError(
                "combat simulation target Health feedback requires a living target at simulation start"
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

    @property
    def is_dead(self) -> bool:
        return self.current_health <= 0.0

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
        suppressed: list[tuple[float, int]] = []
        pending: list[RotationActionDamageOccurrence] = []
        terminated_at_seconds: float | None = None
        terminated_at_sequence: int | None = None

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

        def apply_occurrence(occurrence: RotationActionDamageOccurrence) -> None:
            nonlocal terminated_at_seconds, terminated_at_sequence
            if ledger.is_dead:
                return
            amount = float(occurrence.damage_value)
            ledger.apply_damage(amount)
            if amount > 0.0:
                damage.append(
                    CombatSimulationOutgoingDamage(
                        time_seconds=float(occurrence.time_seconds),
                        sequence=int(occurrence.sequence),
                        source=occurrence.source_name,
                        recipient=ledger.target_identity,
                        amount=amount,
                    )
                )
            if ledger.is_dead and terminated_at_seconds is None:
                terminated_at_seconds = float(occurrence.time_seconds)
                terminated_at_sequence = int(occurrence.sequence)

        def flush_before(time_seconds: float) -> None:
            due = tuple(
                sorted(
                    (
                        item
                        for item in pending
                        if float(item.time_seconds) < float(time_seconds)
                    ),
                    key=lambda item: (
                        float(item.time_seconds),
                        int(item.sequence),
                        int(item.coefficient_number or 0),
                        -1 if item.occurrence_index is None else int(item.occurrence_index),
                    ),
                )
            )
            if not due:
                return
            due_ids = {id(item) for item in due}
            pending[:] = [item for item in pending if id(item) not in due_ids]
            for item in due:
                if ledger.is_dead:
                    break
                apply_occurrence(item)

        occurrence_aware = hasattr(
            action_damage_evidence_provider,
            "evaluate_action_occurrences",
        )

        for action_index, action in enumerate(actions):
            flush_before(action.time_seconds)
            action_key = (float(action.time_seconds), int(action.sequence))

            same_time_pending = tuple(
                item
                for item in pending
                if float(item.time_seconds) == float(action.time_seconds)
            )
            if same_time_pending:
                reason = (
                    f"{float(action.time_seconds):g}s damage ordering is unresolved: "
                    "one or more periodic damage occurrences share the exact timestamp "
                    "with a scheduled damage action, and no reviewed cross-source "
                    "same-instant ordering rule is available"
                )
                unresolved.append(reason)
                remaining_actions = actions[action_index:]
                for remaining in remaining_actions:
                    remaining_key = (
                        float(remaining.time_seconds),
                        int(remaining.sequence),
                    )
                    evidence_rows.append(
                        (
                            *remaining_key,
                            RotationActionDamageEvidence(
                                time_seconds=remaining.time_seconds,
                                sequence=remaining.sequence,
                                damage_value=None,
                                unresolved=(reason,),
                            ),
                        )
                    )
                return CombatSimulationSequentialDamageProjection(
                    damage=tuple(
                        sorted(
                            damage,
                            key=lambda item: (
                                float(item.time_seconds),
                                int(item.sequence),
                                item.source.casefold(),
                            ),
                        )
                    ),
                    evidence=tuple(evidence_rows),
                    unresolved=tuple(dict.fromkeys(unresolved)),
                    terminated_at_seconds=terminated_at_seconds,
                    terminated_at_sequence=terminated_at_sequence,
                    suppressed_action_keys=tuple(suppressed),
                )

            if ledger.is_dead:
                suppressed.append(action_key)
                evidence_rows.append(
                    (
                        *action_key,
                        RotationActionDamageEvidence(
                            time_seconds=action.time_seconds,
                            sequence=action.sequence,
                            damage_value=0.0,
                        ),
                    )
                )
                continue

            identity = self._action_identity(action)
            if occurrence_aware:
                occurrence_evidence = (
                    action_damage_evidence_provider.evaluate_action_occurrences(
                        candidate=candidate,
                        action=action,
                    )
                )
                if (
                    occurrence_evidence.action_time_seconds != action.time_seconds
                    or occurrence_evidence.action_sequence != action.sequence
                ):
                    raise ValueError(
                        "sequential combat-simulation occurrence evidence mismatch: "
                        f"expected ({action.time_seconds:g}s, {action.sequence}), "
                        f"got ({occurrence_evidence.action_time_seconds:g}s, "
                        f"{occurrence_evidence.action_sequence})"
                    )
                if occurrence_evidence.unresolved:
                    unresolved.extend(
                        f"{identity}: {message}"
                        for message in occurrence_evidence.unresolved
                        if str(message).strip()
                    )
                    evidence_rows.append(
                        (
                            *action_key,
                            RotationActionDamageEvidence(
                                time_seconds=action.time_seconds,
                                sequence=action.sequence,
                                damage_value=None,
                                unresolved=occurrence_evidence.unresolved,
                            ),
                        )
                    )
                    continue

                evidence_rows.append(
                    (
                        *action_key,
                        RotationActionDamageEvidence(
                            time_seconds=action.time_seconds,
                            sequence=action.sequence,
                            damage_value=0.0,
                        ),
                    )
                )
                for occurrence in occurrence_evidence.occurrences:
                    if float(occurrence.time_seconds) > float(plan.duration_seconds):
                        continue
                    if float(occurrence.time_seconds) < float(action.time_seconds):
                        unresolved.append(
                            f"{identity}: damage occurrence precedes its parent action "
                            f"at {float(occurrence.time_seconds):g}s"
                        )
                        continue
                    if (
                        float(occurrence.time_seconds) == float(action.time_seconds)
                        and occurrence.occurrence_index is None
                    ):
                        apply_occurrence(occurrence)
                    else:
                        pending.append(occurrence)
                continue

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

            if evidence.unresolved:
                evidence_rows.append((*action_key, evidence))
                unresolved.extend(
                    f"{identity}: {message}"
                    for message in evidence.unresolved
                    if str(message).strip()
                )
                continue
            if evidence.damage_value is None:
                evidence_rows.append((*action_key, evidence))
                unresolved.append(f"{identity}: damage consequence unavailable")
                continue

            evidence_rows.append(
                (
                    *action_key,
                    RotationActionDamageEvidence(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        damage_value=0.0,
                    ),
                )
            )
            apply_occurrence(
                RotationActionDamageOccurrence(
                    time_seconds=float(action.time_seconds),
                    sequence=int(action.sequence),
                    damage_value=float(evidence.damage_value),
                    source_name=str(action.name or action.kind.value),
                )
            )

        for occurrence in sorted(
            (
                item
                for item in pending
                if float(item.time_seconds) <= float(plan.duration_seconds)
            ),
            key=lambda item: (
                float(item.time_seconds),
                int(item.sequence),
                int(item.coefficient_number or 0),
                -1 if item.occurrence_index is None else int(item.occurrence_index),
            ),
        ):
            if ledger.is_dead:
                break
            apply_occurrence(occurrence)

        return CombatSimulationSequentialDamageProjection(
            damage=tuple(
                sorted(
                    damage,
                    key=lambda item: (
                        float(item.time_seconds),
                        int(item.sequence),
                        item.source.casefold(),
                    ),
                )
            ),
            evidence=tuple(evidence_rows),
            unresolved=tuple(dict.fromkeys(unresolved)),
            terminated_at_seconds=terminated_at_seconds,
            terminated_at_sequence=terminated_at_sequence,
            suppressed_action_keys=tuple(suppressed),
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
