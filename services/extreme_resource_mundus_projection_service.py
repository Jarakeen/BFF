from __future__ import annotations

"""Proof-reduce the Mundus axis for Extreme max-resource ceilings.

The complete canonical Mundus catalogue remains part of the denominator. A max-
resource objective may retain only one witness when exactly one supported Mundus
stone has a positive effect on the requested maximum and every other stone has no
supported or unsupported record for that target stat. The legal no-Mundus state is
then dominated by that positive witness.

This proof is also sufficient for Twice-Born Star on a single max-resource
objective: adding a second Mundus that cannot modify the target cannot improve the
requested ceiling, so the target stone alone is a valid exact witness.
"""

from dataclasses import dataclass

from minmax.mundus_repository import MundusRepository
from minmax.stat_ids import StatId


_OBJECTIVE_STATS = {
    "max_magicka": StatId.MAX_MAGICKA.value,
    "max_stamina": StatId.MAX_STAMINA.value,
}


@dataclass(frozen=True)
class ExtremeResourceMundusProjection:
    objective_key: str
    stones_reviewed: int
    witness: str | None
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(self.denominator_proven and self.witness and not self.unresolved)


class ExtremeResourceMundusProjectionService:
    """Prove the unique best Mundus witness for Max Magicka / Max Stamina."""

    SUPPORTED_OBJECTIVES = frozenset(_OBJECTIVE_STATS)

    def __init__(self, repository: MundusRepository) -> None:
        self.repository = repository

    def build(self, objective_key: str) -> ExtremeResourceMundusProjection:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme Mundus projection objective: {objective_key!r}")

        names = tuple(
            str(name or "").strip()
            for name in self.repository.list_names()
            if str(name or "").strip()
        )
        get_records = getattr(self.repository, "get_records", None)
        if not callable(get_records):
            return ExtremeResourceMundusProjection(
                objective_key=key,
                stones_reviewed=len(names),
                witness=None,
                denominator_proven=False,
                unresolved=(
                    "Mundus objective projection lacks canonical per-stone record evidence",
                ),
            )

        unresolved: list[str] = []
        positive: list[tuple[float, str]] = []

        for name in names:
            records = tuple(get_records(name))
            if not records:
                unresolved.append(f"Mundus stone has no canonical records: {name}")
                continue

            target_records = tuple(
                row
                for row in records
                if str(row.stat_id).strip().casefold() == target.casefold()
            )
            if not target_records:
                continue
            if len(target_records) != 1:
                unresolved.append(f"Mundus stone has multiple {key} records: {name}")
                continue

            row = target_records[0]
            if not bool(row.supported):
                unresolved.append(
                    f"Mundus stone has unsupported {key} semantics: {name}: {row.notes}"
                )
                continue
            if str(row.unit or "").strip().casefold() != "flat":
                unresolved.append(
                    f"Mundus stone has non-flat {key} semantics: {name}: {row.unit}"
                )
                continue
            value = float(row.value)
            if value > 0.0:
                positive.append((value, name))
            elif value != 0.0:
                unresolved.append(
                    f"Mundus stone has non-positive {key} mutation: {name}: {value}"
                )

        witness: str | None = None
        if positive:
            positive.sort(key=lambda item: (-item[0], item[1].casefold(), item[1]))
            best_value = positive[0][0]
            tied = tuple(
                name for value, name in positive if abs(value - best_value) <= 1e-9
            )
            if len(tied) == 1:
                witness = tied[0]
            else:
                unresolved.append(
                    f"Multiple Mundus stones tie for strongest {key} witness: {', '.join(tied)}"
                )
        else:
            unresolved.append(
                f"Canonical Mundus catalogue contains no positive {key} witness"
            )

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeResourceMundusProjection(
            objective_key=key,
            stones_reviewed=len(names),
            witness=witness,
            denominator_proven=bool(names) and witness is not None and not final_unresolved,
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeResourceMundusProjection",
    "ExtremeResourceMundusProjectionService",
]
