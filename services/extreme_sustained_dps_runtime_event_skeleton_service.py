from __future__ import annotations

"""Derive the runtime-event skeleton subset already proven by finalized DD evidence."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.rotation_plan import RotationActionKind
from minmax.runtime_event import RuntimeEvent
from services.rotation_candidate_dd_role_output_service import DD_DAMAGE_ACTION_KINDS
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


_PLAN_SKILL_TRIGGERS = {"cast", "skill_cast"}
_PLAN_ULTIMATE_TRIGGERS = {"ultimate_cast", "ultimate_activation_in_combat"}
_PLAN_LIGHT_ATTACK_TRIGGERS = {"light_attack"}
_PLAN_HEAVY_ATTACK_TRIGGERS = {"heavy_attack"}
_PLAN_OWNED_EXCLUDED_TRIGGERS = {"potion_use"}
_DAMAGE_OCCURRENCE_TRIGGERS = {"damage_dealt"}


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEventSkeletonResult:
    events: tuple[RuntimeEvent, ...]
    denominator_proven: bool
    derived_triggers: tuple[str, ...]
    scenario_triggers: tuple[str, ...]
    excluded_plan_owned_triggers: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSRuntimeEventSkeletonService:
    """Compose plan/damage-derived runtime events with proven scenario events."""

    @staticmethod
    def _required_triggers(
        effects: tuple[EffectVariant, ...],
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(effect.trigger).strip()
                    for effect in effects
                    if str(effect.trigger or "").strip()
                }
            )
        )

    @staticmethod
    def _plan_events(
        candidate: GeneratedRotationCandidate,
        trigger: str,
    ) -> tuple[RuntimeEvent, ...]:
        if trigger in _PLAN_SKILL_TRIGGERS:
            kinds = {RotationActionKind.SKILL}
            completion = False
        elif trigger in _PLAN_ULTIMATE_TRIGGERS:
            kinds = {RotationActionKind.ULTIMATE}
            completion = False
        elif trigger in _PLAN_LIGHT_ATTACK_TRIGGERS:
            kinds = {RotationActionKind.LIGHT_ATTACK}
            completion = False
        elif trigger in _PLAN_HEAVY_ATTACK_TRIGGERS:
            kinds = {RotationActionKind.HEAVY_ATTACK}
            completion = True
        else:
            return ()

        heavy_completion = {
            (
                float(row.action_time_seconds),
                int(row.action_sequence),
            ): float(row.completion_time_seconds)
            for row in (
                RotationHeavySustainProjectionService
                .completion_evidence_from_verified_reservations(candidate.plan)
            )
        }

        rows: list[RuntimeEvent] = []
        for action in candidate.plan.actions:
            if action.kind not in kinds:
                continue
            event_time = float(action.time_seconds)
            event_sequence = int(action.sequence)
            if completion:
                key = (event_time, event_sequence)
                if key not in heavy_completion:
                    continue
                event_time = heavy_completion[key]
                event_sequence = 0
            rows.append(
                RuntimeEvent(
                    time_seconds=event_time,
                    sequence=event_sequence,
                    trigger=trigger,
                    source=str(action.name or action.kind.value),
                    target=action.target_key,
                )
            )
        return tuple(rows)

    @staticmethod
    def _damage_events(
        candidate: GeneratedRotationCandidate,
        occurrence_provider: object,
        *,
        target_identity: str | None,
    ) -> tuple[tuple[RuntimeEvent, ...], tuple[str, ...]]:
        events: list[RuntimeEvent] = []
        unresolved: list[str] = []
        for action in candidate.plan.actions:
            if action.kind not in DD_DAMAGE_ACTION_KINDS:
                continue
            evidence = occurrence_provider.evaluate_action_occurrences(
                candidate=candidate,
                action=action,
            )
            unresolved.extend(
                f"{action.time_seconds:g}s #{action.sequence} {action.kind.value}: {item}"
                for item in tuple(evidence.unresolved)
            )
            if evidence.unresolved:
                continue
            for occurrence in evidence.occurrences:
                if float(occurrence.damage_value) <= 0.0:
                    continue
                events.append(
                    RuntimeEvent(
                        time_seconds=float(occurrence.time_seconds),
                        sequence=int(occurrence.sequence),
                        trigger="damage_dealt",
                        source=str(occurrence.source_name),
                        target=(
                            str(target_identity).strip()
                            if str(target_identity or "").strip()
                            else action.target_key
                        ),
                    )
                )
        return tuple(events), tuple(dict.fromkeys(unresolved))

    @classmethod
    def build(
        cls,
        *,
        candidate: GeneratedRotationCandidate,
        effects: tuple[EffectVariant, ...],
        occurrence_provider: object | None = None,
        target_identity: str | None = None,
        supplemental_events: tuple[RuntimeEvent, ...] = (),
        supplemental_denominator_proven: bool = False,
        source: str = "",
    ) -> ExtremeSustainedDPSRuntimeEventSkeletonResult:
        required = cls._required_triggers(tuple(effects))
        unresolved: list[str] = []
        events: list[RuntimeEvent] = []
        derived: list[str] = []
        scenario: list[str] = []
        excluded: list[str] = []

        supplemental_by_trigger: dict[str, list[RuntimeEvent]] = {}
        for event in supplemental_events:
            supplemental_by_trigger.setdefault(event.trigger, []).append(event)

        for trigger in required:
            if trigger in _PLAN_OWNED_EXCLUDED_TRIGGERS:
                excluded.append(trigger)
                continue

            if trigger in (
                _PLAN_SKILL_TRIGGERS
                | _PLAN_ULTIMATE_TRIGGERS
                | _PLAN_LIGHT_ATTACK_TRIGGERS
                | _PLAN_HEAVY_ATTACK_TRIGGERS
            ):
                rows = cls._plan_events(candidate, trigger)
                events.extend(rows)
                derived.append(trigger)
                continue

            if trigger in _DAMAGE_OCCURRENCE_TRIGGERS:
                if occurrence_provider is None:
                    unresolved.append(
                        "damage_dealt runtime skeleton requires canonical exact-time damage occurrence evidence"
                    )
                    continue
                rows, damage_unresolved = cls._damage_events(
                    candidate,
                    occurrence_provider,
                    target_identity=target_identity,
                )
                unresolved.extend(damage_unresolved)
                events.extend(rows)
                derived.append(trigger)
                continue

            scenario.append(trigger)
            events.extend(tuple(supplemental_by_trigger.get(trigger, ())))

        if scenario and not supplemental_denominator_proven:
            unresolved.append(
                "Scenario-owned runtime event skeleton denominator is not proven complete"
            )
        for trigger in scenario:
            if not supplemental_by_trigger.get(trigger):
                unresolved.append(
                    f"Scenario-owned runtime trigger has no supplied event skeletons: {trigger}"
                )

        allowed_supplemental = set(scenario)
        unexpected = tuple(
            sorted(
                {
                    event.trigger
                    for event in supplemental_events
                    if event.trigger not in allowed_supplemental
                }
            )
        )
        if unexpected:
            unresolved.append(
                "Supplemental runtime events contain trigger identities not owned by the scenario skeleton family: "
                + ", ".join(unexpected)
            )

        ordered = tuple(
            sorted(
                events,
                key=lambda row: (
                    row.time_seconds,
                    row.sequence,
                    row.trigger,
                    row.source.casefold(),
                ),
            )
        )
        deduped_unresolved = tuple(dict.fromkeys(unresolved))
        return ExtremeSustainedDPSRuntimeEventSkeletonResult(
            events=ordered,
            denominator_proven=not deduped_unresolved,
            derived_triggers=tuple(dict.fromkeys(derived)),
            scenario_triggers=tuple(dict.fromkeys(scenario)),
            excluded_plan_owned_triggers=tuple(dict.fromkeys(excluded)),
            evidence=(
                f"Canonical runtime trigger identities required: {len(required)}",
                f"Plan/damage-derived trigger families: {len(set(derived))}",
                f"Scenario-owned trigger families: {len(set(scenario))}",
                f"Plan-owned triggers excluded from runtime_state: {len(set(excluded))}",
                f"Runtime event skeletons materialized: {len(ordered)}",
                f"Scenario event denominator source: {str(source or '').strip() or 'caller-supplied proof'}",
                "Expected-value damage does not manufacture critical_damage trigger outcomes",
                "Potion use is excluded because finalized plan potion timing is evaluated downstream",
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEventSkeletonResult",
    "ExtremeSustainedDPSRuntimeEventSkeletonService",
]
