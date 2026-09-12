from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageActivationAnchorResolver,
)


RotationRuntimeActivationAnchorResolverFactory = Callable[
    [RotationPlan],
    PeriodicDamageActivationAnchorResolver,
]


@dataclass(frozen=True)
class RotationRuntimeActivationAnchorEvidence:
    """Exact caller-owned runtime anchor evidence for one final-plan action.

    Canonical skill identity remains semantic lower_snake_case. ``action_time_seconds``
    plus ``action_sequence`` identifies the scheduled action inside the final plan;
    the skill identity guards that ordered position against stale or mismatched
    evidence. Numeric ESO ability IDs are deliberately absent from this executable
    contract.
    """

    skill_entity_id: str
    action_time_seconds: float
    action_sequence: int
    activation_anchor: PeriodicDamageActivationAnchor
    anchor_time_seconds: float
    source: str

    def __post_init__(self) -> None:
        entity_id = ability_entity_id(self.skill_entity_id)
        if not entity_id:
            raise ValueError("runtime activation-anchor evidence requires skill identity")
        object.__setattr__(self, "skill_entity_id", entity_id)

        action_time = float(self.action_time_seconds)
        anchor_time = float(self.anchor_time_seconds)
        if not math.isfinite(action_time) or action_time < 0.0:
            raise ValueError("runtime activation-anchor action time must be finite and non-negative")
        if not math.isfinite(anchor_time) or anchor_time < 0.0:
            raise ValueError("runtime activation-anchor time must be finite and non-negative")
        if anchor_time < action_time:
            raise ValueError("runtime activation anchor cannot precede its scheduled action")
        object.__setattr__(self, "action_time_seconds", action_time)
        object.__setattr__(self, "anchor_time_seconds", anchor_time)

        sequence = int(self.action_sequence)
        if sequence < 0:
            raise ValueError("runtime activation-anchor action sequence cannot be negative")
        object.__setattr__(self, "action_sequence", sequence)

        if not isinstance(self.activation_anchor, PeriodicDamageActivationAnchor):
            object.__setattr__(
                self,
                "activation_anchor",
                PeriodicDamageActivationAnchor(str(self.activation_anchor)),
            )

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("runtime activation-anchor evidence requires provenance")
        object.__setattr__(self, "source", source)

    @property
    def key(self) -> tuple[str, float, int, PeriodicDamageActivationAnchor]:
        return (
            self.skill_entity_id,
            self.action_time_seconds,
            self.action_sequence,
            self.activation_anchor,
        )


class RotationRuntimeActivationAnchorEvidenceService:
    """Bind explicit semantic runtime anchors to the exact final rotation plan.

    This service does not discover or infer impact timing. It only turns reviewed or
    otherwise authoritative caller-owned evidence into the resolver consumed by the
    periodic runtime projection. Evidence that no longer matches the stabilized plan
    is ignored and therefore fails closed at the downstream projection boundary.
    """

    _EPSILON = 1e-9

    def resolver_factory(
        self,
        evidence: Iterable[RotationRuntimeActivationAnchorEvidence],
    ) -> RotationRuntimeActivationAnchorResolverFactory:
        rows = self._dedupe_and_validate(tuple(evidence))

        def factory(plan: RotationPlan) -> PeriodicDamageActivationAnchorResolver:
            matched: dict[
                tuple[str, float, int, PeriodicDamageActivationAnchor],
                float,
            ] = {}
            actions_by_order = {
                (float(action.time_seconds), int(action.sequence)): action
                for action in plan.actions
            }
            for row in rows:
                action = actions_by_order.get(
                    (row.action_time_seconds, row.action_sequence)
                )
                if action is None or action.kind is not RotationActionKind.SKILL:
                    continue
                if ability_entity_id(action.name or "") != row.skill_entity_id:
                    continue
                matched[row.key] = row.anchor_time_seconds

            def resolve(
                action: RotationAction,
                anchor: PeriodicDamageActivationAnchor,
            ) -> float | None:
                resolved_anchor = (
                    anchor
                    if isinstance(anchor, PeriodicDamageActivationAnchor)
                    else PeriodicDamageActivationAnchor(str(anchor))
                )
                if action.kind is not RotationActionKind.SKILL:
                    return None
                skill_entity_id = ability_entity_id(action.name or "")
                if not skill_entity_id:
                    return None
                return matched.get(
                    (
                        skill_entity_id,
                        float(action.time_seconds),
                        int(action.sequence),
                        resolved_anchor,
                    )
                )

            return resolve

        return factory

    def _dedupe_and_validate(
        self,
        evidence: tuple[RotationRuntimeActivationAnchorEvidence, ...],
    ) -> tuple[RotationRuntimeActivationAnchorEvidence, ...]:
        by_key: dict[
            tuple[str, float, int, PeriodicDamageActivationAnchor],
            RotationRuntimeActivationAnchorEvidence,
        ] = {}
        for row in evidence:
            if not isinstance(row, RotationRuntimeActivationAnchorEvidence):
                raise TypeError(
                    "runtime activation-anchor evidence must use "
                    "RotationRuntimeActivationAnchorEvidence"
                )
            existing = by_key.get(row.key)
            if existing is None:
                by_key[row.key] = row
                continue
            if (
                abs(existing.anchor_time_seconds - row.anchor_time_seconds)
                > self._EPSILON
            ):
                raise ValueError(
                    "conflicting runtime activation-anchor evidence for "
                    f"{row.skill_entity_id} at {row.action_time_seconds:g}s/"
                    f"sequence {row.action_sequence} ({row.activation_anchor.value})"
                )
        return tuple(by_key.values())


__all__ = [
    "RotationRuntimeActivationAnchorEvidence",
    "RotationRuntimeActivationAnchorEvidenceService",
    "RotationRuntimeActivationAnchorResolverFactory",
]
