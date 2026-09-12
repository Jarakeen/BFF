from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from engine.config import get_data_dir
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.damage_done import DamageDoneModifiers
from models.build_model import PlayerBuild


_VALUE = r"([0-9]+(?:\.[0-9]+)?)"


@dataclass(frozen=True)
class RotationSavedBuildDDDamageDoneResolution:
    """Reviewed unconditional Damage Done buckets resolved from one saved DD build."""

    modifiers: DamageDoneModifiers = DamageDoneModifiers()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RotationSavedBuildDDDamageDoneService:
    """Resolve reviewed saved-build Champion Point Damage Done modifiers.

    This service owns only unconditional per-event Damage Done categories whose ESO
    semantics are explicit in the canonical Champion Point record. It deliberately
    excludes conditional stars such as Exploiter because their value depends on exact
    target state at each hit/tick and therefore belongs to runtime target evaluation.
    """

    _SEMANTICS = {
        "master-at-arms": (
            "direct",
            rf"^Increases your damage done with direct damage attacks by {_VALUE}% per stage\.$",
        ),
        "biting aura": (
            "area",
            rf"^Increases your damage done with area of effect attacks by {_VALUE}% per stage\.$",
        ),
        "thaumaturge": (
            "dot",
            rf"^Increases your damage done with damage over time effects by {_VALUE}% per stage\.$",
        ),
    }

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        champion_point_repository: ChampionPointStaticRepository | object | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.repository = champion_point_repository or ChampionPointStaticRepository(database)

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

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

    def resolve(self, build: PlayerBuild) -> RotationSavedBuildDDDamageDoneResolution:
        values = {
            "generic": 0.0,
            "direct": 0.0,
            "dot": 0.0,
            "area": 0.0,
            "single_target": 0.0,
        }
        unresolved: list[str] = []

        for entry in tuple(getattr(build, "ChampionPoints", ()) or ()):
            name = str(getattr(entry, "Name", "") or "").strip()
            key = self._key(name)
            semantic = self._SEMANTICS.get(key)
            if semantic is None:
                continue

            points = self._points(getattr(entry, "Points", ""))
            if points is None:
                unresolved.append(
                    f"Champion Point {name}: allocation is not a non-negative integer"
                )
                continue

            record = self.repository.get(name)
            if record is None:
                unresolved.append(f"Champion Point not found: {name}")
                continue

            stages = self._stages(record, points)
            if stages <= 0:
                continue

            field, pattern = semantic
            first_line = str(record.description or "").splitlines()[0].strip()
            match = re.match(pattern, first_line, flags=re.IGNORECASE)
            if match is None:
                unresolved.append(
                    f"Champion Point {name}: reviewed DD Damage Done semantics no longer match canonical tooltip: {first_line}"
                )
                continue

            per_stage = float(match.group(1)) / 100.0
            values[field] += per_stage * stages

        return RotationSavedBuildDDDamageDoneResolution(
            modifiers=DamageDoneModifiers(**values),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationSavedBuildDDDamageDoneResolution",
    "RotationSavedBuildDDDamageDoneService",
]
