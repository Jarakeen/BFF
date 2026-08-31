"""Compatibility shim for the old achievement broadcast desk module name.

The OBS-facing achievement run desk now lives in
``ui.achievement_broadcast_page``.
"""

from ui.achievement_broadcast_page import AchievementBroadcastPage


AchievementPage = AchievementBroadcastPage

__all__ = ["AchievementBroadcastPage", "AchievementPage"]
