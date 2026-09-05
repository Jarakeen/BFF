from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TopTeamPlayer:
    Name: str = ""
    Role: str = "dps"
    ClassName: str = ""
    GearSets: list[str] = field(default_factory=list)
    Abilities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TopTeamResult:
    TrialName: str = ""
    EncounterName: str = ""
    ReportCode: str = ""
    FightId: int = 0
    SourceReportCount: int = 0
    Players: list[TopTeamPlayer] = field(default_factory=list)
