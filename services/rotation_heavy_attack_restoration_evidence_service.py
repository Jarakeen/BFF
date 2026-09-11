from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.character_build.character_build import CharacterBuild
from minmax.heavy_attack_restoration import (
    HeavyAttackRestorationModifiers,
    HeavyAttackWeaponType,
    create_heavy_attack_restoration_event,
    verified_heavy_attack_base_restore,
)
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_heavy_attack_weapon_projection_service import (
    RotationHeavyAttackWeaponProjection,
    RotationHeavyAttackWeaponProjectionService,
)


@dataclass(frozen=True)
class RotationHeavyAttackCompletionEvidence:
    """Explicit runtime evidence for one scheduled heavy attack completion.

    `fully_charged=False` is affirmative evidence that the heavy did not complete
    as a fully charged attack and therefore produces no heavy-attack restoration.
    Missing evidence is not treated as an interrupted/partial heavy; it remains
    unresolved.

    ``verified_base_restore`` is an optional evidence override. When omitted, the
    restoration service may use the shared canonical live-verified weapon base.
    Unknown weapon families still fail closed.
    """

    action_time_seconds: float
    action_sequence: int
    completion_time_seconds: float
    fully_charged: bool
    verified_base_restore: float | None
    modifiers: HeavyAttackRestorationModifiers = HeavyAttackRestorationModifiers()
    source: str = "explicit heavy-attack completion evidence"

    def __post_init__(self) -> None:
        start = float(self.action_time_seconds)
        completion = float(self.completion_time_seconds)
        if start < 0.0 or completion < 0.0:
            raise ValueError("heavy-attack evidence times cannot be negative")
        if completion < start:
            raise ValueError("heavy-attack completion cannot precede its scheduled start")
        if int(self.action_sequence) < 0:
            raise ValueError("heavy-attack evidence sequence cannot be negative")
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("heavy-attack completion evidence requires a source")
        object.__setattr__(self, "action_time_seconds", start)
        object.__setattr__(self, "completion_time_seconds", completion)
        object.__setattr__(self, "action_sequence", int(self.action_sequence))
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class RotationHeavyAttackResolvedModifiers:
    modifiers: HeavyAttackRestorationModifiers
    unresolved: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return not self.unresolved


HeavyAttackRestorationModifierResolver = Callable[
    [RotationAction, HeavyAttackWeaponType, RotationHeavyAttackCompletionEvidence],
    RotationHeavyAttackResolvedModifiers,
]


@dataclass(frozen=True)
class RotationHeavyAttackRestorationResolution:
    action: RotationAction
    weapon: HeavyAttackWeaponType
    evidence: RotationHeavyAttackCompletionEvidence
    restoration_event: ResourceRestorationEvent | None


@dataclass(frozen=True)
class RotationHeavyAttackRestorationProjection:
    weapon_projection: RotationHeavyAttackWeaponProjection
    resolutions: tuple[RotationHeavyAttackRestorationResolution, ...]
    restoration_events: tuple[ResourceRestorationEvent, ...]
    unresolved: tuple[str, ...]

    @property
    def is_resolved(self) -> bool:
        return self.weapon_projection.is_legal and not self.unresolved


