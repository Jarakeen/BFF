from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from engine.config import get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild


_VALUE = r"([0-9]+(?:\.[0-9]+)?)"


def exploiter_damage_done_bonus(
    target_combat_state: CombatState | None,
    bonus: float,
) -> float:
    """Return reviewed Exploiter Damage Done only for explicit Off Balance state."""

    value = max(0.0, float(bonus))
    if value <= 0.0 or target_combat_state is None:
        return 0.0
    return value if target_combat_state.has_buff("Off Balance") else 0.0


@dataclass(frozen=True)
class RotationSavedBuildDDConditionalDamageDoneResolution:
    """Reviewed target-state-dependent DD Damage Done values from one saved build."""

    exploiter_bonus: float = 0.0
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RotationSavedBuildDDConditionalDamageDoneService:
    """Resolve saved-build DD Damage Done that depends on exact target runtime state.

    Exploiter is intentionally represented as a stored bonus magnitude only. Whether
    that magnitude applies belongs to the exact target combat state at each damage
    event. Callers apply it only when the target is explicitly Off Balance.
    """

    _EXPLOITER_PATTERN = (
        rf"^Increases your damage done against Off Balance enemies by {_VALUE}% per stage\.$"
    )

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        champion_point_repository: ChampionPointStaticRepository | object | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.repository = champion_point_repository or ChampionPointStaticRepository(database)

    @staticmethod
    def _points(value: object) -> int | None:
        try:
            points = int(str(value or "0").strip() or "0")
        except (TypeError, ValueError):
            return None
        return points if points >= 0 else None

    @staticmethod
    def _stages(record, points: int) -> int:
        allocated = max(0, min(int(points), int(record.max_points or points)))
        thresholds = tuple(int(value) for value in tuple(record.jump_points or ()) if int(value) > 0)
        if thresholds:
            return sum(1 for threshold in thresholds if allocated >= threshold)
        return allocated

    def resolve(self, build: PlayerBuild) -> RotationSavedBuildDDConditionalDamageDoneResolution:
        entry = next(
            (
                item
                for item in tuple(getattr(build, "ChampionPoints", ()) or ())
                if str(getattr(item, "Name", "") or "").strip().casefold() == "exploiter"
            ),
            None,
        )
        if entry is None:
            return RotationSavedBuildDDConditionalDamageDoneResolution()

        points = self._points(getattr(entry, "Points", ""))
        if points is None:
            return RotationSavedBuildDDConditionalDamageDoneResolution(
                unresolved=("Champion Point Exploiter: allocation is not a non-negative integer",)
            )

        record = self.repository.get("Exploiter")
        if record is None:
            return RotationSavedBuildDDConditionalDamageDoneResolution(
                unresolved=("Champion Point not found: Exploiter",)
            )

        stages = self._stages(record, points)
        if stages <= 0:
            return RotationSavedBuildDDConditionalDamageDoneResolution()

        first_line = str(record.description or "").splitlines()[0].strip()
        match = re.match(self._EXPLOITER_PATTERN, first_line, flags=re.IGNORECASE)
        if match is None:
            return RotationSavedBuildDDConditionalDamageDoneResolution(
                unresolved=(
                    "Champion Point Exploiter: reviewed Off Balance Damage Done semantics no longer match canonical tooltip: "
                    + first_line,
                )
            )

        return RotationSavedBuildDDConditionalDamageDoneResolution(
            exploiter_bonus=(float(match.group(1)) / 100.0) * stages,
        )


__all__ = [
    "RotationSavedBuildDDConditionalDamageDoneResolution",
    "RotationSavedBuildDDConditionalDamageDoneService",
    "exploiter_damage_done_bonus",
]
