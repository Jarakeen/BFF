from __future__ import annotations

"""Project canonical provisioning choices onto a Recovery objective.

This service owns the reusable food/drink catalogue reduction that was previously
embedded in a Health Recovery audit.  It does not choose a whole Extreme build.
It answers the narrower question: for one Recovery stat, what is the strongest
mapped static food and strongest mapped static drink in the canonical catalogue?
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.effects import EffectOperation
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "health_recovery": StatId.HEALTH_RECOVERY,
    "magicka_recovery": StatId.MAGICKA_RECOVERY,
    "stamina_recovery": StatId.STAMINA_RECOVERY,
}


@dataclass(frozen=True)
class ExtremeRecoveryProvisioningCandidate:
    name: str
    kind: str
    delta: float


@dataclass(frozen=True)
class ExtremeRecoveryProvisioningProjection:
    objective_key: str
    reviewed_names: int
    candidates: tuple[ExtremeRecoveryProvisioningCandidate, ...]
    unresolved: tuple[str, ...] = ()

    def best(self, kind: str) -> ExtremeRecoveryProvisioningCandidate | None:
        target = str(kind or "").strip().casefold()
        return next((row for row in self.candidates if row.kind == target), None)

    @property
    def food(self) -> ExtremeRecoveryProvisioningCandidate | None:
        return self.best("food")

    @property
    def drink(self) -> ExtremeRecoveryProvisioningCandidate | None:
        return self.best("drink")

    @property
    def comparison_proven(self) -> bool:
        return self.food is not None and self.drink is not None and not self.unresolved


class ExtremeRecoveryProvisioningProjectionService:
    """Reduce canonical food/drink static effects for one Recovery objective."""

    @staticmethod
    def _kind_map(database_path: str | Path) -> tuple[dict[str, str], tuple[str, ...]]:
        path = Path(database_path)
        try:
            connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            return {}, (f"Provisioning kind database unreadable: {exc}",)

        with connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "entity" not in tables:
                return {}, ("Provisioning kind database missing entity table",)
            rows = connection.execute(
                """
                SELECT lower(name), lower(trim(entity_type))
                FROM entity
                WHERE lower(trim(entity_type)) IN ('food', 'drink')
                  AND trim(coalesce(name, '')) <> ''
                ORDER BY lower(name), lower(trim(entity_type))
                """
            ).fetchall()

        values: dict[str, set[str]] = {}
        for raw_name, raw_kind in rows:
            name = str(raw_name or "").strip().casefold()
            kind = str(raw_kind or "").strip().casefold()
            if name and kind:
                values.setdefault(name, set()).add(kind)

        unresolved = tuple(
            f"Provisioning {name!r} has ambiguous canonical kinds: {tuple(sorted(kinds))!r}"
            for name, kinds in sorted(values.items())
            if len(kinds) != 1
        )
        kind_map = {
            name: next(iter(kinds))
            for name, kinds in values.items()
            if len(kinds) == 1
        }
        return kind_map, unresolved

    @classmethod
    def project(
        cls,
        repository: ProvisioningStaticRepository,
        *,
        kind_by_name: dict[str, str],
        objective_key: str,
    ) -> ExtremeRecoveryProvisioningProjection:
        key = str(objective_key or "").strip().casefold()
        stat = _OBJECTIVE_STATS.get(key)
        if stat is None:
            return ExtremeRecoveryProvisioningProjection(
                objective_key=key,
                reviewed_names=0,
                candidates=(),
                unresolved=(f"Unsupported Recovery provisioning objective: {objective_key!r}",),
            )

        names = tuple(repository.list_names())
        best: dict[str, ExtremeRecoveryProvisioningCandidate] = {}
        unresolved: list[str] = []
        for raw_name in names:
            name = str(raw_name or "").strip()
            if not name:
                continue
            effects, effect_unresolved = repository.resolve(name)
            target_effects = tuple(effect for effect in effects if effect.stat is stat)
            if not target_effects:
                continue

            value = 0.0
            supported = True
            for effect in target_effects:
                if effect.operation is not EffectOperation.ADD:
                    unresolved.append(
                        f"{name}: unsupported {key} provisioning operation {effect.operation.value}"
                    )
                    supported = False
                    continue
                value += float(effect.value)
            if not supported:
                continue
            for message in effect_unresolved:
                unresolved.append(f"{name}: {message}")
            if value <= 0.0:
                continue

            kind = kind_by_name.get(name.casefold())
            if kind not in {"food", "drink"}:
                unresolved.append(f"{name}: no unique canonical food/drink identity")
                continue
            candidate = ExtremeRecoveryProvisioningCandidate(name=name, kind=kind, delta=value)
            current = best.get(kind)
            if current is None or value > current.delta + 1e-9 or (
                abs(value - current.delta) <= 1e-9
                and (name.casefold(), name) < (current.name.casefold(), current.name)
            ):
                best[kind] = candidate

        return ExtremeRecoveryProvisioningProjection(
            objective_key=key,
            reviewed_names=len(names),
            candidates=tuple(best[kind] for kind in ("food", "drink") if kind in best),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def build(
        cls,
        database_path: str | Path,
        *,
        objective_key: str = "health_recovery",
    ) -> ExtremeRecoveryProvisioningProjection:
        kind_map, kind_unresolved = cls._kind_map(database_path)
        if kind_unresolved:
            return ExtremeRecoveryProvisioningProjection(
                objective_key=str(objective_key or "").strip().casefold(),
                reviewed_names=0,
                candidates=(),
                unresolved=kind_unresolved,
            )
        repository = ProvisioningStaticRepository(database_path)
        return cls.project(
            repository,
            kind_by_name=kind_map,
            objective_key=objective_key,
        )


__all__ = [
    "ExtremeRecoveryProvisioningCandidate",
    "ExtremeRecoveryProvisioningProjection",
    "ExtremeRecoveryProvisioningProjectionService",
]
