from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.combat_state import CombatState
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeDragonknightEarthenHeartMendingResult:
    combat_state: CombatState
    major_mending_active: bool
    source_ability_name: str | None
    reviewed_duration_seconds: float | None
    unresolved: tuple[str, ...]


class ExtremeDragonknightEarthenHeartMendingService:
    """Resolve reviewed Obsidian Shield-family Major Mending windows.

    Under reviewed U50 semantics, Obsidian Shield and Igneous Shield grant Major
    Mending for 4 seconds, while Fragmented Shield extends the named buff to
    6 seconds. The caller must explicitly state that the Major Mending window is
    active; this service never assumes a shield was cast simply because Earthen
    Heart is legal for the build.

    The effect is routed through ``CombatState`` so canonical named-buff semantics
    own Major Mending's +16% Healing Done and duplicate Major Mending sources are
    deduplicated at the combat-state boundary.
    """

    EARTHEN_HEART_ID = "earthen_heart"
    SOURCE_DURATIONS = {
        "obsidian shield": 4.0,
        "igneous shield": 4.0,
        "fragmented shield": 6.0,
    }

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def earthen_heart_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.EARTHEN_HEART_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "dragonknight"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        source_ability_name: str | None,
        major_mending_window_active: bool = False,
    ) -> ExtremeDragonknightEarthenHeartMendingResult:
        if not major_mending_window_active:
            return ExtremeDragonknightEarthenHeartMendingResult(
                combat_state=CombatState(),
                major_mending_active=False,
                source_ability_name=None,
                reviewed_duration_seconds=None,
                unresolved=(),
            )

        base_state = CombatState(in_combat=True)
        normalized = " ".join(str(source_ability_name or "").strip().casefold().split())
        duration = self.SOURCE_DURATIONS.get(normalized)
        if duration is None:
            return ExtremeDragonknightEarthenHeartMendingResult(
                combat_state=base_state,
                major_mending_active=False,
                source_ability_name=str(source_ability_name or "").strip() or None,
                reviewed_duration_seconds=None,
                unresolved=(
                    "Dragonknight Major Mending requires a reviewed Obsidian Shield-family source",
                ),
            )

        canonical_name = next(
            name.title() for name in self.SOURCE_DURATIONS if name == normalized
        )
        if not self.earthen_heart_equipped(build):
            return ExtremeDragonknightEarthenHeartMendingResult(
                combat_state=base_state,
                major_mending_active=False,
                source_ability_name=canonical_name,
                reviewed_duration_seconds=duration,
                unresolved=(
                    "Dragonknight Major Mending source requires the Earthen Heart class line",
                ),
            )

        return ExtremeDragonknightEarthenHeartMendingResult(
            combat_state=CombatState(in_combat=True, active_buffs=("Major Mending",)),
            major_mending_active=True,
            source_ability_name=canonical_name,
            reviewed_duration_seconds=duration,
            unresolved=(),
        )
