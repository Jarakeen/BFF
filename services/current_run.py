from dataclasses import dataclass, field

"""
The Current Expedition represents the active ESO run.

Every page contributes information to this object.

When the expedition is complete, ArchiveService writes it to disk.
"""


@dataclass
class CurrentRun:

    archive_id: str = ""

    location: str = ""
    expedition: str = ""
    objective: str = ""
    team: str = ""

    marker_log: str = ""
    boss_log: str = ""

    incident_reports: list = field(default_factory=list)

    achievement_notes: str = ""

    boss_notes: str = ""

    finalized: bool = False