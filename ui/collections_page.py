"""Compatibility shim for the old achievements module name.

ESO account achievements now live in ``ui.achievements_page``.
ESO mounts, pets, houses, costumes, and other collectibles remain in
``ui.collectibles_page``.
"""

from ui.achievements_page import AchievementsPage


CollectionsPage = AchievementsPage

__all__ = ["AchievementsPage", "CollectionsPage"]
