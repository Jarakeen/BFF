from __future__ import annotations

"""Machine-readable runtime ownership for closed Extreme power records.

Weapon/Spell Damage records are closed conditional snapshots, but their prerequisites
span more than one canonical owner.  E1's unified runtime snapshot owns ordered player
runtime history (potions, gear procs, external group buffs, skill-triggered buffs),
while target facts and standing structural/class state remain separate inputs.

This service keeps those boundaries explicit so downstream Extreme/Rotation consumers
never need to parse human-readable record prerequisite strings.
"""

from dataclasses import dataclass
from enum import Enum


class ExtremePowerRequirementOwner(str, Enum):
    RUNTIME_HISTORY = "runtime_history"
    TARGET_STATE = "target_state"
    STRUCTURAL_STATE = "structural_state"
    CLASS_RUNTIME = "class_runtime"
    ACTIVE_BAR = "active_bar"


@dataclass(frozen=True)
class ExtremePowerRecordRequirement:
    requirement_id: str
    objective_key: str
    owner: ExtremePowerRequirementOwner
    description: str
    runtime_history_kind: str | None = None
    external: bool = False

    @property
    def unified_runtime_snapshot_owned(self) -> bool:
        return self.owner is ExtremePowerRequirementOwner.RUNTIME_HISTORY


class ExtremePowerRecordRuntimeRequirementService:
    """Return reviewed requirement ownership for closed Weapon/Spell Damage records."""

    _SHARED = (
        ExtremePowerRecordRequirement(
            requirement_id="armor_of_truth_active",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.RUNTIME_HISTORY,
            description="Armor of Truth was triggered and its 10-second buff remains active.",
            runtime_history_kind="gear_proc",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="target_execute_health",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.TARGET_STATE,
            description="Target is at or below 25% Health for Kvatch Gladiator and Bloodthirsty.",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="target_off_balance_trigger",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.TARGET_STATE,
            description="Armor of Truth trigger hit occurs while the target is Off Balance.",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="font_of_power_active",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.CLASS_RUNTIME,
            description="Sorcerer Font of Power is active at the reviewed same-build resource state.",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="calculated_defense_active",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.CLASS_RUNTIME,
            description="Sorcerer Calculated Defense is active after its reviewed shield-survival trigger.",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="six_sorcerer_abilities_slotted",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.ACTIVE_BAR,
            description="Six Sorcerer abilities are slotted on the active bar for full Expert Mage.",
        ),
        ExtremePowerRecordRequirement(
            requirement_id="same_build_higher_resource",
            objective_key="*",
            owner=ExtremePowerRequirementOwner.STRUCTURAL_STATE,
            description="The same build supplies the reviewed higher Max Resource breakpoint.",
        ),
    )

    _BY_OBJECTIVE = {
        "weapon_damage": (
            ExtremePowerRecordRequirement(
                requirement_id="weapon_power_potion",
                objective_key="weapon_damage",
                owner=ExtremePowerRequirementOwner.RUNTIME_HISTORY,
                description="Weapon Power potion supplies Major Brutality.",
                runtime_history_kind="potion_use",
            ),
            ExtremePowerRecordRequirement(
                requirement_id="external_minor_brutality",
                objective_key="weapon_damage",
                owner=ExtremePowerRequirementOwner.RUNTIME_HISTORY,
                description="A proven external group source supplies Minor Brutality.",
                runtime_history_kind="external_group_buff",
                external=True,
            ),
        ),
        "spell_damage": (
            ExtremePowerRecordRequirement(
                requirement_id="spell_power_potion",
                objective_key="spell_damage",
                owner=ExtremePowerRequirementOwner.RUNTIME_HISTORY,
                description="Spell Power potion supplies Major Sorcery.",
                runtime_history_kind="potion_use",
            ),
            ExtremePowerRecordRequirement(
                requirement_id="external_minor_sorcery",
                objective_key="spell_damage",
                owner=ExtremePowerRequirementOwner.RUNTIME_HISTORY,
                description="A proven external group source supplies Minor Sorcery.",
                runtime_history_kind="external_group_buff",
                external=True,
            ),
        ),
    }

    @classmethod
    def requirements_for(cls, objective_key: str) -> tuple[ExtremePowerRecordRequirement, ...]:
        objective = str(objective_key or "").strip().casefold()
        specific = cls._BY_OBJECTIVE.get(objective)
        if specific is None:
            raise KeyError(f"unreviewed Extreme power-record objective: {objective_key!r}")
        shared = tuple(
            ExtremePowerRecordRequirement(
                requirement_id=row.requirement_id,
                objective_key=objective,
                owner=row.owner,
                description=row.description,
                runtime_history_kind=row.runtime_history_kind,
                external=row.external,
            )
            for row in cls._SHARED
        )
        return (*shared, *specific)

    @classmethod
    def grouped_by_owner(
        cls,
        objective_key: str,
    ) -> dict[ExtremePowerRequirementOwner, tuple[ExtremePowerRecordRequirement, ...]]:
        rows = cls.requirements_for(objective_key)
        return {
            owner: tuple(row for row in rows if row.owner is owner)
            for owner in ExtremePowerRequirementOwner
        }


__all__ = [
    "ExtremePowerRecordRequirement",
    "ExtremePowerRecordRuntimeRequirementService",
    "ExtremePowerRequirementOwner",
]
