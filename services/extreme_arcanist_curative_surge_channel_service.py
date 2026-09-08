from __future__ import annotations

from dataclasses import dataclass
import re

from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeArcanistCurativeSurgeChannelResult:
    applies: bool
    final_tick_multiplier: float | None
    whole_channel_multiplier: float | None
    unresolved: tuple[str, ...]


class ExtremeArcanistCurativeSurgeChannelService:
    """Resolve the reviewed Curative Surge channel-scaling boundary.

    Under reviewed U50 semantics, Curative Surge channels for 4.5 seconds and
    gradually grows stronger, reaching up to 192% more healing at the end of the
    channel. The 192% value is therefore a late-channel/tick modifier, not a
    multiplier for the entire 4.5-second aggregate heal.

    BFF's current Extreme healing event represents HEAL coefficient components as
    aggregate event values and does not yet expose tick cadence or per-tick
    coefficient output. This resolver records the proven 2.92 final-tick ceiling
    while intentionally leaving the whole-channel multiplier unresolved. That
    preserves a useful numeric fact without manufacturing an inflated aggregate
    heal.

    Explicit ``ClassSkillLines`` remain authoritative for subclass snapshots.
    """

    ABILITY_NAME = "Curative Surge"
    CURATIVE_RUNEFORMS_ID = "curative_runeforms"
    FINAL_TICK_BONUS = 1.92
    FINAL_TICK_MULTIPLIER = 1.0 + FINAL_TICK_BONUS

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def curative_runeforms_equipped(cls, build: PlayerBuild) -> bool:
        explicit = tuple(
            cls._line_id(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if cls._line_id(value)
        )
        if explicit:
            return cls.CURATIVE_RUNEFORMS_ID in explicit
        return str(build.EsoClass or "").strip().casefold() == "arcanist"

    def resolve(
        self,
        *,
        build: PlayerBuild,
        ability_name: str,
    ) -> ExtremeArcanistCurativeSurgeChannelResult:
        name = str(ability_name or "").strip()
        if name.casefold() != self.ABILITY_NAME.casefold():
            return ExtremeArcanistCurativeSurgeChannelResult(
                applies=False,
                final_tick_multiplier=None,
                whole_channel_multiplier=1.0,
                unresolved=(),
            )
        if not self.curative_runeforms_equipped(build):
            return ExtremeArcanistCurativeSurgeChannelResult(
                applies=False,
                final_tick_multiplier=None,
                whole_channel_multiplier=1.0,
                unresolved=(),
            )

        return ExtremeArcanistCurativeSurgeChannelResult(
            applies=True,
            final_tick_multiplier=self.FINAL_TICK_MULTIPLIER,
            whole_channel_multiplier=None,
            unresolved=(
                "Curative Surge aggregate healing requires tick-level channel timing; "
                "the reviewed 192% bonus applies only at the end of the 4.5-second channel",
            ),
        )
