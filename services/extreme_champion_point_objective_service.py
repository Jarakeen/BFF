from __future__ import annotations

"""Project canonical Champion Point mechanics into Extreme objective units.

Champion Point values remain owned by ``minmax.champion_point_static_repository``.
This adapter keeps two truths separate:

1. reviewed static CP effects can contribute a numeric lower bound; and
2. unresolved or runtime CP mechanics remain explicit blockers and are never
   interpreted as zero contribution merely because the static resolver cannot
   map them yet.

The service does not yet choose a legal four-star Champion Bar combination.
It exposes every slottable max-rank candidate individually so a later CP-loadout
optimizer can apply constellation/bar legality without duplicating CP math.
"""

from dataclasses import dataclass

from minmax.champion_point_static_repository import (
    EXTERNALLY_MODELED_DYNAMIC_CP_NAMES,
    ChampionPointRecord,
    ChampionPointStaticRepository,
)
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class ExtremeChampionPointObjectiveCandidate:
    name: str
    objective_key: str
    max_points: int
    slottable: bool
    reviewed_delta: float | None
    source_effects: tuple[Effect, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeChampionPointObjectiveBaseline:
    objective_key: str
    reviewed_lower_bound: float
    resolved_candidates: tuple[ExtremeChampionPointObjectiveCandidate, ...]
    unresolved_candidates: tuple[ExtremeChampionPointObjectiveCandidate, ...]

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved_candidates


class ExtremeChampionPointObjectiveService:
    """Adapt reviewed CP effects to the current Extreme objective matrix."""

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

    _STAT_BY_OBJECTIVE = {
        "max_health": StatId.MAX_HEALTH,
        "max_magicka": StatId.MAX_MAGICKA,
        "max_stamina": StatId.MAX_STAMINA,
        "critical_damage": StatId.CRITICAL_DAMAGE,
        "magicka_recovery": StatId.MAGICKA_RECOVERY,
        "stamina_recovery": StatId.STAMINA_RECOVERY,
        "physical_resistance": StatId.PHYSICAL_RESISTANCE,
        "spell_resistance": StatId.SPELL_RESISTANCE,
        "spell_damage": StatId.SPELL_DAMAGE,
        "weapon_damage": StatId.WEAPON_DAMAGE,
        "spell_critical": StatId.CRITICAL_CHANCE,
        "weapon_critical": StatId.CRITICAL_CHANCE,
    }

    @classmethod
    def _objective(cls, objective_key: str) -> str:
        objective = str(objective_key).strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme Champion Point objective: {objective_key!r}")
        return objective

    @classmethod
    def _effect_delta(
        cls,
        effect: Effect,
        objective: str,
        *,
        reference_value: float | None,
    ) -> tuple[float | None, str | None]:
        target_stat = cls._STAT_BY_OBJECTIVE[objective]
        if effect.stat is not target_stat:
            return 0.0, None

        if effect.operation is EffectOperation.ADD:
            if objective == "critical_damage":
                if effect.unit is not EffectUnit.PERCENT:
                    return None, f"{effect.source}: Critical Damage CP effect has unexpected unit {effect.unit.value}"
                return float(effect.value) / 100.0, None
            if objective in {"spell_critical", "weapon_critical"}:
                if effect.unit is not EffectUnit.FLAT:
                    return None, f"{effect.source}: Critical Chance CP effect has unexpected unit {effect.unit.value}"
                return GearStatInputResolver.critical_rating_to_ratio(float(effect.value)), None
            if effect.unit is not EffectUnit.FLAT:
                return None, f"{effect.source}: {objective} CP effect has unexpected unit {effect.unit.value}"
            return float(effect.value), None

        if effect.operation is EffectOperation.ADD_PERCENT:
            if objective == "critical_damage":
                return float(effect.value) / 100.0, None
            if reference_value is None:
                return None, f"{effect.source}: {objective} percent effect requires a reference value"
            return float(reference_value) * float(effect.value) / 100.0, None

        return None, f"{effect.source}: unsupported CP operation {effect.operation.value} for {objective}"

    @classmethod
    def candidate_for_record(
        cls,
        repository: ChampionPointStaticRepository,
        record: ChampionPointRecord,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> ExtremeChampionPointObjectiveCandidate:
        objective = cls._objective(objective_key)
        name_key = record.name.strip().casefold()

        if name_key in EXTERNALLY_MODELED_DYNAMIC_CP_NAMES:
            return ExtremeChampionPointObjectiveCandidate(
                name=record.name,
                objective_key=objective,
                max_points=record.max_points,
                slottable=record.is_slottable,
                reviewed_delta=None,
                unresolved=(
                    f"Champion Point requires runtime/dynamic Extreme context: {record.name}",
                ),
            )

        effects, unresolved = repository.resolve(record.name, record.max_points)
        if unresolved:
            return ExtremeChampionPointObjectiveCandidate(
                name=record.name,
                objective_key=objective,
                max_points=record.max_points,
                slottable=record.is_slottable,
                reviewed_delta=None,
                source_effects=tuple(effects),
                unresolved=tuple(unresolved),
            )

        total = 0.0
        local_unresolved: list[str] = []
        for effect in effects:
            delta, problem = cls._effect_delta(
                effect,
                objective,
                reference_value=reference_value,
            )
            if problem:
                local_unresolved.append(problem)
            elif delta is not None:
                total += float(delta)

        if local_unresolved:
            return ExtremeChampionPointObjectiveCandidate(
                name=record.name,
                objective_key=objective,
                max_points=record.max_points,
                slottable=record.is_slottable,
                reviewed_delta=None,
                source_effects=tuple(effects),
                unresolved=tuple(local_unresolved),
            )

        return ExtremeChampionPointObjectiveCandidate(
            name=record.name,
            objective_key=objective,
            max_points=record.max_points,
            slottable=record.is_slottable,
            reviewed_delta=total,
            source_effects=tuple(effects),
        )

    @classmethod
    def non_slottable_baseline_for_objective(
        cls,
        repository: ChampionPointStaticRepository,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> ExtremeChampionPointObjectiveBaseline:
        objective = cls._objective(objective_key)
        candidates = tuple(
            cls.candidate_for_record(
                repository,
                record,
                objective,
                reference_value=reference_value,
            )
            for record in repository.non_slottable_records()
        )
        resolved = tuple(row for row in candidates if row.reviewed_delta is not None)
        unresolved = tuple(row for row in candidates if row.reviewed_delta is None)
        return ExtremeChampionPointObjectiveBaseline(
            objective_key=objective,
            reviewed_lower_bound=sum(float(row.reviewed_delta or 0.0) for row in resolved),
            resolved_candidates=resolved,
            unresolved_candidates=unresolved,
        )

    @classmethod
    def slottable_candidates_for_objective(
        cls,
        repository: ChampionPointStaticRepository,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[ExtremeChampionPointObjectiveCandidate, ...]:
        objective = cls._objective(objective_key)
        rows = tuple(
            cls.candidate_for_record(
                repository,
                record,
                objective,
                reference_value=reference_value,
            )
            for record in repository.slottable_records()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.reviewed_delta is None,
                    -(row.reviewed_delta or 0.0),
                    row.name.casefold(),
                ),
            )
        )
