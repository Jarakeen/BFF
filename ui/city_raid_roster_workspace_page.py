from __future__ import annotations

"""Urban Wilderness Roster entry point.

The themed roster workspace already owns the approved one-screen dashboard: six
Collectibles-style navigation cards, Active Roster, Quick Actions, illustrated city/
field panels, Team Snapshot, Recruitment Needs, and Recent Activity.  Keep this
compatibility class deliberately thin so we do not layer the retired tabbed workspace
on top of the new dashboard.
"""

from ui.themed_raid_roster_workspace_page import ThemedRaidRosterWorkspacePage


class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):
    """Compatibility route name for the single Urban Wilderness Roster dashboard."""

    pass


__all__ = ["CityRaidRosterWorkspacePage"]
