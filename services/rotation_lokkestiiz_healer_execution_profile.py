from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RotationExecutionRequirementKind(str, Enum):
    SKILL = "skill"
    ULTIMATE = "ultimate"
    LIGHT_ATTACK = "light_attack"
    EFFECT = "effect"
    HEALING_OUTCOME = "healing_outcome"


@dataclass(frozen=True)
class RotationExecutionRequirement:
    """One explicit caller-authored execution obligation.

    This contract intentionally carries semantic lower_snake_case identity and
    player strategy only. It does not invent encounter timestamps, numeric ability
    IDs, healing thresholds, or resource restoration values.
    """

    key: str
    kind: RotationExecutionRequirementKind
    semantic_id: str
    minimum_casts: int | None = None
    target: str | None = None
    timing: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        key = str(self.key or "").strip()
        semantic_id = str(self.semantic_id or "").strip().casefold()
        if not key:
            raise ValueError("rotation execution requirement key is required")
        if not semantic_id:
            raise ValueError("rotation execution semantic_id is required")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "semantic_id", semantic_id)

        if not isinstance(self.kind, RotationExecutionRequirementKind):
            object.__setattr__(
                self,
                "kind",
                RotationExecutionRequirementKind(str(self.kind)),
            )

        if self.minimum_casts is not None:
            casts = int(self.minimum_casts)
            if casts <= 0:
                raise ValueError("minimum_casts must be positive when supplied")
            object.__setattr__(self, "minimum_casts", casts)

        if self.target is not None:
            object.__setattr__(self, "target", str(self.target).strip() or None)
        if self.timing is not None:
            object.__setattr__(self, "timing", str(self.timing).strip() or None)
        object.__setattr__(self, "notes", str(self.notes or "").strip())


@dataclass(frozen=True)
class RotationExecutionStage:
    key: str
    label: str
    requirements: tuple[RotationExecutionRequirement, ...]

    def __post_init__(self) -> None:
        key = str(self.key or "").strip()
        label = str(self.label or "").strip()
        if not key or not label:
            raise ValueError("rotation execution stage requires key and label")
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "requirements", tuple(self.requirements))


