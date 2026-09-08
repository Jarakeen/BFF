from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class RotationSavedBuildActionSlotEvidence:
    """Exact slotted-bar ownership resolved from one saved build."""

    slot_requirements: tuple[RotationActionSlotRequirement, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationSavedBuildActionSlotService:
    """Resolve which bars contain each saved-build skill and ultimate.

    This is structural saved-build evidence, not ESO mechanics inference. Slot 6 on
    each bar is treated as the ultimate slot to match the canonical saved-build bar
    contract already used by timing/range resolvers. Empty slots are ignored.
    """

    def resolve(self, player_build: PlayerBuild) -> RotationSavedBuildActionSlotEvidence:
        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        if not front and not back:
            return RotationSavedBuildActionSlotEvidence()

        bars_by_action: dict[tuple[RotationActionKind, str], list[str]] = {}
        display_name: dict[tuple[RotationActionKind, str], str] = {}

        for bar, names in (("front", front), ("back", back)):
            for index, raw_name in enumerate(names):
                name = str(raw_name or "").strip()
                if not name:
                    continue
                kind = (
                    RotationActionKind.ULTIMATE
                    if index == 5
                    else RotationActionKind.SKILL
                )
                key = (kind, name.casefold())
                display_name.setdefault(key, name)
                bars = bars_by_action.setdefault(key, [])
                if bar not in bars:
                    bars.append(bar)

        requirements = tuple(
            RotationActionSlotRequirement(
                action_name=display_name[key],
                allowed_bars=tuple(bars),
                action_kind=key[0],
            )
            for key, bars in bars_by_action.items()
        )
        return RotationSavedBuildActionSlotEvidence(slot_requirements=requirements)


__all__ = [
    "RotationSavedBuildActionSlotEvidence",
    "RotationSavedBuildActionSlotService",
]
