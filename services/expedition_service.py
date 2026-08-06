# ==================================================
# Black Feather Foundry
#
# File:
# services/expedition_service.py
#
# Purpose:
# Maintains the active Expedition for the current
# streaming session.
#
# ==================================================

from __future__ import annotations

from datetime import datetime

from models.event_model import Event
from models.expedition_model import ExpeditionModel


class ExpeditionService:
    """
    Maintains the current Expedition.
    """

    def __init__(self):

        self._expedition = ExpeditionModel()

        self.new()

    # --------------------------------------------------
    # Expedition
    # --------------------------------------------------

    @property
    def expedition(self) -> ExpeditionModel:
        """
        Return the active Expedition.
        """

        return self._expedition

    def new(self) -> ExpeditionModel:
        """
        Begin a new Expedition.
        """

        self._expedition = ExpeditionModel()

        #
        # Optional if you add these to ExpeditionModel
        #

        self._expedition.StartTime = datetime.now()

        self._expedition.Events = []

        return self._expedition

    def reset(self):
        """
        Reset the current Expedition.
        """

        self.new()

    # --------------------------------------------------
    # Events
    # --------------------------------------------------

    def add_event(self, event: Event):
        """
        Record an Event for the active Expedition.
        """

        self._expedition.Events.append(event)

    # --------------------------------------------------
    # Convenience
    # --------------------------------------------------

    def event_count(self) -> int:
        """
        Return the number of recorded events.
        """

        return len(self._expedition.Events)