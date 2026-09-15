from __future__ import annotations

"""Canonical closed Extreme Weapon Damage record.

This service promotes the reviewed Phase 13.5 conditional-snapshot proof out of the
one-off audit layer.  It does not re-run the search.  The exhaustive denominator and
same-build coexistence proof remain regression/audit responsibilities; this module is
the shared read-only contract consumed by Extreme and downstream advisers.
"""

from dataclasses import dataclass

from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


WEAPON_DAMAGE_RECORD_VALUE = 13_020.810
WEAPON_DAMAGE_WINNER = ("Armor of Truth 5pc", "Kvatch Gladiator 5pc")


@dataclass(frozen=True)
class ExtremeWeaponDamageConditionalSnapshot:
    nongear_preclass_weapon_damage: float = 5_297.006
    armor_of_truth_weapon_damage: float = 589.0
    kvatch_gladiator_weapon_damage: float = 1_604.0
    expert_mage_weapon_damage: float = 648.0
    higher_max_resource: float = 49_961.0
    font_plus_calculated_defense_percent: float = 0.40
    major_brutality_percent: float = 0.20

    @property
    def named_gear_weapon_damage(self) -> float:
        return self.armor_of_truth_weapon_damage + self.kvatch_gladiator_weapon_damage

    @property
    def pre_percent_reference(self) -> float:
        return (
            self.nongear_preclass_weapon_damage
            + self.named_gear_weapon_damage
            + self.expert_mage_weapon_damage
        )

    @property
    def weapon_damage(self) -> float:
        return self.pre_percent_reference * (
            1.0
            + self.font_plus_calculated_defense_percent
            + self.major_brutality_percent
        )


class ExtremeWeaponDamageRecordService:
    """Return the reviewed U50 contextual potion-active Weapon Damage maximum."""

    RUNTIME_PREREQUISITES = (
        "Target is at or below 25% Health for Kvatch Gladiator.",
        "Armor of Truth was triggered by damaging an Off Balance target and its 10-second buff remains active.",
        "Bloodthirsty execute-side condition is active.",
        "Weapon Power potion supplies Major Brutality.",
        "Font of Power is active at the reviewed same-build higher Max Resource breakpoint.",
        "Calculated Defense is active after its reviewed shield-survival trigger.",
        "Six Sorcerer abilities remain slotted on the active bar for full Expert Mage.",
    )

    SELF_PROVIDED_CONDITIONS = (
        "Weapon Power potion: Major Brutality",
        "Font of Power active",
        "Calculated Defense active",
        "Six Sorcerer abilities slotted",
    )

    EXTERNAL_CONDITIONS = (
        "Target at or below 25% Health",
        "Target Off Balance on Armor of Truth trigger hit",
    )

    def snapshot(self) -> ExtremeWeaponDamageConditionalSnapshot:
        return ExtremeWeaponDamageConditionalSnapshot()

    def record(self) -> ExtremeRecordResult:
        snapshot = self.snapshot()
        value = snapshot.weapon_damage
        if abs(value - WEAPON_DAMAGE_RECORD_VALUE) > 0.001:
            raise RuntimeError(
                "Canonical Weapon Damage snapshot drifted from the reviewed closed record: "
                f"{value:.3f} != {WEAPON_DAMAGE_RECORD_VALUE:.3f}"
            )

        coverage = ExtremeRecordSearchCoverage(
            searched=(
                "reviewed U50 Weapon Damage named-gear semantic breakpoint denominator",
                "physical named-set topology and slot realization denominator",
                "pure-Sorcerer active-bar Expert Mage frontier",
                "same-build Max Magicka/Max Stamina resource coupling",
                "potion-active Major Brutality baseline",
                "conditional named-set coexistence snapshot",
                "Twice-Born Star finite two-Mundus resource states",
            ),
            omitted=(),
            candidates_screened=79,
            candidates_optimized=79,
            denominator_proven=True,
        )
        winning_build = {
            "sets": WEAPON_DAMAGE_WINNER,
            "nongear_preclass_weapon_damage": snapshot.nongear_preclass_weapon_damage,
            "named_gear_weapon_damage": snapshot.named_gear_weapon_damage,
            "expert_mage_weapon_damage": snapshot.expert_mage_weapon_damage,
            "higher_max_resource": snapshot.higher_max_resource,
            "font_plus_calculated_defense_percent": snapshot.font_plus_calculated_defense_percent,
            "major_brutality_percent": snapshot.major_brutality_percent,
            "pre_percent_reference": snapshot.pre_percent_reference,
        }
        return ExtremeRecordResult.for_objective(
            "weapon_damage",
            raw_value=value,
            proof_status=ExtremeRecordProofStatus.CONDITIONAL,
            winning_build=winning_build,
            unit="points",
            runtime_prerequisites=self.RUNTIME_PREREQUISITES,
            self_provided_conditions=self.SELF_PROVIDED_CONDITIONS,
            external_conditions=self.EXTERNAL_CONDITIONS,
            unresolved=(),
            ceiling_threats=(),
            search_coverage=coverage,
            explanation=(
                "The contextual potion-active U50 maximum is 13,020.810 Weapon Damage.",
                "Armor of Truth 5pc + Kvatch Gladiator 5pc is the sole physical witness tied at the validated maximum.",
                "The final denominator replay scored 79 clean physical witnesses and found zero rows above the winner.",
                "The record is conditional rather than resting/unconditional because execute, target-state, potion, and class-runtime prerequisites must coexist.",
            ),
        )


__all__ = [
    "ExtremeWeaponDamageConditionalSnapshot",
    "ExtremeWeaponDamageRecordService",
    "WEAPON_DAMAGE_RECORD_VALUE",
    "WEAPON_DAMAGE_WINNER",
]
