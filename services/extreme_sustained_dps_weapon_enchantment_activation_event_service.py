from __future__ import annotations

"""Derive ZOS-proven weapon-enchantment activation opportunities for Objective #32.

This service does not decide whether an enchantment actually procs. It identifies
only the damage events that are eligible to *attempt* activation: landed Light
Attacks, landed Heavy Attacks, and landed damage occurrences owned by canonical
weapon-line abilities. Cooldown state, weapon-source selection, poison replacement,
off-bar persistence, and same-identity cooldown behavior remain separate evidence.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind
from minmax.runtime_event import RuntimeEvent
from minmax.skill_line_repository import SkillLineRepository
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER = "weapon_enchantment_activation"

_WEAPON_SKILL_LINES = frozenset(
    {
        "one hand and shield",
        "two handed",
        "dual wield",
        "bow",
        "destruction staff",
        "restoration staff",
    }
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences:
    occurrences: tuple[object, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentActivationEventResult:
    events: tuple[RuntimeEvent, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentActivationEventService:
    """Resolve exact damage events eligible to attempt a weapon enchantment proc."""

    def __init__(
        self,
        *,
        skill_line_repository: object,
        weapon_ability_occurrence_classifier: object | None = None,
    ) -> None:
        if skill_line_repository is None:
            raise ValueError(
                "weapon-enchantment activation events require canonical skill-line repository"
            )
        self.skill_line_repository = skill_line_repository
        self.weapon_ability_occurrence_classifier = (
            weapon_ability_occurrence_classifier
        )

    @classmethod
    def from_database(
        cls,
        database_path,
        *,
        weapon_ability_occurrence_classifier: object | None = None,
    ):
        if weapon_ability_occurrence_classifier is None:
            from services.extreme_sustained_dps_weapon_ability_enchantment_occurrence_classifier import (
                ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier,
            )

            weapon_ability_occurrence_classifier = (
                ExtremeSustainedDPSWeaponAbilityEnchantmentOccurrenceClassifier.from_database(
                    database_path
                )
            )
        return cls(
            skill_line_repository=SkillLineRepository(database_path),
            weapon_ability_occurrence_classifier=weapon_ability_occurrence_classifier,
        )

    @staticmethod
    def _action_identity(action) -> str:
        return (
            f"{float(action.time_seconds):g}s #{int(action.sequence)} "
            f"{action.kind.value} {str(action.name or '').strip()}".strip()
        )

    def _is_weapon_action(self, action) -> tuple[bool, str | None]:
        if action.kind in {
            RotationActionKind.LIGHT_ATTACK,
            RotationActionKind.HEAVY_ATTACK,
        }:
            return True, None

        if action.kind not in {
            RotationActionKind.SKILL,
            RotationActionKind.ULTIMATE,
        }:
            return False, None

        ability_name = str(action.name or "").strip()
        if not ability_name:
            return False, (
                f"{self._action_identity(action)}: weapon-enchantment activation "
                "classification requires ability name"
            )

        skill_line = self.skill_line_repository.skill_line_for_ability_name(
            ability_name
        )
        if not str(skill_line or "").strip():
            return False, (
                f"{self._action_identity(action)}: canonical skill line is unavailable "
                "for weapon-enchantment activation classification"
            )

        return str(skill_line).strip().casefold() in _WEAPON_SKILL_LINES, None

    def resolve(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        occurrence_provider: object,
        target_identity: str | None = None,
    ) -> ExtremeSustainedDPSWeaponEnchantmentActivationEventResult:
        if occurrence_provider is None:
            return ExtremeSustainedDPSWeaponEnchantmentActivationEventResult(
                events=(),
                evidence=(),
                unresolved=(
                    "Weapon-enchantment activation opportunities require canonical exact-time damage occurrence evidence",
                ),
            )

        events: list[RuntimeEvent] = []
        unresolved: list[str] = []
        inspected = 0
        eligible_actions = 0

        for action in candidate.plan.actions:
            is_weapon, classification_unresolved = self._is_weapon_action(action)
            if classification_unresolved:
                unresolved.append(classification_unresolved)
                continue
            if not is_weapon:
                continue

            eligible_actions += 1
            inspected += 1
            evidence = occurrence_provider.evaluate_action_occurrences(
                candidate=candidate,
                action=action,
            )
            if tuple(evidence.unresolved):
                unresolved.extend(
                    f"{self._action_identity(action)}: {item}"
                    for item in tuple(evidence.unresolved)
                )
                continue

            occurrences = tuple(evidence.occurrences)
            if action.kind in {
                RotationActionKind.SKILL,
                RotationActionKind.ULTIMATE,
            }:
                if self.weapon_ability_occurrence_classifier is None:
                    unresolved.append(
                        f"{self._action_identity(action)}: weapon-ability enchantment "
                        "activation requires occurrence-level eligibility classification "
                        "because single-target Damage over Time ticks are excluded"
                    )
                    continue
                classified = self.weapon_ability_occurrence_classifier.resolve(
                    candidate=candidate,
                    action=action,
                    occurrence_evidence=evidence,
                )
                unresolved.extend(
                    f"{self._action_identity(action)}: {item}"
                    for item in tuple(getattr(classified, "unresolved", ()) or ())
                )
                if tuple(getattr(classified, "unresolved", ()) or ()):
                    continue
                occurrences = tuple(
                    getattr(classified, "occurrences", ()) or ()
                )

            for occurrence in occurrences:
                if float(occurrence.damage_value) <= 0.0:
                    continue
                events.append(
                    RuntimeEvent(
                        time_seconds=float(occurrence.time_seconds),
                        sequence=int(occurrence.sequence),
                        trigger=WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
                        source=str(occurrence.source_name),
                        target=(
                            str(target_identity).strip()
                            if str(target_identity or "").strip()
                            else action.target_key
                        ),
                    )
                )

        ordered = tuple(
            sorted(
                events,
                key=lambda row: (
                    row.time_seconds,
                    row.sequence,
                    row.source.casefold(),
                ),
            )
        )
        deduped = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSWeaponEnchantmentActivationEventResult(
            events=ordered,
            evidence=(
                f"Weapon-enchantment eligible scheduled actions: {eligible_actions}",
                f"Weapon-enchantment activation opportunities materialized: {len(ordered)}",
                "Activation opportunity requires a positive exact-time damage occurrence",
                "Light/Heavy attacks are eligible directly; skills and Ultimates require canonical weapon-line ownership plus occurrence-level enchant eligibility classification",
                "Single-target Damage over Time weapon-ability occurrences are never inferred eligible from damage occurrence alone",
                "Opportunity evidence does not assert cooldown availability, source selection, poison replacement, or an actual enchantment proc",
            ),
            unresolved=deduped,
        )


__all__ = [
    "WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER",
    "ExtremeSustainedDPSWeaponEnchantmentEligibleOccurrences",
    "ExtremeSustainedDPSWeaponEnchantmentActivationEventResult",
    "ExtremeSustainedDPSWeaponEnchantmentActivationEventService",
]
