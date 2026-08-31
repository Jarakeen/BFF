"""ESO account achievements workspace.

This module is the canonical import name for the account-achievement browser.
The implementation remains compatible with the former ``collections_page``
module while the UX branch finishes the naming migration.
"""

from ui.collections_page import CollectionsPage


class AchievementsPage(CollectionsPage):
    """Clearly named ESO account achievements page."""

    pass
