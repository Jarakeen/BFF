# ==================================================
# Black Feather Foundry
#
# File:
# services/raid_service.py
#
# Purpose:
# Records raid progression events for the
# active Expedition.
#
# ==================================================

from __future__ import annotations

from models.event_model import Event
from services.expedition_service import ExpeditionService


class RaidService:
    """
    Handles raid progression events.
    """

    def __init__(
        self,
        expedition: ExpeditionService,
    ):
        self.expedition = expedition

    # --------------------------------------------------
    # Pulls
    # --------------------------------------------------

    def pull_started(
        self,
        boss: str,
        pull: int,
        first_pull: bool = False,
    ):

        self.expedition.add_event(
            Event(
                category="Raid",
                event="Pull Started",
                source="Live Operations",
                payload={
                    "boss": boss,
                    "pull": pull,
                    "first_pull": first_pull,
                },
            )
        )

    def ult_pull(
        self,
        boss: str,
    ):

        self.expedition.add_event(
            Event(
                category="Raid",
                event="Ult Pull",
                source="Live Operations",
                payload={
                    "boss": boss,
                },
            )
        )

    def wipe(
        self,
        boss: str,
        pull: int,
        percent: int,
        rough_night: bool = False,
    ):

        self.expedition.add_event(
            Event(
                category="Raid",
                event="Wipe",
                source="Live Operations",
                payload={
                    "boss": boss,
                    "pull": pull,
                    "percent": percent,
                    "rough_night": rough_night,
                },
            )
        )

    def boss_clear(
        self,
        boss: str,
        pull: int,
    ):

        self.expedition.add_event(
            Event(
                category="Raid",
                event="Boss Clear",
                source="Live Operations",
                payload={
                    "boss": boss,
                    "pull": pull,
                },
            )
        )

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    @property
    def total_pulls(self) -> int:

        return sum(
            event.event == "Pull Started"
            for event in self.expedition.expedition.Events
        )

    @property
    def total_wipes(self) -> int:

        return sum(
            event.event == "Wipe"
            for event in self.expedition.expedition.Events
        )

    @property
    def best_pull(self) -> int | None:

        percentages = [

            event.payload["percent"]

            for event in self.expedition.expedition.Events

            if event.event == "Wipe"

            and "percent" in event.payload

        ]

        if not percentages:
            return None

        return min(percentages)