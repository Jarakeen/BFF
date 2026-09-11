from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in max-resource objectives.

Extreme gear relevance should fail closed when an unmapped bonus could modify the
requested maximum resource or alter the legal equipment search itself.  It should
not, however, require the entire ESO gear proc corpus to be mechanic-mapped before
we can prove that an unrelated damage/healing proc contributes zero to Max Health,
Max Magicka, or Max Stamina.

This service owns no stat math.  It only decides whether an *unmapped* bonus is
safe to prune for one reviewed max-resource objective.  Screening is deliberately
conservative but observes two important mechanics/language rules:

* scaling *from* a maximum resource is not the same thing as modifying it;
* the ordinary English word ``maximum`` in phrases such as ``up to a maximum`` or
  ``reaching the maximum at 50% Magicka`` is not a ``Maximum Magicka`` stat
  reference.

Direct resource mutation and reviewed equipment-state mechanics remain blockers.
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

_CHANGE_VERB = r"(?:increase(?:s|d|ing)?|reduce(?:s|d|ing)?|decrease(?:s|d|ing)?|adds?)"
_EXPLICIT_MAX_RESOURCE = r"max(?:imum)?\s+{resource}"


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

        explicit_resource = _EXPLICIT_MAX_RESOURCE.format(resource=re.escape(resource_word))
        direct_before = re.compile(
            rf"\b{_CHANGE_VERB}\b(?P<body>[^.;]{{0,80}}?)\b{explicit_resource}\b",
            re.IGNORECASE,
        )
        inverse = re.compile(
            rf"\b(?:your\s+)?{explicit_resource}\b[^.;]{{0,24}}?\b(?:is\s+)?"
            rf"{_CHANGE_VERB}\b",
            re.IGNORECASE,
        )

        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
            # Direct forms: "increase your Max Magicka" / "reduces Maximum Health".
            match = direct_before.search(sentence)
            if match is not None:
                between = match.group("body")
                if "scal" not in between and "based on" not in between:
                    return True

            # Inverse forms: "your Max Magicka is increased by ...".
            if inverse.search(sentence):
                return True

            # ESO also writes shared-list mutations such as:
            #   "increase your Maximum Health, Stamina, and Magicka by 1707"
            # Only treat the list as a stat mutation when Maximum starts the
            # resource list and a direct change verb governs that list.
            list_match = re.search(
                rf"\b{_CHANGE_VERB}\b[^.;]{{0,40}}?\bmaximum\s+"
                rf"(?P<resources>[^.;]{{0,70}}?)\s+by\s+[-+]?\d",
                sentence,
                re.IGNORECASE,
            )
            if list_match is not None:
                resources = list_match.group("resources")
                if re.search(rf"\b{re.escape(resource_word)}\b", resources):
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
