from __future__ import annotations

import re

from .champion_point_static_repository import ChampionPointStaticRepository
from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


_VALUE = r"([0-9]+(?:\.[0-9]+)?)"


class ChampionPointMovementEffectResolver:
    """Resolve reviewed movement CP stars from canonical Champion Point records.

    Values are parsed from the same DB-backed Champion Point tooltip records used
    by the static CP repository. This keeps movement out of duplicated Extreme
    constants while allowing the broader static-stat owner to delegate here later.
    """

    def __init__(self, repository: ChampionPointStaticRepository) -> None:
        self.repository = repository

    def resolve(self, name: str, points: int) -> tuple[list[Effect], list[str]]:
        record = self.repository.get(name)
        if record is None:
            return [], [f"Champion Point not found: {name}"]

        stages = self.repository._stages(record, points)
        if stages <= 0:
            return [], []

        first_line = str(record.description or "").splitlines()[0].strip()
        movement = re.match(
            rf"^Increases(?: your)? Movement Speed by {_VALUE}% per stage\.$",
            first_line,
            flags=re.IGNORECASE,
        )
        if movement:
            amount = float(movement.group(1)) * stages
            return [
                Effect(
                    source=f"Champion Point: {record.name}",
                    stat=StatId.MOVEMENT_SPEED,
                    operation=EffectOperation.ADD_PERCENT,
                    value=amount,
                    unit=EffectUnit.PERCENT,
                )
            ], []

        sprint = re.match(
            rf"^Increases(?: your)? Movement Speed when Sprinting by {_VALUE}% per stage\.$",
            first_line,
            flags=re.IGNORECASE,
        )
        if sprint:
            amount = float(sprint.group(1)) * stages
            return [
                Effect(
                    source=f"Champion Point: {record.name}",
                    stat=StatId.SPRINT_SPEED,
                    operation=EffectOperation.ADD_PERCENT,
                    value=amount,
                    unit=EffectUnit.PERCENT,
                )
            ], []

        return [], [f"Champion Point movement effect not mapped: {record.name}"]


__all__ = ["ChampionPointMovementEffectResolver"]