class RotationHeavyAttackRestorationEvidenceService:
    """Turn scheduled heavies into restoration events from reviewed evidence.

    Weapon/resource identity comes from the actual build and reconstructed active
    bar. Completion/full-charge state and completion time remain explicit caller
    evidence. A caller may supply a reviewed base-restore override; otherwise the
    service reuses the shared canonical live-verified weapon base. Resolved modifier
    composition may be supplied by a canonical upstream resolver once the weapon is
    known. Unknown bases or modifiers remain unresolved rather than guessed.
    """

    _EPSILON = 1e-9

    def __init__(
        self,
        weapon_service: RotationHeavyAttackWeaponProjectionService | None = None,
    ) -> None:
        self.weapon_service = weapon_service or RotationHeavyAttackWeaponProjectionService()

    def project(
        self,
        *,
        build: CharacterBuild,
        plan: RotationPlan,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
        modifier_resolver: HeavyAttackRestorationModifierResolver | None = None,
    ) -> RotationHeavyAttackRestorationProjection:
        weapon_projection = self.weapon_service.project(
            build=build,
            plan=plan,
            initial_bar=initial_bar,
        )

        evidence_by_action: dict[tuple[float, int], RotationHeavyAttackCompletionEvidence] = {}
        for item in completion_evidence:
            key = (float(item.action_time_seconds), int(item.action_sequence))
            if key in evidence_by_action:
                raise ValueError(
                    "duplicate heavy-attack completion evidence for "
                    f"{item.action_time_seconds:.3f}s sequence {item.action_sequence}"
                )
            evidence_by_action[key] = item

        heavy_keys = {
            (float(action.time_seconds), int(action.sequence))
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        }
        extras = tuple(sorted(key for key in evidence_by_action if key not in heavy_keys))
        if extras:
            formatted = ", ".join(f"{time:.3f}s seq {sequence}" for time, sequence in extras)
            raise ValueError(f"heavy-attack completion evidence has no scheduled heavy: {formatted}")

        unresolved: list[str] = list(weapon_projection.unresolved)
        resolutions: list[RotationHeavyAttackRestorationResolution] = []
        events: list[ResourceRestorationEvent] = []

        resolution_by_key = {
            (float(item.action.time_seconds), int(item.action.sequence)): item
            for item in weapon_projection.resolutions
        }

        for action in plan.actions:
            if action.kind is not RotationActionKind.HEAVY_ATTACK:
                continue
            key = (float(action.time_seconds), int(action.sequence))
            weapon_resolution = resolution_by_key.get(key)
            if weapon_resolution is None:
                # Weapon projection already carries an unresolved/violation reason.
                continue

            evidence = evidence_by_action.get(key)
            if evidence is None:
                unresolved.append(
                    f"scheduled heavy attack at {action.time_seconds:.3f}s sequence "
                    f"{action.sequence} lacks completion/full-charge evidence"
                )
                continue
            if evidence.completion_time_seconds > plan.duration_seconds + self._EPSILON:
                unresolved.append(
                    f"heavy attack at {action.time_seconds:.3f}s completes after the "
                    f"rotation plan horizon at {evidence.completion_time_seconds:.3f}s"
                )
                continue

            if not evidence.fully_charged:
                resolutions.append(
                    RotationHeavyAttackRestorationResolution(
                        action=action,
                        weapon=weapon_resolution.weapon,
                        evidence=evidence,
                        restoration_event=None,
                    )
                )
                continue

            base_restore = evidence.verified_base_restore
            if base_restore is None:
                base_restore = verified_heavy_attack_base_restore(weapon_resolution.weapon)
            if base_restore is None:
                unresolved.append(
                    f"fully charged {weapon_resolution.weapon.value} heavy at "
                    f"{action.time_seconds:.3f}s lacks verified base restore evidence"
                )
                continue

            modifiers = evidence.modifiers
            if modifier_resolver is not None:
                modifier_resolution = modifier_resolver(
                    action,
                    weapon_resolution.weapon,
                    evidence,
                )
                if modifier_resolution.unresolved:
                    unresolved.extend(
                        f"fully charged {weapon_resolution.weapon.value} heavy at "
                        f"{action.time_seconds:.3f}s modifier resolution: {detail}"
                        for detail in modifier_resolution.unresolved
                    )
                    continue
                modifiers = modifier_resolution.modifiers

            event = create_heavy_attack_restoration_event(
                time_seconds=evidence.completion_time_seconds,
                weapon=weapon_resolution.weapon,
                verified_base_restore=base_restore,
                modifiers=modifiers,
                source=evidence.source,
            )
            resolutions.append(
                RotationHeavyAttackRestorationResolution(
                    action=action,
                    weapon=weapon_resolution.weapon,
                    evidence=evidence,
                    restoration_event=event,
                )
            )
            events.append(event)

        return RotationHeavyAttackRestorationProjection(
            weapon_projection=weapon_projection,
            resolutions=tuple(resolutions),
            restoration_events=tuple(events),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def resolver(
        projection: RotationHeavyAttackRestorationProjection,
    ):
        """Return a replay-compatible resolver keyed to exact scheduled heavies."""

        events_by_key = {
            (float(item.action.time_seconds), int(item.action.sequence)): item.restoration_event
            for item in projection.resolutions
        }

        def resolve(action: RotationAction) -> ResourceRestorationEvent | None:
            return events_by_key.get((float(action.time_seconds), int(action.sequence)))

        return resolve

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "HeavyAttackRestorationModifierResolver",
    "RotationHeavyAttackCompletionEvidence",
    "RotationHeavyAttackResolvedModifiers",
    "RotationHeavyAttackRestorationEvidenceService",
    "RotationHeavyAttackRestorationProjection",
    "RotationHeavyAttackRestorationResolution",
]
