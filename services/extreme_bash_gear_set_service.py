from __future__ import annotations

"""Project gear-set Bash and resistance channels for MOST Bashy.

Bash damage scales from the higher of Physical or Spell Resistance, so a set
candidate cannot be ranked only by text that explicitly mentions Bash. This
adapter keeps the two relevant set-owned channels together:

* flat extra Bash damage; and
* static Physical/Spell Resistance supplied by active set bonuses.

The shared GearSetEffectResolver remains authoritative for ordinary static
stats. Bash-specific tooltip wording is intentionally parsed here because the
formula destination is ``Set.ExtraBashDamage``, not a normal character-sheet
stat. Unmapped active bonuses remain blockers rather than assumed zeroes.
"""

from dataclasses import dataclass, replace
import re

from minmax.eso_markup import normalize_eso_markup
from minmax.formulas.final_calculations import calculate_bash_damage
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.gear_sets import GearSet, GearSetBonus
from minmax.stat_ids import StatId

from .extreme_bash_objective_service import (
    ExtremeBashDamageInputs,
    ExtremeBashLegalityContext,
    ExtremeBashObjectiveResult,
    ExtremeBashObjectiveService,
)


@dataclass(frozen=True)
class ExtremeBashGearSetCandidate:
    set_id: int
    set_name: str
    category: str | None
    equipped_piece_count: int
    extra_bash_damage: float
    physical_resistance: float
    spell_resistance: float
    source_bonuses: tuple[GearSetBonus, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved

    @property
    def max_resistance_delta(self) -> float:
        return max(self.physical_resistance, self.spell_resistance)


@dataclass(frozen=True)
class ExtremeBashGearSetEvaluation:
    candidate: ExtremeBashGearSetCandidate
    objective: ExtremeBashObjectiveResult


class ExtremeBashGearSetService:
    """Resolve and rank one set's coupled Bash/resistance contribution."""

    _PREFIX = re.compile(r"^\(\d+\s+(?:perfected\s+)?items?\)\s*", re.IGNORECASE)
    _NUMBER = r"(?P<value>\d+(?:\.\d+)?)"
    _RANGE = r"(?P<min>\d+(?:\.\d+)?)\s*-\s*(?P<max>\d+(?:\.\d+)?)"

    @staticmethod
    def _maximum_useful_piece_count(repository: GearSetRepository, gear_set: GearSet) -> int:
        bonuses = repository.get_bonuses(gear_set.id)
        highest_bonus = max((bonus.piece_count for bonus in bonuses), default=0)
        configured = int(gear_set.max_equip_count or 0)
        if configured > 0 and highest_bonus > 0:
            return min(configured, highest_bonus)
        return configured or highest_bonus

    @classmethod
    def _clean(cls, description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text.strip()
        return cls._PREFIX.sub("", text).strip()

    @classmethod
    def _bash_damage_value(cls, text: str, *, use_max_value: bool) -> float | None:
        patterns = (
            rf"Increases your Bash damage by {cls._RANGE}\.?",
            rf"Adds {cls._RANGE} Bash Damage\.?",
        )
        for pattern in patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                key = "max" if use_max_value else "min"
                return float(match.group(key))

        patterns = (
            rf"Increases your Bash damage by {cls._NUMBER}\.?",
            rf"Adds {cls._NUMBER} Bash Damage\.?",
            rf"Your Bash attacks deal {cls._NUMBER} more damage\.?",
            rf"Your Bash attacks deal {cls._NUMBER} additional damage\.?",
        )
        for pattern in patterns:
            match = re.fullmatch(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group("value"))
        return None

    @classmethod
    def candidate_for_set(
        cls,
        repository: GearSetRepository,
        set_name: str,
        *,
        equipped_piece_count: int | None = None,
        use_max_value: bool = True,
        resolver: GearSetEffectResolver | None = None,
    ) -> ExtremeBashGearSetCandidate:
        gear_set = repository.get_set(set_name)
        if gear_set is None:
            raise KeyError(f"gear set not found: {set_name!r}")

        piece_count = (
            cls._maximum_useful_piece_count(repository, gear_set)
            if equipped_piece_count is None
            else int(equipped_piece_count)
        )
        if piece_count < 0:
            raise ValueError("equipped gear-set piece count must be non-negative")
        if gear_set.max_equip_count and piece_count > int(gear_set.max_equip_count):
            raise ValueError(
                f"{gear_set.name}: equipped piece count {piece_count} exceeds canonical max "
                f"{gear_set.max_equip_count}"
            )

        active = tuple(
            bonus for bonus in repository.get_bonuses(gear_set.id)
            if bonus.piece_count <= piece_count
        )
        effect_resolver = resolver or GearSetEffectResolver()
        bash = 0.0
        physical = 0.0
        spell = 0.0
        unresolved: list[str] = []

        for bonus in active:
            source = f"{gear_set.name} ({bonus.piece_count})"
            text = cls._clean(bonus.description)
            effects = tuple(
                effect_resolver.resolve(
                    bonus,
                    use_max_value=use_max_value,
                    source=source,
                )
            )
            if effects:
                for effect in effects:
                    if effect.condition:
                        if effect.stat in {StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE}:
                            unresolved.append(
                                f"{source}: resistance contribution requires condition {effect.condition}"
                            )
                        continue
                    if effect.stat is StatId.PHYSICAL_RESISTANCE:
                        physical += float(effect.value)
                    elif effect.stat is StatId.SPELL_RESISTANCE:
                        spell += float(effect.value)
                continue

            bash_value = cls._bash_damage_value(text, use_max_value=use_max_value)
            if bash_value is not None:
                bash += bash_value
                continue

            if text:
                unresolved.append(
                    f"{source}: active set bonus is not yet Bash-mechanic-mapped: {text}"
                )

        return ExtremeBashGearSetCandidate(
            set_id=gear_set.id,
            set_name=gear_set.name,
            category=gear_set.category,
            equipped_piece_count=piece_count,
            extra_bash_damage=bash,
            physical_resistance=physical,
            spell_resistance=spell,
            source_bonuses=active,
            unresolved=tuple(unresolved),
        )

    @classmethod
    def evaluate_candidate(
        cls,
        candidate: ExtremeBashGearSetCandidate,
        base_inputs: ExtremeBashDamageInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
    ) -> ExtremeBashGearSetEvaluation:
        physical = None if base_inputs.physical_resist is None else (
            float(base_inputs.physical_resist) + candidate.physical_resistance
        )
        spell = None if base_inputs.spell_resist is None else (
            float(base_inputs.spell_resist) + candidate.spell_resistance
        )
        existing_set_bash = base_inputs.set_extra_bash_damage
        set_bash = None if existing_set_bash is None else (
            float(existing_set_bash) + candidate.extra_bash_damage
        )

        objective = ExtremeBashObjectiveService.evaluate_damage(
            replace(
                base_inputs,
                physical_resist=physical,
                spell_resist=spell,
                set_extra_bash_damage=set_bash,
            ),
            legality=legality,
        )
        if candidate.unresolved:
            objective = ExtremeBashObjectiveResult(
                objective_key=objective.objective_key,
                reviewed_value=objective.reviewed_value,
                unresolved_channels=objective.unresolved_channels + tuple(
                    f"gear_set:{problem}" for problem in candidate.unresolved
                ),
                legality_blockers=objective.legality_blockers,
            )
        return ExtremeBashGearSetEvaluation(candidate=candidate, objective=objective)

    @classmethod
    def candidates_for_objective(
        cls,
        repository: GearSetRepository,
        base_inputs: ExtremeBashDamageInputs,
        *,
        legality: ExtremeBashLegalityContext | None = None,
    ) -> tuple[ExtremeBashGearSetEvaluation, ...]:
        rows = tuple(
            cls.evaluate_candidate(
                cls.candidate_for_set(repository, gear_set.name),
                base_inputs,
                legality=legality,
            )
            for gear_set in repository.list_sets()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    not row.objective.mechanic_complete,
                    -row.objective.reviewed_value,
                    row.candidate.set_name.casefold(),
                    row.candidate.set_id,
                ),
            )
        )
