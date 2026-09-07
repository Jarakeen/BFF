from __future__ import annotations

from dataclasses import dataclass
from math import floor

from services.class_mastery_classification_service import ClassMasteryBoundary
from services.class_mastery_repository import ClassMasteryPassive


@dataclass(frozen=True)
class ClassMasteryExtremeContribution:
    objective_key: str
    flat: float = 0.0
    percent: float = 0.0
    additive_ratio: float = 0.0
    boundary: ClassMasteryBoundary = ClassMasteryBoundary.UNRESOLVED
    condition: str = ""


class ClassMasteryExtremeEffectService:
    """Reviewed Class Mastery contributions relevant to Extreme Build objectives.

    This is intentionally an explicit-name mapping, not a tooltip parser. Only
    passives whose numeric mechanics have been reviewed may return a contribution.
    Conditional values represent the maximum legal value of that passive and are
    tagged with the runtime boundary required to realize them; callers must not
    mix them into a resting sheet snapshot.
    """

    @staticmethod
    def _same(passive: ClassMasteryPassive, name: str, class_name: str) -> bool:
        return (
            passive.name.strip().casefold() == name.casefold()
            and passive.class_name.strip().casefold() == class_name.casefold()
        )

    @classmethod
    def contributions(
        cls,
        passive: ClassMasteryPassive,
        *,
        higher_max_resource: float | None = None,
    ) -> tuple[ClassMasteryExtremeContribution, ...]:
        # Nightblade: permanent non-Battle-Spirit critical bonus.
        if cls._same(passive, "Above and Beyond", "Nightblade"):
            return (
                ClassMasteryExtremeContribution(
                    objective_key="critical_damage",
                    additive_ratio=0.25,
                    boundary=ClassMasteryBoundary.STANDING_SELF_CONTAINED,
                    condition="Non-Battle-Spirit value; also raises the Critical Damage/Healing cap by 30 percentage points.",
                ),
            )

        # Nightblade: reaches its maximum at a target with 100% missing Health.
        if cls._same(passive, "An Eye for Exploitation", "Nightblade"):
            return cls._paired_damage_flat(
                2000.0,
                ClassMasteryBoundary.TARGET_STATE_DEPENDENT,
                "Maximum non-Battle-Spirit value at maximum target missing Health.",
            )

        # Templar Illuminate upgrade: 300 for allies, doubled for the player.
        if cls._same(passive, "Bright Harbinger", "Templar"):
            return cls._paired_damage_flat(
                600.0,
                ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                "Self value while Bright Harbinger is active from rank-2 Illuminate.",
            )

        # Warden target-state maximum: 333 per status effect, capped at 1665.
        if cls._same(passive, "Wild Adaptation", "Warden"):
            return cls._paired_damage_flat(
                1665.0,
                ClassMasteryBoundary.TARGET_STATE_DEPENDENT,
                "Maximum value with enough status effects on the target.",
            )

        # Warden Bond with Nature upgrade: self-achievable at full Health after heal.
        if cls._same(passive, "Glacial Obstinance", "Warden"):
            return cls._paired_damage_percent(
                0.15,
                ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                "10-second value after the upgraded Bond with Nature condition resolves at full Health.",
            )

        # Necromancer: 2% per Nothing Wasted stack, maximum 10 stacks.
        if cls._same(passive, "Nothing Wasted", "Necromancer"):
            condition = "Maximum 10-stack Nothing Wasted state; stacks require Corpse Consumption activity."
            return (
                ClassMasteryExtremeContribution(
                    objective_key="max_health",
                    percent=0.20,
                    boundary=ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                    condition=condition,
                ),
                *cls._paired_damage_percent(
                    0.20,
                    ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                    condition,
                ),
            )

        # Sorcerer: 6% plus 1% per complete 1750 of the higher Max Mag/Stam.
        if cls._same(passive, "Font of Power", "Sorcerer"):
            if higher_max_resource is None:
                return ()
            resource = max(0.0, float(higher_max_resource))
            percent = 0.06 + (floor(resource / 1750.0) * 0.01)
            return cls._paired_damage_percent(
                percent,
                ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                f"Font of Power active; 6% base plus 1% per complete 1750 higher Max Magicka/Stamina ({resource:g}).",
            )

        # Sorcerer shield survives, then the 20-second self/group power buff applies.
        if cls._same(passive, "Calculated Defense", "Sorcerer"):
            return cls._paired_damage_percent(
                0.06,
                ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                "20-second value after the Calculated Defense shield does not break.",
            )

        if cls._same(passive, "Sphere of Influence", "Sorcerer"):
            return cls._triple_recovery_flat(
                225.0,
                "12-second recovery value after casting a damage shield on yourself or an ally.",
            )

        if cls._same(passive, "Devout Guardian", "Templar"):
            return cls._triple_recovery_flat(
                300.0,
                "Recovery value while the Sacred Ground damage shield is active.",
            )

        return ()

    @staticmethod
    def _paired_damage_flat(
        value: float,
        boundary: ClassMasteryBoundary,
        condition: str,
    ) -> tuple[ClassMasteryExtremeContribution, ...]:
        return tuple(
            ClassMasteryExtremeContribution(
                objective_key=key,
                flat=float(value),
                boundary=boundary,
                condition=condition,
            )
            for key in ("weapon_damage", "spell_damage")
        )

    @staticmethod
    def _paired_damage_percent(
        value: float,
        boundary: ClassMasteryBoundary,
        condition: str,
    ) -> tuple[ClassMasteryExtremeContribution, ...]:
        return tuple(
            ClassMasteryExtremeContribution(
                objective_key=key,
                percent=float(value),
                boundary=boundary,
                condition=condition,
            )
            for key in ("weapon_damage", "spell_damage")
        )

    @staticmethod
    def _triple_recovery_flat(
        value: float,
        condition: str,
    ) -> tuple[ClassMasteryExtremeContribution, ...]:
        return tuple(
            ClassMasteryExtremeContribution(
                objective_key=key,
                flat=float(value),
                boundary=ClassMasteryBoundary.COMBAT_STATE_DEPENDENT,
                condition=condition,
            )
            for key in ("health_recovery", "magicka_recovery", "stamina_recovery")
        )
