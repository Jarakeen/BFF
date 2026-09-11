from __future__ import annotations

"""Project canonical passive-skill tooltips into reviewed Extreme objective units.

Every player passive belongs in the Extreme coverage universe.  This service
projects only simple unconditional max-rank stat clauses whose units can be
mapped losslessly. Conditional, slot-dependent, equipment-dependent, runtime,
and otherwise unresolved passives remain explicit results rather than being
silently scored as zero.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.gear_stat_inputs import GearStatInputResolver
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
)


class ExtremePassiveProjectionStatus(str, Enum):
    REVIEWED_STATIC = "reviewed_static"
    CONTEXT_REQUIRED = "context_required"
    KNOWN_NONCOMBAT = "known_noncombat"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ExtremePassiveContribution:
    objective_key: str
    flat: float = 0.0
    ratio: float = 0.0
    percent_of_reference: float = 0.0
    source: str = ""

    def projected_delta(self, reference_value: float | None = None) -> float | None:
        if self.percent_of_reference and reference_value is None:
            return None
        return (
            float(self.flat)
            + float(self.ratio)
            + float(reference_value or 0.0) * float(self.percent_of_reference)
        )


@dataclass(frozen=True)
class ExtremePassiveProjection:
    passive: ExtremePlayerSkillRecord
    status: ExtremePassiveProjectionStatus
    contributions: tuple[ExtremePassiveContribution, ...] = ()
    conditions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_NUMBER = r"([0-9]+(?:\.[0-9]+)?)"
_PERCENT = rf"{_NUMBER}\s*%"
_CONDITION_PREFIXES = (
    "while ",
    "when ",
    "whenever ",
    "after ",
    "if ",
    "upon ",
    "for each ",
    "per ",
    "with a ",
    "with an ",
    "against ",
    "during ",
)
_CONDITION_PHRASES = (
    " is slotted",
    " are slotted",
    " slotted on",
    " equipped",
    " have a ",
    " has a ",
    " below ",
    " above ",
    " within ",
    " after you ",
    " when you ",
    " whenever you ",
    " while you ",
    " while wearing ",
    " for every ",
    " for each ",
)

# These passives already have reviewed purpose-built formulas. Their actual
# contribution depends on bars, armor composition, or another dynamic input and
# therefore must not be duplicated as a static tooltip score here.
_CONTEXTUAL_KNOWN_PASSIVES = frozenset(
    {
        "advanced species",
        "flourish",
        "frozen armor",
        "pressure points",
        "expert mage",
        "magicka controller",
        "slayer",
        "magicka aid",
        "evocation",
        "concentration",
        "spell warding",
        "prodigy",
        "wind walker",
        "agility",
        "dexterity",
        "constitution",
        "undaunted mettle",
        # Crafting passives can alter combat consumable duration/effects and
        # therefore remain context-bearing rather than being discarded.
        "medicinal use",
        "snakeblood",
        "gourmand",
        "connoisseur",
    }
)

_CONSUMABLE_CONTEXT_TERMS = (
    "potion",
    "poison",
    "food",
    "drink",
    "beverage",
    "meal",
    "consumable",
)


class ExtremePassiveProjectionService:
    REVIEWED_OBJECTIVES = (
        "max_health",
        "max_magicka",
        "max_stamina",
        "critical_damage",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
    )

    @staticmethod
    def _clean(text: object) -> str:
        value = _COLOR.sub("", str(text or ""))
        return " ".join(value.split())

    @classmethod
    def _clauses(cls, description: str) -> tuple[str, ...]:
        clean = cls._clean(description)
        if not clean:
            return ()
        return tuple(
            clause.strip(" .;:")
            for clause in re.split(r"(?<=[.!?;])\s+|\n+", clean)
            if clause.strip(" .;:")
        )

    @staticmethod
    def _conditional_clause(clause: str) -> bool:
        lowered = f" {clause.casefold()} "
        stripped = clause.casefold().lstrip()
        return any(stripped.startswith(prefix) for prefix in _CONDITION_PREFIXES) or any(
            phrase in lowered for phrase in _CONDITION_PHRASES
        )

    @staticmethod
    def _source(passive: ExtremePlayerSkillRecord, clause: str) -> str:
        return f"{passive.name} [{passive.skill_line}]: {clause}"

    @classmethod
    def _static_clause_contributions(
        cls,
        passive: ExtremePlayerSkillRecord,
        clause: str,
    ) -> tuple[ExtremePassiveContribution, ...]:
        if cls._conditional_clause(clause):
            return ()

        source = cls._source(passive, clause)
        rows: list[ExtremePassiveContribution] = []

        def flat(pattern: str, objectives: tuple[str, ...]) -> bool:
            match = re.search(pattern, clause, flags=re.IGNORECASE)
            if not match:
                return False
            value = float(match.group(1))
            rows.extend(
                ExtremePassiveContribution(objective, flat=value, source=source)
                for objective in objectives
            )
            return True

        def percent_reference(pattern: str, objectives: tuple[str, ...]) -> bool:
            match = re.search(pattern, clause, flags=re.IGNORECASE)
            if not match:
                return False
            value = float(match.group(1)) / 100.0
            rows.extend(
                ExtremePassiveContribution(
                    objective,
                    percent_of_reference=value,
                    source=source,
                )
                for objective in objectives
            )
            return True

        crit_damage = re.search(
            rf"Increases your Critical Damage(?: and Critical Healing)? by {_PERCENT}",
            clause,
            flags=re.IGNORECASE,
        )
        if crit_damage:
            rows.append(
                ExtremePassiveContribution(
                    "critical_damage",
                    ratio=float(crit_damage.group(1)) / 100.0,
                    source=source,
                )
            )

        if "%" not in clause:
            flat(rf"Increases your Max Health by {_NUMBER}", ("max_health",))
            flat(rf"Increases your Max Magicka by {_NUMBER}", ("max_magicka",))
            flat(rf"Increases your Max Stamina by {_NUMBER}", ("max_stamina",))
            flat(
                rf"Increases your Max Health,? Magicka,? and Stamina by {_NUMBER}",
                ("max_health", "max_magicka", "max_stamina"),
            )
            flat(
                rf"Increases your (?:Weapon and Spell|Spell and Weapon) Damage by {_NUMBER}",
                ("weapon_damage", "spell_damage"),
            )
            flat(rf"Increases your Weapon Damage by {_NUMBER}", ("weapon_damage",))
            flat(rf"Increases your Spell Damage by {_NUMBER}", ("spell_damage",))
            flat(
                rf"Increases your (?:Physical and Spell|Spell and Physical) Resistance by {_NUMBER}",
                ("physical_resistance", "spell_resistance"),
            )
            flat(rf"Increases your Physical Resistance by {_NUMBER}", ("physical_resistance",))
            flat(rf"Increases your Spell Resistance by {_NUMBER}", ("spell_resistance",))
            flat(rf"Increases your Magicka Recovery by {_NUMBER}", ("magicka_recovery",))
            flat(rf"Increases your Stamina Recovery by {_NUMBER}", ("stamina_recovery",))

        percent_reference(rf"Increases your Max Health by {_PERCENT}", ("max_health",))
        percent_reference(rf"Increases your Max Magicka by {_PERCENT}", ("max_magicka",))
        percent_reference(rf"Increases your Max Stamina by {_PERCENT}", ("max_stamina",))
        percent_reference(
            rf"Increases your Max Health,? Magicka,? and Stamina by {_PERCENT}",
            ("max_health", "max_magicka", "max_stamina"),
        )
        percent_reference(
            rf"Increases your (?:Weapon and Spell|Spell and Weapon) Damage by {_PERCENT}",
            ("weapon_damage", "spell_damage"),
        )
        percent_reference(rf"Increases your Weapon Damage by {_PERCENT}", ("weapon_damage",))
        percent_reference(rf"Increases your Spell Damage by {_PERCENT}", ("spell_damage",))
        percent_reference(rf"Increases your Magicka Recovery by {_PERCENT}", ("magicka_recovery",))
        percent_reference(rf"Increases your Stamina Recovery by {_PERCENT}", ("stamina_recovery",))

        critical_rating_patterns = (
            rf"Increases your (?:Weapon and Spell|Spell and Weapon) Critical(?: Chance| Rating)? by {_NUMBER}",
            rf"Increases your Critical Chance(?: Rating)? by {_NUMBER}",
        )
        if "%" not in clause:
            for pattern in critical_rating_patterns:
                match = re.search(pattern, clause, flags=re.IGNORECASE)
                if match:
                    ratio = GearStatInputResolver.critical_rating_to_ratio(float(match.group(1)))
                    rows.extend(
                        (
                            ExtremePassiveContribution("weapon_critical", ratio=ratio, source=source),
                            ExtremePassiveContribution("spell_critical", ratio=ratio, source=source),
                        )
                    )
                    break

            match = re.search(
                rf"Increases your Weapon Critical(?: Chance| Rating)? by {_NUMBER}",
                clause,
                flags=re.IGNORECASE,
            )
            if match:
                rows.append(
                    ExtremePassiveContribution(
                        "weapon_critical",
                        ratio=GearStatInputResolver.critical_rating_to_ratio(float(match.group(1))),
                        source=source,
                    )
                )
            match = re.search(
                rf"Increases your Spell Critical(?: Chance| Rating)? by {_NUMBER}",
                clause,
                flags=re.IGNORECASE,
            )
            if match:
                rows.append(
                    ExtremePassiveContribution(
                        "spell_critical",
                        ratio=GearStatInputResolver.critical_rating_to_ratio(float(match.group(1))),
                        source=source,
                    )
                )

        return tuple(dict.fromkeys(rows))

    @classmethod
    def project(cls, passive: ExtremePlayerSkillRecord) -> ExtremePassiveProjection:
        if not passive.is_passive:
            raise ValueError(f"not a passive skill: {passive.name}")

        name_key = cls._clean(passive.name).casefold()
        clauses = cls._clauses(passive.description)
        conditions = tuple(clause for clause in clauses if cls._conditional_clause(clause))

        contributions: list[ExtremePassiveContribution] = []
        for clause in clauses:
            contributions.extend(cls._static_clause_contributions(passive, clause))

        projected = tuple(dict.fromkeys(contributions))
        if projected:
            return ExtremePassiveProjection(
                passive=passive,
                status=ExtremePassiveProjectionStatus.REVIEWED_STATIC,
                contributions=projected,
                conditions=conditions,
            )

        description_key = cls._clean(passive.description).casefold()
        consumable_context = any(term in description_key for term in _CONSUMABLE_CONTEXT_TERMS)
        if name_key in _CONTEXTUAL_KNOWN_PASSIVES or conditions or consumable_context:
            reason = (
                f"Reviewed contextual passive requires build/runtime inputs: {passive.name}"
                if name_key in _CONTEXTUAL_KNOWN_PASSIVES
                else f"Conditional passive requires build/runtime interpretation: {passive.name}"
            )
            return ExtremePassiveProjection(
                passive=passive,
                status=ExtremePassiveProjectionStatus.CONTEXT_REQUIRED,
                conditions=conditions,
                unresolved=(reason,),
            )

        if not passive.description:
            reason = f"Canonical max-rank passive description unavailable: {passive.name}"
        else:
            reason = f"Passive tooltip is not yet losslessly mapped to Extreme objectives: {passive.name}"
        return ExtremePassiveProjection(
            passive=passive,
            status=ExtremePassiveProjectionStatus.UNRESOLVED,
            unresolved=(reason,),
        )

    @classmethod
    def project_all(
        cls,
        passives: tuple[ExtremePlayerSkillRecord, ...],
    ) -> tuple[ExtremePassiveProjection, ...]:
        return tuple(cls.project(passive) for passive in passives)
