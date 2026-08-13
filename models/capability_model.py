# models/capability_model.py
#
# Data model for the Capabilities page: per raid-team-member
# ESO Logs report/fight pointer, the buffs/debuffs/skills
# they want watched, and the most recently fetched uptime
# results (kept so the tab still shows something useful
# after a restart, without re-hitting the API).

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class WatchEntry:
    """A single buff, debuff, or skill to track uptime for."""

    Name: str = ""
    Kind: str = "Buff"  # "Buff" | "Debuff" | "Skill"
    Suggested: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "WatchEntry":
        data = data or {}
        return cls(
            Name=data.get("Name", ""),
            Kind=data.get("Kind", "Buff"),
            Suggested=bool(data.get("Suggested", False)),
        )


@dataclass
class UptimeResult:
    """One computed row in the results table."""

    Name: str = ""
    Kind: str = ""
    UptimeMs: float = 0.0
    UptimePercentFull: float = 0.0
    UptimePercentActive: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "UptimeResult":
        data = data or {}
        return cls(
            Name=data.get("Name", ""),
            Kind=data.get("Kind", ""),
            UptimeMs=float(data.get("UptimeMs", 0.0)),
            UptimePercentFull=float(data.get("UptimePercentFull", 0.0)),
            UptimePercentActive=float(data.get("UptimePercentActive", 0.0)),
        )


@dataclass
class CapabilityProfile:
    """One raid team member's Capabilities tab."""

    Name: str = ""
    ReportCode: str = ""
    FightId: str = ""
    EquippedSets: str = ""
    BossActiveSeconds: str = ""

    Watches: list[WatchEntry] = field(default_factory=list)

    LastResults: list[UptimeResult] = field(default_factory=list)
    LastFightName: str = ""
    LastFightDurationSeconds: float = 0.0

    def to_dict(self) -> dict:

        return {
            "Name": self.Name,
            "ReportCode": self.ReportCode,
            "FightId": self.FightId,
            "EquippedSets": self.EquippedSets,
            "BossActiveSeconds": self.BossActiveSeconds,
            "Watches": [w.to_dict() for w in self.Watches],
            "LastResults": [r.to_dict() for r in self.LastResults],
            "LastFightName": self.LastFightName,
            "LastFightDurationSeconds": self.LastFightDurationSeconds,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "CapabilityProfile":

        data = dict(data or {})

        return cls(
            Name=data.get("Name", ""),
            ReportCode=data.get("ReportCode", ""),
            FightId=data.get("FightId", ""),
            EquippedSets=data.get("EquippedSets", ""),
            BossActiveSeconds=data.get("BossActiveSeconds", ""),
            Watches=[
                WatchEntry.from_dict(w) for w in data.get("Watches", [])
            ],
            LastResults=[
                UptimeResult.from_dict(r) for r in data.get("LastResults", [])
            ],
            LastFightName=data.get("LastFightName", ""),
            LastFightDurationSeconds=float(
                data.get("LastFightDurationSeconds", 0.0)
            ),
        )

    def display_label(self, fallback: str) -> str:

        return self.Name.strip() or fallback


@dataclass
class CapabilityRoster:
    """Up to 12 CapabilityProfiles, one per raid team member tab."""

    Members: list[CapabilityProfile] = field(
        default_factory=lambda: [CapabilityProfile()]
    )

    MAX_MEMBERS = 12

    def to_dict(self) -> dict:
        return {"Members": [m.to_dict() for m in self.Members]}

    @classmethod
    def from_dict(cls, data: dict | None) -> "CapabilityRoster":

        data = data or {}

        members = [
            CapabilityProfile.from_dict(m)
            for m in data.get("Members", [])
        ]

        if not members:
            members = [CapabilityProfile()]

        return cls(Members=members[: cls.MAX_MEMBERS])
