# services/mock_achievement_provider.py

from dataclasses import dataclass


@dataclass
class MockAchievement:

    id: str
    name: str
    category: str
    completed: bool


class MockAchievementProvider:

    def categories(self):

        return [
            "Trials",
            "Dungeons",
            "Housing",
            "Exploration",
        ]

    def achievements(self, category):

        return [

            MockAchievement(
                id="1",
                name="No Death",
                category=category,
                completed=False,
            ),

            MockAchievement(
                id="2",
                name="Speed Run",
                category=category,
                completed=True,
            ),

            MockAchievement(
                id="3",
                name="Hard Mode",
                category=category,
                completed=False,
            ),
        ]

    def achievements(self, category):
        ...

    def completed_count(self):
        return 1

    def total_count(self):
        return 3

    def subcategories(self, category: str) -> list[str]:

        return [
            "General",
            "Veteran",
            "Hard Mode",
        ]