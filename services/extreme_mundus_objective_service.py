from __future__ import annotations

"""Project canonical Mundus records into Extreme Build objective units.

Mundus mechanics remain owned by ``minmax.mundus_repository``.  This adapter
only translates supported repository records into the objective units already
used by the Extreme engine.  It does not duplicate stone values and it refuses
to score a relevant unsupported record as though it contributed zero.
"""

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.mundus_repository import MundusEffectRecord, MundusRepository
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class ExtremeMundusObjectiveCandidate:
    mundus_name: str
    objective_key: str
    projected_delta: float | None
    source_records: tuple[MundusEffectRecord, ...]
    unresolved: tuple[str, ...] = ()


class ExtremeMundusObjectiveService:
    """Enumerate one Mundus choice for a reviewed Extreme objective."""

    REVIEWED_OBJECTIVES = (
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

    _DIRECT_STAT_BY_OBJECTIVE = {
        "critical_damage": StatId.CRITICAL_DAMAGE.value,
        "magicka_recovery": StatId.MAGICKA_RECOVERY.value,
        "stamina_recovery": StatId.STAMINA_RECOVERY.value,
        "physical_resistance": StatId.PHYSICAL_RESISTANCE.value,
        "spell_resistance": StatId.SPELL_RESISTANCE.value,
        "spell_damage": StatId.SPELL_DAMAGE.value,
        "weapon_damage": StatId.WEAPON_DAMAGE.value,
    }

    @classmethod
    def _record_matches_objective(
        cls,
        record: MundusEffectRecord,
        objective_key: str,
    ) -> bool:
        if objective_key in {"spell_critical", "weapon_critical"}:
            return record.stat_id == StatId.CRITICAL_CHANCE.value
        return record.stat_id == cls._DIRECT_STAT_BY_OBJECTIVE.get(objective_key)

    @staticmethod
    def _record_delta(
        record: MundusEffectRecord,
        objective_key: str,
        *,
        multiplier: float,
    ) -> float:
        value = float(record.value) * float(multiplier)

        if objective_key == "critical_damage":
            if record.unit != "percent":
                raise ValueError(
                    f"critical_damage Mundus record must use percent units: {record.name}"
                )
            return value / 100.0

        if objective_key in {"spell_critical", "weapon_critical"}:
            if record.unit != "rating":
                raise ValueError(
                    f"critical chance Mundus record must use rating units: {record.name}"
                )
            return GearStatInputResolver.critical_rating_to_ratio(value)

        if record.unit != "flat":
            raise ValueError(
                f"{objective_key} Mundus record must use flat units: {record.name}"
            )
        return value

    @classmethod
    def candidate_for_name(
        cls,
        repository: MundusRepository,
        mundus_name: str,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> ExtremeMundusObjectiveCandidate:
        objective = objective_key.strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme Mundus objective: {objective_key!r}")
        if multiplier < 0.0:
            raise ValueError("Mundus multiplier must be non-negative")

        records = tuple(repository.get_records(mundus_name))
        relevant = tuple(
            record for record in records if cls._record_matches_objective(record, objective)
        )
        unsupported = tuple(record for record in relevant if not record.supported)
        if unsupported:
            unresolved = tuple(
                f"{record.name}: {record.stat_id} unresolved ({record.notes})"
                for record in unsupported
            )
            return ExtremeMundusObjectiveCandidate(
                mundus_name=str(mundus_name),
                objective_key=objective,
                projected_delta=None,
                source_records=relevant,
                unresolved=unresolved,
            )

        delta = sum(
            cls._record_delta(record, objective, multiplier=multiplier)
            for record in relevant
        )
        return ExtremeMundusObjectiveCandidate(
            mundus_name=str(mundus_name),
            objective_key=objective,
            projected_delta=float(delta),
            source_records=relevant,
        )

    @classmethod
    def candidates_for_objective(
        cls,
        repository: MundusRepository,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> tuple[ExtremeMundusObjectiveCandidate, ...]:
        rows = tuple(
            cls.candidate_for_name(
                repository,
                name,
                objective_key,
                multiplier=multiplier,
            )
            for name in repository.list_names()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.projected_delta is None,
                    -(row.projected_delta or 0.0),
                    row.mundus_name.casefold(),
                ),
            )
        )

    @classmethod
    def best_for_objective(
        cls,
        repository: MundusRepository,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> ExtremeMundusObjectiveCandidate | None:
        return next(
            (
                row
                for row in cls.candidates_for_objective(
                    repository,
                    objective_key,
                    multiplier=multiplier,
                )
                if row.projected_delta is not None
            ),
            None,
        )