@dataclass(frozen=True)
class LokkestiizHealerExecutionProfile:
    character_name: str
    build_name: str
    encounter_id: str
    requested_cycles: int
    canonical_flight_health_thresholds: tuple[int, ...]
    stages: tuple[RotationExecutionStage, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def canonical_flight_count(self) -> int:
        return len(self.canonical_flight_health_thresholds)

    @property
    def ready_for_clock_scheduling(self) -> bool:
        return not self.unresolved

    @property
    def required_skill_ids(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for stage in self.stages:
            for requirement in stage.requirements:
                if requirement.kind is not RotationExecutionRequirementKind.SKILL:
                    continue
                if requirement.semantic_id in seen:
                    continue
                seen.add(requirement.semantic_id)
                ordered.append(requirement.semantic_id)
        return tuple(ordered)


def build_magrat_df_healer_lokkestiiz_profile(
    *,
    canonical_flight_health_thresholds: tuple[int, ...] = (80, 50, 20),
    requested_cycles: int = 4,
) -> LokkestiizHealerExecutionProfile:
    """Return the first real Phase-13 healer execution profile.

    The strategy is caller-authored for Magrat -> DF Healer. The canonical encounter
    evidence currently identifies Lokkestiiz Aerial Onslaught at 80/50/20 health.
    Exact clock timing remains intentionally unresolved because health thresholds are
    not converted into seconds by the rotation engine.
    """

    cycles = int(requested_cycles)
    if cycles <= 0:
        raise ValueError("requested_cycles must be positive")
    thresholds = tuple(int(value) for value in canonical_flight_health_thresholds)

    landing = RotationExecutionStage(
        key="landing",
        label="Boss landing / damageable window",
        requirements=(
            RotationExecutionRequirement(
                key="landing_ultimate",
                kind=RotationExecutionRequirementKind.ULTIMATE,
                semantic_id="selected_ultimate",
                minimum_casts=1,
                target="raid_or_boss_as_selected_ultimate_requires",
                timing="as_soon_as_lokkestiiz_lands",
                notes="Ultimate must be affordable at each landing.",
            ),
            RotationExecutionRequirement(
                key="landing_elemental_susceptibility",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="elemental_susceptibility",
                minimum_casts=1,
                target="lokkestiiz",
                timing="after_landing_ultimate",
            ),
            RotationExecutionRequirement(
                key="landing_elemental_blockade",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="elemental_blockade",
                minimum_casts=1,
                target="lokkestiiz",
                timing="after_elemental_susceptibility",
            ),
            RotationExecutionRequirement(
                key="damageable_major_brittle",
                kind=RotationExecutionRequirementKind.EFFECT,
                semantic_id="major_brittle",
                target="lokkestiiz",
                timing="boss_damageable_non_immune_windows",
                notes="Maintain during eligible dragon uptime; never demand it while the boss is immune/untargetable.",
            ),
            RotationExecutionRequirement(
                key="ultimate_regeneration_light_attacks",
                kind=RotationExecutionRequirementKind.LIGHT_ATTACK,
                semantic_id="light_attack",
                target="lokkestiiz_or_available_enemy",
                timing="between_landings",
                notes="Use enough successful damaging light attacks to restore the selected Ultimate before the next landing; exact cast count is derived from runtime Ultimate evidence, not guessed here.",
            ),
        ),
    )

    first_cage = RotationExecutionStage(
        key="ice_cage_one",
        label="First Ice Cage",
        requirements=(
            RotationExecutionRequirement(
                key="cage_one_budding_seeds",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="budding_seeds",
                minimum_casts=1,
                target="ice_cage_one",
            ),
            RotationExecutionRequirement(
                key="cage_one_illustrious_healing",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="illustrious_healing",
                minimum_casts=1,
                target="ice_cage_one",
            ),
            RotationExecutionRequirement(
                key="cage_one_combat_prayer",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="combat_prayer",
                minimum_casts=5,
                target="ice_cage_one",
            ),
        ),
    )

    second_cage = RotationExecutionStage(
        key="ice_cage_two",
        label="Second Ice Cage",
        requirements=(
            RotationExecutionRequirement(
                key="cage_two_budding_seeds",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="budding_seeds",
                minimum_casts=1,
                target="ice_cage_two",
            ),
            RotationExecutionRequirement(
                key="cage_two_illustrious_healing",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="illustrious_healing",
                minimum_casts=1,
                target="ice_cage_two",
            ),
            RotationExecutionRequirement(
                key="cage_two_combat_prayer",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="combat_prayer",
                minimum_casts=2,
                target="ice_cage_two",
            ),
        ),
    )

    add_phase = RotationExecutionStage(
        key="add_phase",
        label="Aerial Onslaught add phase",
        requirements=(
            RotationExecutionRequirement(
                key="supplemental_add_phase_healing",
                kind=RotationExecutionRequirementKind.HEALING_OUTCOME,
                semantic_id="supplemental_healing",
                target="raid_group",
                timing="while_lokkestiiz_is_airborne_and_adds_are_active",
                notes="Remain able to provide supplemental healing; no invented HPS threshold is attached.",
            ),
        ),
    )

    static_phase = RotationExecutionStage(
        key="static_phase",
        label="Static Phase",
        requirements=(
            RotationExecutionRequirement(
                key="static_budding_seeds",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="budding_seeds",
                minimum_casts=1,
                target="raid_group",
            ),
            RotationExecutionRequirement(
                key="static_illustrious_healing",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="illustrious_healing",
                minimum_casts=1,
                target="raid_group",
            ),
            RotationExecutionRequirement(
                key="static_energy_orb",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="energy_orb",
                minimum_casts=1,
                target="raid_group",
            ),
            RotationExecutionRequirement(
                key="static_combat_prayer",
                kind=RotationExecutionRequirementKind.SKILL,
                semantic_id="combat_prayer",
                minimum_casts=None,
                target="raid_group",
                timing="repeat_until_static_phase_ends",
                notes="Caller requested several casts; exact minimum remains unresolved instead of converting 'several' into an arbitrary number.",
            ),
        ),
    )

    unresolved: list[str] = []
    if len(thresholds) != cycles:
        unresolved.append(
            "requested execution cycle count does not match canonical Aerial Onslaught trigger count: "
            f"requested={cycles}, canonical={len(thresholds)} at health thresholds {thresholds}"
        )
    unresolved.extend(
        (
            "Lokkestiiz landing, Ice Cage, add-phase, and Static Phase clock windows are not yet canonically resolved in seconds",
            "light-attack count required to restore the selected Ultimate is runtime-dependent and must be derived from Ultimate cost/generation evidence",
            "Static Phase Combat Prayer minimum is qualitative ('several') and has no caller-supplied numeric minimum",
        )
    )

    return LokkestiizHealerExecutionProfile(
        character_name="Magrat",
        build_name="DF Healer",
        encounter_id="lokkestiiz",
        requested_cycles=cycles,
        canonical_flight_health_thresholds=thresholds,
        stages=(landing, first_cage, second_cage, add_phase, static_phase),
        unresolved=tuple(unresolved),
    )


__all__ = [
    "LokkestiizHealerExecutionProfile",
    "RotationExecutionRequirement",
    "RotationExecutionRequirementKind",
    "RotationExecutionStage",
    "build_magrat_df_healer_lokkestiiz_profile",
]
