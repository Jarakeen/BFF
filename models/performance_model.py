# models/performance_model.py
#
# Data model for the Capabilities page's Performance Dashboard tab:
# who you are in a given ESO Logs fight (by name, or by anonymized
# label like "Anonymous 7" when the report owner hid names), plus
# the computed buff/debuff uptimes, output totals, and per-ability
# breakdown built from that.
#
# Only the *pick* (report/fight/actor/role) is persisted between
# sessions -- the computed PerformanceSnapshot is intentionally not
# saved to disk, so it can never go stale silently; it's re-fetched
# from ESO Logs each time the tab is opened or refreshed.

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class ActorChoice:
    """One player found in a fight, offered in the 'Who Am I?' picker."""

    ActorId: int
    Label: str
    Role: str = "DPS"  # "Tank" | "Healer" | "DPS", from ESO Logs' own grouping
    Anonymous: bool = False


@dataclass
class AbilityUptime:
    """One row in a buff/debuff uptime chart."""

    Name: str = ""
    UptimeSeconds: float = 0.0
    UptimePercent: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AbilityBreakdown:
    """One row in a top-abilities chart (damage or healing by ability)."""

    Name: str = ""
    Total: float = 0.0
    Percent: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceSnapshot:
    """
    Everything the dashboard needs to draw for one actor on one
    fight -- built fresh by PerformanceDashboardService each time
    "Show My Performance" is clicked, never persisted.
    """

    ReportCode: str = ""
    FightId: str = ""
    ActorId: int | None = None
    ActorLabel: str = ""
    Role: str = "DPS"

    FightName: str = ""
    FightDurationSeconds: float = 0.0

    BuffUptimes: list[AbilityUptime] = field(default_factory=list)
    DebuffUptimes: list[AbilityUptime] = field(default_factory=list)

    OutputLabel: str = "Damage"  # "Damage" | "Healing"
    OutputRateLabel: str = "DPS"  # "DPS" | "HPS"
    OutputTotal: float = 0.0
    OutputPerSecond: float = 0.0
    OutputSeries: list[tuple[float, float]] = field(default_factory=list)

    TopAbilities: list[AbilityBreakdown] = field(default_factory=list)

    PeakWindowLabel: str = ""


@dataclass
class PerformanceProfile:
    """
    One raid member's Performance Dashboard tab -- just enough of a
    pick to re-run the same query next time without re-typing it.
    """

    Name: str = ""
    ReportCode: str = ""
    FightId: str = ""
    ActorId: int | None = None
    ActorLabel: str = ""
    Role: str = "DPS"

    def to_dict(self) -> dict:

        return {
            "Name": self.Name,
            "ReportCode": self.ReportCode,
            "FightId": self.FightId,
            "ActorId": self.ActorId,
            "ActorLabel": self.ActorLabel,
            "Role": self.Role,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "PerformanceProfile":

        data = dict(data or {})

        actor_id = data.get("ActorId")

        return cls(
            Name=data.get("Name", ""),
            ReportCode=data.get("ReportCode", ""),
            FightId=data.get("FightId", ""),
            ActorId=int(actor_id) if actor_id is not None else None,
            ActorLabel=data.get("ActorLabel", ""),
            Role=data.get("Role", "DPS"),
        )

    def display_label(self, fallback: str) -> str:

        return self.Name.strip() or self.ActorLabel.strip() or fallback


@dataclass
class PerformanceRoster:
    """Up to 12 PerformanceProfiles, one per raid team member tab."""

    Members: list[PerformanceProfile] = field(
        default_factory=lambda: [PerformanceProfile()]
    )

    MAX_MEMBERS = 12

    def to_dict(self) -> dict:
        return {"Members": [m.to_dict() for m in self.Members]}

    @classmethod
    def from_dict(cls, data: dict | None) -> "PerformanceRoster":

        data = data or {}

        members = [
            PerformanceProfile.from_dict(m)
            for m in data.get("Members", [])
        ]

        if not members:
            members = [PerformanceProfile()]

        return cls(Members=members[: cls.MAX_MEMBERS])
