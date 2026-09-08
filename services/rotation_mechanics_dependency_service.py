from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.rotation_demand_window import RotationDemandWindow
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement


@dataclass(frozen=True)
class RotationMechanicsDependency:
    """One canonical mechanics coverage area that can affect this rotation decision."""

    key: str
    reason: str

    def __post_init__(self) -> None:
        key = str(self.key or "").strip()
        reason = str(self.reason or "").strip()
        if not key:
            raise ValueError("rotation mechanics dependency key must be non-empty")
        if not reason:
            raise ValueError("rotation mechanics dependency reason must be non-empty")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "reason", reason)


class RotationMechanicsDependencyService:
    """Discover broad mechanics coverage needed by one canonical rotation decision.

    This service does not claim that every referenced mechanics area is incomplete or
    blocking. It only identifies which shared coverage rows are relevant to the build
    and evidence currently being evaluated. The coverage report remains responsible
    for saying whether each dependency is calculation-ready, advisory, or blocking.
    """

    def discover(
        self,
        *,
        character_build: CharacterBuild,
        demands: tuple[RotationDemandWindow, ...] = (),
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: tuple[PassiveGrant, ...] = (),
        recovery_enabled: bool = True,
    ) -> tuple[RotationMechanicsDependency, ...]:
        dependencies: list[RotationMechanicsDependency] = []

        self._add(
            dependencies,
            "saved_build:canonical_structure",
            "The rotation is evaluated from a canonical CharacterBuild and depends on its resolved build identity.",
        )

        bars = character_build.bars()
        if bars:
            self._add(
                dependencies,
                "skills:runtime_topology",
                "The build has slotted bars, so skill timing, duration, targeting, channel, and runtime behavior can affect the rotation.",
            )
            self._add(
                dependencies,
                "weapons:bash_interrupt_poison_topology",
                "The build has equipped weapon bars, so weapon timing and weapon-specific runtime behavior can affect legal actions.",
            )

        equipped = character_build.all_armor_pieces()
        if any(piece.set_id or piece.effects for piece in equipped):
            self._add(
                dependencies,
                "gear:conditional_topology",
                "The build equips set or effect-bearing gear whose runtime conditions can alter rotation legality, duration, or value.",
            )
        if any(piece.effects for piece in equipped):
            self._add(
                dependencies,
                "procs:conditional_topology",
                "Equipped gear carries explicit effect variants, so proc trigger, cooldown, stacking, or refresh behavior can matter.",
            )

        if character_build.potion_id or character_build.poison_id:
            self._add(
                dependencies,
                "consumables:runtime_resource_and_buff_policy",
                "The build selects a potion or poison whose runtime resource, buff, debuff, or cooldown behavior can affect the schedule.",
            )

        if passives or character_build.class_mastery.passive_ability_ids:
            self._add(
                dependencies,
                "passives:runtime_semantics",
                "Explicit passive or Class Mastery evidence is present and can modify skill, resource, duration, or combat behavior.",
            )

        if requirements:
            self._add(
                dependencies,
                "effect_duration:build_modifiers",
                "The rotation has explicit effect-uptime requirements, so build-derived duration modifiers can change refresh timing and measured uptime.",
            )
            self._add(
                dependencies,
                "assignment:rotation_fulfillment_catalog",
                "The rotation has explicit effect obligations that must be tied to verified fulfillment semantics rather than inferred from role labels.",
            )

        if demands:
            self._add(
                dependencies,
                "encounter:target_range_movement_topology",
                "Encounter demand windows are present, so target, range, movement, downtime, or phase constraints can alter legal rotation timing.",
            )

        if recovery_enabled:
            self._add(
                dependencies,
                "heavy_attack:restoration",
                "The candidate pipeline may use recovery-heavy decisions, so verified heavy restoration and completion semantics can affect candidate legality.",
            )

        return tuple(dependencies)

    @staticmethod
    def keys(
        dependencies: tuple[RotationMechanicsDependency, ...],
    ) -> tuple[str, ...]:
        return tuple(item.key for item in dependencies)

    @staticmethod
    def _add(
        dependencies: list[RotationMechanicsDependency],
        key: str,
        reason: str,
    ) -> None:
        normalized = key.casefold()
        if any(item.key.casefold() == normalized for item in dependencies):
            return
        dependencies.append(RotationMechanicsDependency(key=key, reason=reason))


__all__ = [
    "RotationMechanicsDependency",
    "RotationMechanicsDependencyService",
]
