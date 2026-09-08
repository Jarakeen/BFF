from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.rotation_demand_window import RotationDemandWindow
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement


@dataclass(frozen=True)
class RotationMechanicsDependency:
    """One canonical mechanics coverage area that can affect this rotation decision.

    ``evidence`` records the exact build/evaluation identities that made the broad
    coverage area relevant. These labels are diagnostic provenance only; they do not
    claim any ESO mechanic that has not already been canonically modeled.
    """

    key: str
    reason: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        key = str(self.key or "").strip()
        reason = str(self.reason or "").strip()
        if not key:
            raise ValueError("rotation mechanics dependency key must be non-empty")
        if not reason:
            raise ValueError("rotation mechanics dependency reason must be non-empty")

        normalized_evidence: list[str] = []
        seen: set[str] = set()
        for item in self.evidence:
            value = str(item or "").strip()
            folded = value.casefold()
            if not value or folded in seen:
                continue
            seen.add(folded)
            normalized_evidence.append(value)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "evidence", tuple(normalized_evidence))


class RotationMechanicsDependencyService:
    """Discover mechanics coverage needed by one canonical rotation decision.

    This service does not claim that every referenced mechanics area is incomplete or
    blocking. It identifies which shared coverage rows are relevant to the build and
    evidence currently being evaluated. The coverage report remains responsible for
    saying whether each dependency is calculation-ready, advisory, or blocking.

    Exact selected identities are retained on each dependency so future research and
    UI surfaces can explain *why* a broad mechanics domain mattered for this build.
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
            evidence=(
                f"class={character_build.character_class.value}",
                f"role={character_build.role.value}",
                f"build={character_build.name}",
            ),
        )

        bars = character_build.bars()
        represented_skill_lines: tuple[str, ...] = ()
        if bars:
            slotted_skills = tuple(
                f"{bar.bar_id.value}:{slot.skill_id}"
                for bar in bars
                for slot in bar.slots
                if str(getattr(slot, "skill_id", "") or "").strip()
            )
            skill_lines = tuple(
                f"skill_line={slot.skill_line_id}"
                for bar in bars
                for slot in bar.slots
                if str(getattr(slot, "skill_line_id", "") or "").strip()
            )
            represented_skill_lines = tuple(
                f"represented_skill_line={value}"
                for value in dict.fromkeys(
                    str(getattr(slot, "skill_line_id", "") or "").strip()
                    for bar in bars
                    for slot in bar.slots
                    if str(getattr(slot, "skill_line_id", "") or "").strip()
                )
            )
            weapon_types = tuple(
                f"{bar.bar_id.value}:weapon={bar.main_hand.weapon_type.value}"
                for bar in bars
            )
            self._add(
                dependencies,
                "skills:runtime_topology",
                "The build has slotted bars, so skill timing, duration, targeting, channel, and runtime behavior can affect the rotation.",
                evidence=slotted_skills + skill_lines,
            )
            self._add(
                dependencies,
                "weapons:bash_interrupt_poison_topology",
                "The build has equipped weapon bars, so weapon timing and weapon-specific runtime behavior can affect legal actions.",
                evidence=weapon_types,
            )

        equipped = character_build.all_armor_pieces()
        set_ids = tuple(
            f"set={piece.set_id}"
            for piece in equipped
            if str(piece.set_id or "").strip()
        )
        weights = tuple(
            f"armor_weight={piece.weight}"
            for piece in equipped
            if str(piece.weight or "").strip()
        )
        normalized_weights = [
            str(piece.weight or "").strip().casefold()
            for piece in equipped
            if str(piece.weight or "").strip()
        ]
        weight_counts = Counter(normalized_weights)
        armor_weight_evidence = tuple(
            f"armor_weight_count:{weight}={weight_counts[weight]}"
            for weight in sorted(weight_counts)
        )
        effect_slots = tuple(
            f"effect_bearing_slot={piece.slot.value}"
            for piece in equipped
            if piece.effects
        )
        if any(piece.set_id or piece.effects for piece in equipped):
            self._add(
                dependencies,
                "gear:conditional_topology",
                "The build equips set or effect-bearing gear whose runtime conditions can alter rotation legality, duration, or value.",
                evidence=set_ids + weights + effect_slots,
            )
        if any(piece.effects for piece in equipped):
            self._add(
                dependencies,
                "procs:conditional_topology",
                "Equipped gear carries explicit effect variants, so proc trigger, cooldown, stacking, or refresh behavior can matter.",
                evidence=effect_slots + set_ids,
            )

        if character_build.potion_id or character_build.poison_id:
            consumables = tuple(
                item
                for item in (
                    f"potion={character_build.potion_id}" if character_build.potion_id else "",
                    f"poison={character_build.poison_id}" if character_build.poison_id else "",
                )
                if item
            )
            self._add(
                dependencies,
                "consumables:runtime_resource_and_buff_policy",
                "The build selects a potion or poison whose runtime resource, buff, debuff, or cooldown behavior can affect the schedule.",
                evidence=consumables,
            )

        if passives or character_build.class_mastery.passive_ability_ids or armor_weight_evidence:
            passive_lines = tuple(
                f"passive_skill_line={value}"
                for value in (
                    str(getattr(passive, "skill_line_id", "") or "").strip()
                    for passive in passives
                )
                if value
            )
            mastery = tuple(
                f"class_mastery_passive={passive_id}"
                for passive_id in character_build.class_mastery.passive_ability_ids
            )
            reasons: list[str] = []
            if passives or mastery:
                reasons.append(
                    "Explicit passive or Class Mastery evidence can modify skill, resource, duration, or combat behavior."
                )
            if armor_weight_evidence:
                reasons.append(
                    "Equipped armor-weight distribution can make verified armor passive bonuses relevant to timing, sustain, mitigation, or output."
                )
            self._add(
                dependencies,
                "passives:runtime_semantics",
                " ".join(reasons),
                evidence=(
                    passive_lines
                    + mastery
                    + armor_weight_evidence
                    + represented_skill_lines
                ),
            )

        if requirements:
            self._add(
                dependencies,
                "effect_duration:build_modifiers",
                "The rotation has explicit effect-uptime requirements, so build-derived duration modifiers can change refresh timing and measured uptime.",
                evidence=(f"uptime_requirement_count={len(requirements)}",),
            )
            self._add(
                dependencies,
                "assignment:rotation_fulfillment_catalog",
                "The rotation has explicit effect obligations that must be tied to verified fulfillment semantics rather than inferred from role labels.",
                evidence=(f"effect_obligation_count={len(requirements)}",),
            )

        if demands:
            self._add(
                dependencies,
                "encounter:target_range_movement_topology",
                "Encounter demand windows are present, so target, range, movement, downtime, or phase constraints can alter legal rotation timing.",
                evidence=(f"encounter_demand_count={len(demands)}",),
            )

        if recovery_enabled:
            self._add(
                dependencies,
                "heavy_attack:restoration",
                "The candidate pipeline may use recovery-heavy decisions, so verified heavy restoration and completion semantics can affect candidate legality.",
                evidence=("recovery_heavy_candidate_path=enabled",),
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
        *,
        evidence: tuple[str, ...] = (),
    ) -> None:
        normalized = key.casefold()
        for index, item in enumerate(dependencies):
            if item.key.casefold() != normalized:
                continue
            dependencies[index] = RotationMechanicsDependency(
                key=item.key,
                reason=item.reason,
                evidence=item.evidence + tuple(evidence),
            )
            return
        dependencies.append(
            RotationMechanicsDependency(
                key=key,
                reason=reason,
                evidence=tuple(evidence),
            )
        )


__all__ = [
    "RotationMechanicsDependency",
    "RotationMechanicsDependencyService",
]
