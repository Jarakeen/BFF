from __future__ import annotations

"""Proof-reduce provisioning choices for Extreme max-resource ceilings.

The full canonical provisioning catalogue is still reviewed. For Max Magicka and
Max Stamina, static provisioning effects are additive and non-negative, so only the
strongest witness in each semantic provisioning kind can affect the objective.
Keeping food and drink separate preserves runtime conditions such as
``drink_buff_active`` while avoiding repeated scoring of every recipe.

Canonical provisioning entries whose static resolver has no mapped sheet stats are
not automatically blockers. Their source tooltip may prove objective irrelevance
when the target resource is absent, or appears only in an explicitly recovery-only
clause. Anything that could plausibly describe the target maximum remains unresolved.
"""

from dataclasses import dataclass
import re
import sqlite3

from minmax.effects import EffectOperation
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}
_OBJECTIVE_RESOURCE_WORD = {
    "max_magicka": "magicka",
    "max_stamina": "stamina",
}


@dataclass(frozen=True)
class ExtremeResourceProvisioningProjection:
    objective_key: str
    choices: tuple[str, ...]
    foods_reviewed: int
    food_witness: str | None
    drink_witness: str | None
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(self.denominator_proven and self.choices and not self.unresolved)


class ExtremeResourceProvisioningProjectionService:
    """Collapse canonical provisioning to strongest food + drink witnesses."""

    SUPPORTED_OBJECTIVES = frozenset(_OBJECTIVE_STATS)

    def __init__(self, repository: ProvisioningStaticRepository) -> None:
        self.repository = repository

    def _kind(self, name: str) -> tuple[str | None, tuple[str, ...]]:
        database_path = str(getattr(self.repository, "database_path", "") or "").strip()
        if not database_path:
            return None, (f"Provisioning type evidence unavailable for {name}: no database path",)

        try:
            with sqlite3.connect(database_path) as connection:
                table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entity'"
                ).fetchone()
                if table is None:
                    return None, (f"Provisioning type evidence unavailable for {name}: entity table missing",)
                rows = connection.execute(
                    """
                    SELECT DISTINCT lower(trim(entity_type))
                    FROM entity
                    WHERE lower(name)=lower(?)
                      AND lower(trim(entity_type)) IN ('food', 'drink', 'provisioning')
                    ORDER BY 1
                    """,
                    (name,),
                ).fetchall()
        except sqlite3.Error as exc:
            return None, (f"Provisioning type evidence unreadable for {name}: {exc}",)

        kinds = tuple(str(row[0] or "").strip().casefold() for row in rows if row[0])
        concrete = tuple(kind for kind in kinds if kind in {"food", "drink"})
        if len(concrete) == 1:
            return concrete[0], ()
        if len(concrete) > 1:
            return None, (f"Provisioning item has ambiguous food/drink identity: {name}",)
        return None, (f"Provisioning item has no canonical food/drink identity: {name}",)

    @staticmethod
    def _better(
        current: tuple[float, str] | None,
        candidate: tuple[float, str],
    ) -> tuple[float, str]:
        if current is None:
            return candidate
        value, name = candidate
        current_value, current_name = current
        if value > current_value + 1e-9:
            return candidate
        if abs(value - current_value) <= 1e-9 and (name.casefold(), name) < (
            current_name.casefold(),
            current_name,
        ):
            return candidate
        return current

    def _unmapped_description_proven_irrelevant(
        self,
        objective_key: str,
        name: str,
    ) -> bool:
        description_getter = getattr(self.repository, "description", None)
        if not callable(description_getter):
            return False
        description = str(description_getter(name) or "").strip()
        if not description:
            return False

        text = " ".join(description.casefold().split())
        resource = _OBJECTIVE_RESOURCE_WORD[objective_key]
        if resource not in text:
            return True

        # Any source tooltip that couples the target resource with a Max clause is
        # potentially relevant and must remain explicit rather than being guessed away.
        if "max" in text:
            return False

        # Remove reviewed recovery-only grammar. This covers both explicit single
        # recovery clauses and ESO's shared "Magicka and Stamina Recovery" wording.
        recovery_patterns = (
            r"health\s*,?\s*magicka\s*,?\s*(?:and\s*)?stamina\s+recovery",
            r"magicka\s+and\s+stamina\s+recovery",
            r"magicka\s+recovery",
            r"stamina\s+recovery",
        )
        remainder = text
        for pattern in recovery_patterns:
            remainder = re.sub(pattern, " ", remainder)
        remainder = " ".join(remainder.split())
        return resource not in remainder

    def build(self, objective_key: str) -> ExtremeResourceProvisioningProjection:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme provisioning projection objective: {objective_key!r}")

        names = tuple(self.repository.list_names())
        unresolved: list[str] = []
        best: dict[str, tuple[float, str] | None] = {"food": None, "drink": None}

        for raw_name in names:
            name = str(raw_name or "").strip()
            if not name:
                continue
            effects, effect_unresolved = self.repository.resolve(name)
            if effect_unresolved and self._unmapped_description_proven_irrelevant(key, name):
                continue
            unresolved.extend(str(item) for item in effect_unresolved if str(item))

            kind, kind_unresolved = self._kind(name)
            unresolved.extend(kind_unresolved)
            if effect_unresolved or kind not in best:
                continue

            value = 0.0
            for effect in effects:
                if effect.stat is not target:
                    continue
                if effect.operation is not EffectOperation.ADD:
                    unresolved.append(
                        f"Provisioning item {name} uses unsupported {key} operation: {effect.operation.value}"
                    )
                    continue
                value += float(effect.value)
            best[kind] = self._better(best[kind], (value, name))

        food = None if best["food"] is None else best["food"][1]
        drink = None if best["drink"] is None else best["drink"][1]
        choices = tuple(
            dict.fromkeys(name for name in (food, drink) if str(name or "").strip())
        )
        if names and not choices:
            unresolved.append("Canonical provisioning catalogue produced no food/drink witness")

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeResourceProvisioningProjection(
            objective_key=key,
            choices=choices,
            foods_reviewed=len(names),
            food_witness=food,
            drink_witness=drink,
            denominator_proven=bool(names) and not final_unresolved,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceProvisioningProjection",
    "ExtremeResourceProvisioningProjectionService",
]
