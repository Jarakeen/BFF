from __future__ import annotations

"""Classify weapon-ability damage occurrences for enchantment activation.

ZOS weapon-enchantment activation is occurrence-driven: Light/Heavy attacks and
weapon abilities may attempt a proc when damage lands, but single-target Damage
over Time ticks are excluded from the weapon-ability path. This service resolves
that distinction from the same canonical per-coefficient component identity used
by DD damage evidence. It never infers direct/DoT or AoE/single-target shape from
ability names, timing, or occurrence count.
"""

from minmax.skill_coefficient_repository import SkillCoefficientRepository
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences,
)
from services.rotation_dd_reviewed_skill_component_repository import (
    RotationDDReviewedSkillComponentRepository,
)


class ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier:
    """Keep only canonically eligible weapon-ability damage occurrences."""

    def __init__(
        self,
        *,
        coefficient_repository: object,
        component_repository: object,
    ) -> None:
        if coefficient_repository is None:
            raise ValueError(
                "weapon-ability enchant occurrence classification requires coefficient repository"
            )
        if component_repository is None:
            raise ValueError(
                "weapon-ability enchant occurrence classification requires component repository"
            )
        self.coefficient_repository = coefficient_repository
        self.component_repository = component_repository

    @classmethod
    def from_database(cls, database_path):
        return cls(
            coefficient_repository=SkillCoefficientRepository(database_path),
            component_repository=RotationDDReviewedSkillComponentRepository(
                database_path
            ),
        )

    def resolve(
        self,
        *,
        candidate,
        action,
        occurrence_evidence,
    ) -> ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences:
        del candidate  # candidate identity is intentionally not mechanics evidence.

        ability_name = str(getattr(action, "name", "") or "").strip()
        if not ability_name:
            return ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences(
                occurrences=(),
                unresolved=(
                    "weapon-ability occurrence classification requires ability name",
                ),
            )

        resolution = self.coefficient_repository.resolve_entity_id(ability_name)
        resolution_unresolved = tuple(
            str(item).strip()
            for item in tuple(getattr(resolution, "unresolved", ()) or ())
            if str(item).strip()
        )
        skill = getattr(resolution, "rank", None)
        if resolution_unresolved or skill is None:
            detail = resolution_unresolved or (
                f"canonical skill rank is unavailable for {ability_name}",
            )
            return ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences(
                occurrences=(),
                unresolved=tuple(detail),
            )

        kept: list[object] = []
        unresolved: list[str] = []
        reviewed = 0
        excluded_single_target_dot = 0

        for occurrence in tuple(getattr(occurrence_evidence, "occurrences", ()) or ()):
            coefficient_number = getattr(occurrence, "coefficient_number", None)
            if coefficient_number is None:
                unresolved.append(
                    f"{ability_name}: damage occurrence at "
                    f"{float(occurrence.time_seconds):g}s lacks coefficient identity"
                )
                continue

            component = self.component_repository.get_component(
                int(skill.skill_rank_id),
                int(coefficient_number),
            )
            if component is None:
                unresolved.append(
                    f"{ability_name}: coefficient {int(coefficient_number)} "
                    "has no canonical component classification"
                )
                continue
            is_damage = getattr(component, "is_damage", None)
            if not isinstance(is_damage, bool):
                unresolved.append(
                    f"{ability_name}: coefficient {int(coefficient_number)} "
                    "requires boolean damage-component classification"
                )
                continue
            if not is_damage:
                unresolved.append(
                    f"{ability_name}: coefficient {int(coefficient_number)} "
                    "damage occurrence conflicts with non-damage component classification"
                )
                continue

            is_dot = getattr(component, "is_dot", None)
            is_aoe = getattr(component, "is_aoe", None)
            if not isinstance(is_dot, bool) or not isinstance(is_aoe, bool):
                unresolved.append(
                    f"{ability_name}: coefficient {int(coefficient_number)} "
                    "requires reviewed DoT and AoE identity for enchant eligibility"
                )
                continue

            reviewed += 1
            if is_dot and not is_aoe:
                excluded_single_target_dot += 1
                continue
            kept.append(occurrence)

        if unresolved:
            return ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences(
                occurrences=(),
                evidence=(
                    f"Reviewed weapon-ability occurrences: {reviewed}",
                    f"Excluded single-target DoT occurrences: {excluded_single_target_dot}",
                ),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        return ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences(
            occurrences=tuple(kept),
            evidence=(
                f"Reviewed weapon-ability occurrences: {reviewed}",
                f"Excluded single-target DoT occurrences: {excluded_single_target_dot}",
                "Direct damage and area Damage over Time remain eligible; single-target Damage over Time is excluded",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier",
]
