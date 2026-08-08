class MockAchievementProvider:

    def categories(self):

        return [
            "Trials",
            "Dungeons",
            "Housing",
            "Exploration",
        ]

    def subcategories(
        self,
        category: str,
    ):

        return [
            "General",
            "Veteran",
            "Hard Mode",
        ]

    def achievements(
        self,
        category: str,
        subcategory: str,
    ):

        return [

            {
                "id": "1",
                "name": "No Death",
                "points": 50,
                "completed": False,
            },

            {
                "id": "2",
                "name": "Speed Run",
                "points": 50,
                "completed": True,
            },

            {
                "id": "3",
                "name": "Hard Mode",
                "points": 100,
                "completed": False,
            },

        ]

    def search(
        self,
        text: str,
    ):

        return self.achievements(
            "",
            "",
        )

    def completed_count(self):

        return 1

    def total_count(self):

        return 3