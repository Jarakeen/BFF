from __future__ import annotations

"""First deterministic Phase 14 combat-simulation kernel.

This slice proves deterministic orchestration and bar-state progression over the
canonical Phase 13 RotationPlan. ESO consequences that are not yet connected are
reported explicitly as unresolved instead of being treated as zero.
"""

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationIncomingDamage,
    CombatSimulationOutgoingDamage,
    CombatSimulationResult,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind, RotationPlan

from services.combat_simulation_event_queue import CombatSimulationEventQueue
from services.combat_simulation_healing_service import CombatSimulationHealingService
from services.combat_simulation_health_service import CombatSimulationHealthService
from services.combat_simulation_outgoing_damage_service import (
    CombatSimulationOutgoingDamageService,
)
from services.combat_simulation_resource_service import CombatSimulationResourceService
from services.combat_simulation_skill_effect_service import CombatSimulationSkillEffectService
from services.combat_simulation_target_binding_service import CombatSimulationTargetBindingService
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidenceProvider,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


_CONSEQUENCE_PENDING = frozenset(
    {
        RotationActionKind.SKILL,
        RotationActionKind.LIGHT_ATTACK,
        RotationActionKind.HEAVY_ATTACK,
        RotationActionKind.ULTIMATE,
        RotationActionKind.POTION,
        RotationActionKind.BLOCK,
        RotationActionKind.DODGE,
    }
)


