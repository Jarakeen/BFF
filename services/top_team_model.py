# models/top_team_model.py
#
# Data model for the "Top Ranked Team" card on the Capabilities
# page: one row per player in the top-ranking log for a chosen
# trial + boss, with role/class, equipped gear sets, skills, and
# (where detectable) Mundus stone.

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class TeamPlayerBuild:
    """One player's build, as read off the top-ranked log."""

    Name: str = ""
    ClassName: str = ""
    Role: str = ""  # "tank" | "healer" | "dps"
    GearSets: list[str] = field(default_factory=list)
    Abilities: list[str] = field(default_factory=list)
    Mundus: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "TeamPlayerBuild":
        data = data or {}
        return cls(
            Name=data.get("Name", ""),
            ClassName=data.get("ClassName", ""),
            Role=data.get("Role", ""),
            GearSets=list(data.get("GearSets", []) or []),
            Abilities=list(data.get("Abilities", []) or []),
            Mundus=data.get("Mundus", ""),
        )


@dataclass
class TopTeamResult:
    """The full top-ranked team for one trial + boss selection."""

    TrialName: str = ""
    EncounterName: str = ""
    ReportCode: str = ""
    FightId: int = 0
    Players: list[TeamPlayerBuild] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "TrialName": self.TrialName,
            "EncounterName": self.EncounterName,
            "ReportCode": self.ReportCode,
            "FightId": self.FightId,
            "Players": [p.to_dict() for p in self.Players],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "TopTeamResult":
        data = data or {}
        return cls(
            TrialName=data.get("TrialName", ""),
            EncounterName=data.get("EncounterName", ""),
            ReportCode=data.get("ReportCode", ""),
            FightId=int(data.get("FightId", 0)),
            Players=[
                TeamPlayerBuild.from_dict(p)
                for p in (data.get("Players", []) or [])
            ],
        )
