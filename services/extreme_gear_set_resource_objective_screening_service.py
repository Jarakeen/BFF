from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in max-resource objectives.

Extreme gear relevance should fail closed when an unmapped bonus could modify the
requested maximum resource or alter the legal equipment search itself.  It should
not, however, require the entire ESO gear proc corpus to be mechanic-mapped before
we can prove that an unrelated damage/healing proc contributes zero to Max Health,
Max Magicka, or Max Stamina.

This service owns no stat math.  It only decides whether an *unmapped* bonus is
safe to prune for one reviewed max-resource objective.  Screening is deliberately
conservative but observes one important mechanics rule: scaling *from* a maximum
resource is not the same thing as modifying that resource.

* direct increase/decrease/reduction language for the target maximum resource
  remains a blocker;
* scaling, restore, comparison, or target-Max-Health reference language alone does
  not make a bonus relevant to the resource maximum;
* reviewed global equipment-state mechanics remain blockers even when they do not
  name the target resource directly;
* Max Health also treats Toughness references as potential resource modifiers;
* only bonuses with none of those hazards are proven irrelevant.
"""

from dataclasses import dataclass
import re

from minmax.eso_markup import normalize_eso_markup


_RESOURCE_WORD_BY_OBJECTIVE = {
    "max_health": "health",
    "max_magicka": "magicka",
    "max_stamina": "stamina",
}

_GLOBAL_EQUIPMENT_HAZARDS = (
    "disable all other item set bonuses",
    "unable to swap between your primary and backup weapon sets",
    "two mundus stone boons",
)

_DIRECT_CHANGE_VERB = re.compile(
    r"\b(?:increase(?:s|d|ing)?|reduce(?:s|d|ing)?|decrease(?:s|d|ing)?|adds?)\b",
    re.IGNORECASE,
)
_MAXIMUM_WORD = re.compile(r"\bmax(?:imum)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class ExtremeGearSetResourceObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    target_resource_mentioned: bool = False
    global_equipment_hazards: tuple[str, ...] = ()
    named_resource_hazards: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[str, ...]:
        rows: list[str] = []
        if self.target_resource_mentioned:
            rows.append("target maximum resource is directly modified")
        rows.extend(self.global_equipment_hazards)
        rows.extend(self.named_resource_hazards)
        return tuple(rows)


class ExtremeGearSetResourceObjectiveScreeningService:
    """Conservatively prove an unmapped bonus irrelevant to one max resource."""

    @staticmethod
    def _normalized(description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text
        return " ".join(text.casefold().split())

    @classmethod
    def _directly_modifies_target_resource(
        cls,
        text: str,
        resource_word: str,
    ) -> bool:
        if not text:
            return False

        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
            if resource_word not in sentence:
                continue
            if not _MAXIMUM_WORD.search(sentence):
                continue

            # Direct mutation uses a change verb in the same sentence as the
            # maximum-resource reference.  This catches list wording such as
            # "increase your Maximum Health, Stamina, and Magicka by 1707" and
            # inverse wording such as "your Max Magicka is increased by 3132".
            # Pure scaling/reference wording has no such change verb and is safe
            # to prune for a maximum-resource objective.
            if _DIRECT_CHANGE_VERB.search(sentence):
                return True

        return False

    @classmethod
    def review(
        cls,
        description: str,
        objective_key: str,
    ) -> ExtremeGearSetResourceObjectiveScreeningResult:
        key = str(objective_key or "").strip().casefold()
        resource_word = _RESOURCE_WORD_BY_OBJECTIVE.get(key)
        if resource_word is None:
            raise KeyError(f"unreviewed Extreme gear resource screening objective: {objective_key!r}")

        text = cls._normalized(description)
        target_resource_mentioned = cls._directly_modifies_target_resource(
            text,
            resource_word,
        )

        global_hazards = tuple(
            phrase
            for phrase in _GLOBAL_EQUIPMENT_HAZARDS
            if phrase in text
        )

        named_hazards: list[str] = []
        if key == "max_health" and "toughness" in text:
            named_hazards.append("Toughness resource modifier reference")

        proven_irrelevant = not (
            target_resource_mentioned
            or global_hazards
            or named_hazards
        )
        return ExtremeGearSetResourceObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=proven_irrelevant,
            target_resource_mentioned=target_resource_mentioned,
            global_equipment_hazards=global_hazards,
            named_resource_hazards=tuple(named_hazards),
        )


__all__ = [
    "ExtremeGearSetResourceObjectiveScreeningResult",
    "ExtremeGearSetResourceObjectiveScreeningService",
]
