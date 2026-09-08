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

    If the same normalized action name appears as both a normal skill and an
    ultimate, the saved build does not provide one unambiguous executable identity.
    That name is therefore omitted from slot requirements and returned as unresolved
    evidence rather than allowing dictionary/order behavior to choose one meaning.
    """

    def resolve(self, player_build: PlayerBuild) -> RotationSavedBuildActionSlotEvidence:
        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        if not front and not back:
            return RotationSavedBuildActionSlotEvidence()

        bars_by_action: dict[tuple[RotationActionKind, str], list[str]] = {}
        display_name: dict[tuple[RotationActionKind, str], str] = {}
        kinds_by_name: dict[str, set[RotationActionKind]] = {}
        display_name_by_name: dict[str, str] = {}

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
                normalized_name = name.casefold()
                display_name_by_name.setdefault(normalized_name, name)
                kinds_by_name.setdefault(normalized_name, set()).add(kind)

                key = (kind, normalized_name)
                display_name.setdefault(key, name)
                bars = bars_by_action.setdefault(key, [])
                if bar not in bars:
                    bars.append(bar)

        ambiguous_names = {
            name_key
            for name_key, kinds in kinds_by_name.items()
            if len(kinds) > 1
        }
        unresolved = tuple(
            "saved-build action slot identity is ambiguous because "
            f"{display_name_by_name[name_key]!r} appears as both skill and ultimate"
            for name_key in sorted(ambiguous_names)
        )

        requirements = tuple(
            RotationActionSlotRequirement(
                action_name=display_name[key],
                allowed_bars=tuple(bars),
                action_kind=key[0],
            )
            for key, bars in bars_by_action.items()
            if key[1] not in ambiguous_names
        )
        return RotationSavedBuildActionSlotEvidence(
            slot_requirements=requirements,
            unresolved=unresolved,
        )


__all__ = [
    "RotationSavedBuildActionSlotEvidence",
    "RotationSavedBuildActionSlotService",
]
