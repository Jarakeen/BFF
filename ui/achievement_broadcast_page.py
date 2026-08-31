"""OBS-facing achievement run display/control desk.

This is the canonical import name for the former ``achievement_desk_page``
module. The legacy module remains temporarily as a compatibility source so
existing imports do not break during the UX naming migration.
"""

from ui.achievement_desk_page import AchievementPage as AchievementBroadcastPage


__all__ = ["AchievementBroadcastPage"]