class CombatSimulationService:
    """Replay one exact build + rotation into a deterministic event stream."""

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        resource_service: CombatSimulationResourceService | None = None,
        healing_service: CombatSimulationHealingService | None = None,
        health_service: CombatSimulationHealthService | None = None,
        skill_effect_service: CombatSimulationSkillEffectService | None = None,
        target_binding_service: CombatSimulationTargetBindingService | None = None,
        outgoing_damage_service: CombatSimulationOutgoingDamageService | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.resource_service = resource_service or CombatSimulationResourceService()
        self.healing_service = healing_service or CombatSimulationHealingService()
        self.health_service = health_service or CombatSimulationHealthService()
        self.skill_effect_service = skill_effect_service or CombatSimulationSkillEffectService()
        self.target_binding_service = target_binding_service or CombatSimulationTargetBindingService()
        self.outgoing_damage_service = outgoing_damage_service

    def simulate(
        self,
        *,
        build_snapshot: EffectiveBuildSnapshot,
        plan: RotationPlan,
        initial_bar: str = "front",
        target_state: CombatSimulationTargetState | None = None,
        incoming_damage: tuple[CombatSimulationIncomingDamage, ...] = (),
        outgoing_damage: tuple[CombatSimulationOutgoingDamage, ...] = (),
        damage_target_identity: str = "",
        damage_candidate: GeneratedRotationCandidate | None = None,
        action_damage_evidence_provider: RotationActionDamageEvidenceProvider | None = None,
    ) -> CombatSimulationResult:
        if not isinstance(build_snapshot, EffectiveBuildSnapshot):
            raise TypeError("combat simulation requires EffectiveBuildSnapshot")
        if not isinstance(plan, RotationPlan):
            raise TypeError("combat simulation requires RotationPlan")

        build = build_snapshot.materialize()
        if plan.character_name.casefold() != str(build.Name or "").strip().casefold():
            raise ValueError("rotation character does not match effective build")
        if plan.build_name.casefold() != str(build.BuildName or "").strip().casefold():
            raise ValueError("rotation build does not match effective build")

        assessment = self.active_bar_assessor.assess(plan, initial_bar=initial_bar)
        unresolved: list[str] = list(plan.unresolved)
        damage_unresolved: list[str] = []
        for violation in assessment.violations:
            unresolved.append(
                f"{violation.time_seconds:g}s {violation.action_name}: {violation.reason}"
            )

        queue = CombatSimulationEventQueue()
        for item in incoming_damage:
            if item.time_seconds > plan.duration_seconds:
                continue
            queue.push(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.DIRECT_RESULT),
                    sequence=int(item.sequence),
                    event_type="incoming_damage",
                    source=item.source,
                    payload=(
                        ("recipient", item.recipient),
                        ("amount", float(item.amount)),
                        ("damage_type", item.damage_type or ""),
                    ),
                )
            )

        for item in outgoing_damage:
            if item.time_seconds > plan.duration_seconds:
                continue
            queue.push(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.DIRECT_RESULT),
                    sequence=int(item.sequence),
                    event_type="outgoing_damage",
                    source=item.source,
                    payload=(
                        ("recipient", item.recipient),
                        ("amount", float(item.amount)),
                        ("damage_type", item.damage_type or ""),
                    ),
                )
            )

        resolved_damage_actions: set[tuple[float, int]] = set()
        projection_service = self.outgoing_damage_service
        if action_damage_evidence_provider is not None:
            if projection_service is not None:
                raise ValueError(
                    "combat simulation accepts either configured outgoing-damage service "
                    "or action_damage_evidence_provider, not both"
                )
            projection_service = CombatSimulationOutgoingDamageService(
                action_damage_evidence_provider=action_damage_evidence_provider,
            )

        if projection_service is not None:
            if not str(damage_target_identity or "").strip():
                message = (
                    "canonical outgoing damage projection requires explicit target identity"
                )
                unresolved.append(message)
                damage_unresolved.append(message)
            else:
                projection = projection_service.project(
                    plan=plan,
                    target_identity=damage_target_identity,
                    candidate=damage_candidate,
                )
                unresolved.extend(projection.unresolved)
                damage_unresolved.extend(projection.unresolved)
                resolved_damage_actions.update(projection.resolved_action_keys)
                for item in projection.damage:
                    if item.time_seconds > plan.duration_seconds:
                        continue
                    queue.push(
                        CombatSimulationEvent(
                            time_seconds=float(item.time_seconds),
                            priority=int(SimulationEventPriority.DIRECT_RESULT),
                            sequence=int(item.sequence),
                            event_type="outgoing_damage",
                            source=item.source,
                            payload=(
                                ("recipient", item.recipient),
                                ("amount", float(item.amount)),
                                ("damage_type", item.damage_type or ""),
                            ),
                        )
                    )

        for action in plan.actions:
            queue.push(
                CombatSimulationEvent(
                    time_seconds=float(action.time_seconds),
                    priority=int(SimulationEventPriority.ACTION),
                    sequence=int(action.sequence),
                    event_type="action",
                    source=str(action.name or action.kind.value),
                    payload=(
                        ("kind", action.kind.value),
                        ("bar", action.bar or ""),
                        ("target_key", action.target_key or ""),
                    ),
                )
            )

        resources = []
        magicka = self.resource_service.project(
            build=build,
            plan=plan,
            resource=ResourceType.MAGICKA,
        )
        resources.append(magicka.result)
        queue.extend(magicka.events)
        unresolved.extend(magicka.unresolved)

        healing = self.healing_service.project(build=build, plan=plan)
        queue.extend(healing.events)
        unresolved.extend(healing.unresolved)

        effects = self.skill_effect_service.project(build=build, plan=plan)
        queue.extend(effects.events)
        unresolved.extend(effects.unresolved)

        events: list[CombatSimulationEvent] = []
        while queue:
            event = queue.pop()
            if event.time_seconds > plan.duration_seconds:
                break
            events.append(event)

            if event.event_type != "action":
                continue
            kind = RotationActionKind(event.payload_dict()["kind"])
            if kind in _CONSEQUENCE_PENDING:
                action_key = (float(event.time_seconds), int(event.sequence))
                damage_resolved = action_key in resolved_damage_actions

                if kind is RotationActionKind.SKILL:
                    if damage_resolved:
                        unresolved.append(
                            f"{event.time_seconds:g}s {event.source}: "
                            "damage consequence is wired; remaining unsupported non-damage "
                            "skill consequences are unresolved"
                        )
                    else:
                        message = (
                            f"{event.time_seconds:g}s {event.source}: "
                            "remaining skill consequences (for example damage or unsupported effects) "
                            "not yet wired in Phase 14"
                        )
                        unresolved.append(message)
                        damage_unresolved.append(message)
                    continue

                if kind in {
                    RotationActionKind.LIGHT_ATTACK,
                    RotationActionKind.HEAVY_ATTACK,
                    RotationActionKind.ULTIMATE,
                } and damage_resolved:
                    if kind is RotationActionKind.ULTIMATE:
                        unresolved.append(
                            f"{event.time_seconds:g}s {event.source}: "
                            "Ultimate damage consequence is wired; unsupported non-damage "
                            "Ultimate consequences remain unresolved"
                        )
                    continue

                message = (
                    f"{event.time_seconds:g}s {event.source}: "
                    f"{kind.value} consequence projection not yet wired in Phase 14"
                )
                unresolved.append(message)
                if kind in {
                    RotationActionKind.LIGHT_ATTACK,
                    RotationActionKind.HEAVY_ATTACK,
                    RotationActionKind.ULTIMATE,
                }:
                    damage_unresolved.append(message)

        target_projection = self.target_binding_service.bind(
            events=tuple(events),
            target_state=target_state,
        )
        unresolved.extend(target_projection.unresolved)

        health_projection = self.health_service.project(
            events=target_projection.events,
            target_state=target_state,
        )
        unresolved.extend(health_projection.unresolved)

        merged_events = tuple(
            sorted(
                (*target_projection.events, *health_projection.events),
                key=lambda event: (
                    event.time_seconds,
                    event.priority,
                    event.sequence,
                    event.event_type,
                    event.source.casefold(),
                ),
            )
        )

        return CombatSimulationResult(
            duration_seconds=plan.duration_seconds,
            initial_bar=assessment.initial_bar,
            final_bar=assessment.final_bar,
            events=merged_events,
            resources=tuple(resources),
            effect_windows=tuple(effects.windows),
            target_state=target_state,
            unresolved=tuple(dict.fromkeys(unresolved)),
            damage_unresolved=tuple(dict.fromkeys(damage_unresolved)),
        )


__all__ = ["CombatSimulationService"]
