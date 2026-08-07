# ==================================================
# Black Feather Foundry
#
# File:
# services/broadcast_generator.py
#
# Purpose:
# Generates stream titles and live notifications.
#
# ==================================================

from dataclasses import dataclass


@dataclass
class BroadcastRequest:
    focus: str
    location: str
    goal: str
    mood: str
    team: str = ""

@dataclass
class BroadcastResult:
    titles: list[str]
    notifications: list[str]    


class BroadcastGenerator:
    """
    Generates stream titles and notifications.
    """

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def generate_titles(
        self,
        request: BroadcastRequest,
    ) -> list[str]:

        titles = [
            f"Field Notes: {request.location} — {request.goal}",
            f"{request.location} Survey, Continued",
            f"Documenting {request.location} Tonight",
            f"Foundry Field Report — {request.location}",
            f"An Expedition to {request.location}",
            f"{request.location}: Observations in Progress",
            f"Cataloging {request.location} — {request.goal}",
            f"Field Office Live: {request.location}",
            f"Weather Permitting: {request.location}",
            f"Tonight's Log: {request.location} ({request.mood})",
            f"Routine Survey — {request.location}",
            f"{request.goal}, Documented Live from {request.location}",
        ]

        if request.team:
            titles = [
                f"{title} — {request.team}"
                for title in titles
            ]

        return self._unique(titles)[:10]

    def generate_notifications(
        self,
        request: BroadcastRequest,
    ) -> list[str]:

        mood = request.mood.lower()

        goal = (
            request.goal[:1].lower() +
            request.goal[1:]
        ) if request.goal else ""

        notifications = [

            f"The Foundry has resumed operations at {request.location}. Tonight's objective: {request.goal}. Findings to follow.",

            f"Field notes are being taken at {request.location}. Conditions: {mood}.",

            f"An expedition has been dispatched to {request.location}. Purpose: {request.goal}.",

            f"Observed: the crew has returned to {request.location}. Documentation ongoing.",

            f"Tonight's survey covers {request.location}. Objective: {request.goal}. Weather: {mood}.",

            f"The archive grows. Tonight: {request.location}, {goal}.",

            f"Field Office open. Currently investigating {request.location}. No further remarks at this time.",

            f"Routine documentation of {request.location} is underway. All quiet so far.",
        ]

        trimmed = []

        for text in notifications:

            if len(text) > 140:
                text = text[:137].rstrip() + "..."

            trimmed.append(text)

        return self._unique(trimmed)[:8]


    def generate(
        self,
        request: BroadcastRequest,
    ) -> BroadcastResult:
        """
        Generate both stream titles and notifications.
        """

        return BroadcastResult(
            titles=self.generate_titles(request),
            notifications=self.generate_notifications(request),
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:

        seen = set()
        unique = []

        for value in values:

            if value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique