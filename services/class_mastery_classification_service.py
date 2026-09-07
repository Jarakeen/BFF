from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.class_mastery_repository import ClassMasteryPassive


class ClassMasteryBoundary(str, Enum):
    """How much runtime state is required before a mastery can contribute."""

    STANDING_SELF_CONTAINED = "standing_self_contained"
    SELF_ACHIEVABLE_CONDITIONAL = "self_achievable_conditional"
    COMBAT_STATE_DEPENDENT = "combat_state_dependent"
    TARGET_STATE_DEPENDENT = "target_state_dependent"
    GROUP_ONLY_OR_NON_SELF = "group_only_or_non_self"
    NON_SHEET_OR_OTHER = "non_sheet_or_other"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ClassMasteryClassification:
    passive: ClassMasteryPassive
    boundary: ClassMasteryBoundary
    objective_keys: tuple[str, ...]
    reason: str


_OBJECTIVE_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("weapon and spell damage", ("weapon_damage", "spell_damage")),
    ("weapon damage", ("weapon_damage",)),
    ("spell damage", ("spell_damage",)),
    ("critical chance", ("weapon_critical", "spell_critical")),
    ("critical damage", ("critical_damage",)),
    ("maximum health", ("max_health",)),
    ("max health", ("max_health",)),
    ("maximum magicka", ("max_magicka",)),
    ("max magicka", ("max_magicka",)),
    ("maximum stamina", ("max_stamina",)),
    ("max stamina", ("max_stamina",)),
    ("health recovery", ("health_recovery",)),
    ("magicka recovery", ("magicka_recovery",)),
    ("stamina recovery", ("stamina_recovery",)),
    ("physical resistance", ("physical_resistance",)),
    ("spell resistance", ("spell_resistance",)),
)

# These markers are intentionally conservative. They classify the *boundary*
# needed to reason about a canonical tooltip; they do not parse a numeric effect
# or grant stats. Actual scoring remains a separate reviewed mapping.
_TARGET_MARKERS = (
    "your target",
    "the target",
    "target's",
    "an enemy",
    "enemies",
    "enemy ",
    "status effect on",
)
_COMBAT_MARKERS = (
    "while in combat",
    "when you deal",
    "when you take",
    "when you heal",
    "when you cast",
    "casting ",
    "activating ",
    "when you activate",
    "while bracing",
    "applying ",
    "when rank ",
    "when your ",
)
_SELF_CONDITIONAL_MARKERS = (
    "based on your",
    "while you are",
    "for each",
    "up to",
    "at full",
    "missing health",
)


class ClassMasteryClassificationService:
    """Classify canonical Class Mastery rows before any stat scoring occurs.

    The service is deliberately non-numeric. It identifies which Extreme Build
    objective a tooltip explicitly names and how much runtime state would be
    required to realize that effect. Anything not supported by explicit wording
    stays unresolved/non-sheet instead of being promoted into optimistic math.
    """

    @staticmethod
    def objective_keys(description: str) -> tuple[str, ...]:
        text = str(description or "").casefold()
        found: list[str] = []
        for phrase, keys in _OBJECTIVE_PHRASES:
            if phrase not in text:
                continue
            for key in keys:
                if key not in found:
                    found.append(key)
        return tuple(found)

    @classmethod
    def classify(cls, passive: ClassMasteryPassive) -> ClassMasteryClassification:
        text = str(passive.description or "").strip()
        normalized = text.casefold()
        objectives = cls.objective_keys(text)

        if not text:
            return ClassMasteryClassification(
                passive,
                ClassMasteryBoundary.UNRESOLVED,
                objectives,
                "Canonical Class Mastery row has no description to classify.",
            )

        # If the tooltip explicitly says the effect is for group members and does
        # not also grant it to the player, it cannot raise a self-sheet extreme.
        mentions_group = "group member" in normalized or "group members" in normalized
        mentions_self = any(
            marker in normalized
            for marker in ("you and", "you gain", "your ", "yourself", "grants you", "to you")
        )
        if mentions_group and not mentions_self:
            return ClassMasteryClassification(
                passive,
                ClassMasteryBoundary.GROUP_ONLY_OR_NON_SELF,
                objectives,
                "Tooltip names group recipients but no self recipient.",
            )

        if any(marker in normalized for marker in _TARGET_MARKERS):
            boundary = ClassMasteryBoundary.TARGET_STATE_DEPENDENT
            reason = "Tooltip requires an enemy/target state before the effect can exist."
        elif any(marker in normalized for marker in _COMBAT_MARKERS):
            boundary = ClassMasteryBoundary.COMBAT_STATE_DEPENDENT
            reason = "Tooltip requires a combat action/state rather than existing continuously."
        elif any(marker in normalized for marker in _SELF_CONDITIONAL_MARKERS):
            boundary = ClassMasteryBoundary.SELF_ACHIEVABLE_CONDITIONAL
            reason = "Tooltip names a self-achievable condition or scaling state."
        elif objectives:
            boundary = ClassMasteryBoundary.STANDING_SELF_CONTAINED
            reason = "Tooltip names a supported sheet objective without an explicit combat/target trigger."
        else:
            boundary = ClassMasteryBoundary.NON_SHEET_OR_OTHER
            reason = "Tooltip does not explicitly name a currently supported Extreme Build sheet objective."

        return ClassMasteryClassification(passive, boundary, objectives, reason)

    @classmethod
    def classify_all(
        cls,
        passives: tuple[ClassMasteryPassive, ...],
    ) -> tuple[ClassMasteryClassification, ...]:
        return tuple(cls.classify(passive) for passive in passives)

    @classmethod
    def relevant_to_objective(
        cls,
        passives: tuple[ClassMasteryPassive, ...],
        objective_key: str,
    ) -> tuple[ClassMasteryClassification, ...]:
        target = str(objective_key or "").strip()
        if not target:
            return ()
        return tuple(
            row
            for row in cls.classify_all(passives)
            if target in row.objective_keys
        )
