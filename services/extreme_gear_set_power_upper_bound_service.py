from __future__ import annotations

"""Conservative numeric ceilings for unmapped sheet-power gear descriptions.

This service does not claim that a conditional bonus is executable. It extracts
only proof-safe upper bounds from canonical U50 tooltip evidence so an Extreme
search can discard candidates that cannot win without treating an unresolved
proc as zero. Formulas whose multiplier is not finitely stated remain explicit.
"""

from dataclasses import dataclass
import re

from minmax.combat_effect_semantics import GameUpdate
from minmax.eso_markup import normalize_eso_markup
from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
from services.extreme_gear_set_power_objective_screening_service import (
    ExtremeGearSetPowerObjectiveScreeningService,
)


_TARGET_STAT = {
    "weapon_damage": StatId.WEAPON_DAMAGE,
    "spell_damage": StatId.SPELL_DAMAGE,
}
_TARGET_PHRASE = {
    "weapon_damage": r"(?:weapon(?:\s+(?:and|or)\s+spell)?|spell\s+and\s+weapon)\s+damage",
    "spell_damage": r"(?:spell(?:\s+(?:and|or)\s+weapon)?|weapon\s+and\s+spell)\s+damage",
}
_BUFFS = (
    "Minor Brutality",
    "Major Brutality",
    "Minor Sorcery",
    "Major Sorcery",
    "Minor Courage",
    "Major Courage",
)
_MAX_ACTIVE_EQUIPMENT_UNITS = 12


@dataclass(frozen=True)
class ExtremeGearSetPowerUpperBound:
    objective_key: str
    flat_upper_bound: float
    percent_upper_bound: float
    named_buffs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return not self.unresolved


class ExtremeGearSetPowerUpperBoundService:
    """Extract an intentionally favorable ceiling from one unmapped bonus."""

    @staticmethod
    def _normalized(description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text
        return " ".join(text.casefold().split())

    @staticmethod
    def _maximum(token: str) -> float:
        values = [float(value.replace(",", "")) for value in re.findall(r"\d[\d,]*(?:\.\d+)?", token)]
        return max(values, default=0.0)

    @classmethod
    def _direct_values(
        cls,
        text: str,
        objective_key: str,
    ) -> tuple[tuple[float, bool], ...]:
        target = _TARGET_PHRASE[objective_key]
        number = r"\d[\d,]*(?:\.\d+)?(?:\s*-\s*\d[\d,]*(?:\.\d+)?)?"
        patterns = (
            re.compile(
                rf"(?P<amount>{number})(?P<percent>\s*%)?\s+{target}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{target}[^.;]{{0,45}}?\b(?:by|of)\s+(?:up\s+to\s+)?"
                rf"(?P<amount>{number})(?P<percent>\s*%)?",
                re.IGNORECASE,
            ),
        )
        values: list[tuple[float, bool]] = []
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = cls._maximum(match.group("amount"))
                if value > 0.0:
                    values.append((value, bool(match.group("percent"))))
        return tuple(values)

    @staticmethod
    def _stack_multiplier(text: str) -> tuple[float, str | None]:
        if re.search(r"\b(?:each stack|per stack)\b", text):
            counts = [int(value) for value in re.findall(r"\b(?:up to|at)\s+(\d+)\s+stacks?\b", text)]
            if counts:
                value = max(counts)
                return float(value), f"assumed all {value} stated stacks active"
        if re.search(r"\bfor each enemy\b", text):
            counts = [int(value) for value in re.findall(r"\bup to\s+(\d+)\s+enemies\b", text)]
            if counts:
                value = max(counts)
                return float(value), f"assumed the stated {value}-enemy ceiling"
        if re.search(r"\beach \w+ active grants\b", text):
            counts = [int(value) for value in re.findall(r"\bup to\s+(\d+)\s+total\b", text)]
            if counts:
                value = max(counts)
                return float(value), f"assumed all {value} stated sources active"
        if re.search(r"\bfor every set\b", text):
            return (
                float(_MAX_ACTIVE_EQUIPMENT_UNITS),
                "over-counted one qualifying set per active equipment unit",
            )
        return 1.0, None

    @classmethod
    def build(
        cls,
        description: str,
        objective_key: str,
    ) -> ExtremeGearSetPowerUpperBound:
        key = str(objective_key or "").strip().casefold()
        target_stat = _TARGET_STAT.get(key)
        if target_stat is None:
            raise KeyError(f"unreviewed Extreme power upper-bound objective: {objective_key!r}")

        text = cls._normalized(description)
        screening = ExtremeGearSetPowerObjectiveScreeningService.review(text, key)
        if screening.proven_irrelevant:
            return ExtremeGearSetPowerUpperBound(key, 0.0, 0.0)

        named_flat = 0.0
        named_percent = 0.0
        named_buffs: list[str] = []
        assumptions: list[str] = []
        unresolved: list[str] = []

        for name in _BUFFS:
            if name.casefold() not in text:
                continue
            rows = tuple(
                effect
                for effect in effects_for_buff(name, game_update=GameUpdate.U50)
                if effect.stat is target_stat
            )
            if not rows:
                continue
            named_buffs.append(name)
            for effect in rows:
                if effect.bucket == "flat":
                    named_flat += float(effect.value)
                elif effect.bucket == "percent":
                    named_percent += float(effect.value)
                else:
                    unresolved.append(f"{name}: unsupported power bucket {effect.bucket!r}")

        direct_values = cls._direct_values(text, key)
        direct_flat = 0.0
        direct_percent = 0.0
        if direct_values:
            multiplier, assumption = cls._stack_multiplier(text)
            # Sum every syntactically relevant amount. Duplicate/current-value
            # wording may over-count, which is safe for a dominance ceiling;
            # taking only the largest amount could under-count two independent
            # power grants in one unresolved bonus.
            direct_flat = sum(value for value, is_percent in direct_values if not is_percent) * multiplier
            direct_percent = (
                sum(value for value, is_percent in direct_values if is_percent)
                * multiplier
                / 100.0
            )
            if assumption:
                assumptions.append(assumption)

        # Independent direct grants and named buffs may coexist. Summing them is
        # conservative even when the tooltip makes them mutually exclusive.
        flat = named_flat + direct_flat
        percent = named_percent + direct_percent

        if "equal to the amount of total ultimate consumed" in text:
            unresolved.append("Ultimate-consumed power formula requires a canonical Ultimate ceiling")
        if "for each minor buff" in text:
            unresolved.append("per-Minor-Buff power formula requires a finite named-buff denominator")
        if "effectiveness of your weapon traits" in text:
            unresolved.append("weapon-trait amplification must be compared on each weapon realization")
        if "two mundus stone boons" in text:
            unresolved.append("second-Mundus power requires the canonical distinct-boon frontier")

        if screening.power_hazards and flat <= 0.0 and percent <= 0.0 and not unresolved:
            unresolved.append("direct power mutation has no finite reviewed numeric ceiling")

        return ExtremeGearSetPowerUpperBound(
            objective_key=key,
            flat_upper_bound=float(flat),
            percent_upper_bound=float(percent),
            named_buffs=tuple(dict.fromkeys(named_buffs)),
            assumptions=tuple(dict.fromkeys(assumptions)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeGearSetPowerUpperBound",
    "ExtremeGearSetPowerUpperBoundService",
]
