from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class TopTeamPlayer:
    """One observed player setup from a ranked ESO Logs team.

    The richer fields are additive so the current gear-only Performance card can
    keep reading Name/Role/GearSets while template intake can also use class,
    observed abilities, and optional lazily-resolved Mundus evidence.
    """

    Name: str = ""
    Role: str = "dps"
    GearSets: list[str] = field(default_factory=list)
    ClassName: str = ""
    Abilities: list[str] = field(default_factory=list)
    Mundus: str = ""
    ActorId: int | None = None

    @property
    def EsoClass(self) -> str:
        """Compatibility alias for code that consumes canonical build-style names."""

        return self.ClassName

    @property
    def Skills(self) -> list[str]:
        """Compatibility alias for template adapters."""

        return self.Abilities

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "TopTeamPlayer":
        data = dict(data or {})
        actor_id = data.get("ActorId", data.get("actor_id"))
        return cls(
            Name=str(data.get("Name", data.get("name", "")) or ""),
            Role=str(data.get("Role", data.get("role", "dps")) or "dps"),
            GearSets=list(data.get("GearSets", data.get("gear_sets", [])) or []),
            ClassName=str(
                data.get("ClassName", data.get("EsoClass", data.get("class_name", "")))
                or ""
            ),
            Abilities=list(data.get("Abilities", data.get("Skills", data.get("abilities", []))) or []),
            Mundus=str(data.get("Mundus", data.get("mundus", "")) or ""),
            ActorId=(None if actor_id is None else int(actor_id)),
        )


# Backward-compatible name used by the earlier working Top Team implementation.
TeamPlayerBuild = TopTeamPlayer


@dataclass(slots=True)
class TopTeamResult:
    TrialName: str = ""
    EncounterName: str = ""
    ReportCode: str = ""
    FightId: int = 0
    Players: list[TopTeamPlayer] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "TrialName": self.TrialName,
            "EncounterName": self.EncounterName,
            "ReportCode": self.ReportCode,
            "FightId": self.FightId,
            "Players": [player.to_dict() for player in self.Players],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "TopTeamResult":
        data = dict(data or {})
        return cls(
            TrialName=str(data.get("TrialName", "") or ""),
            EncounterName=str(data.get("EncounterName", "") or ""),
            ReportCode=str(data.get("ReportCode", "") or ""),
            FightId=int(data.get("FightId", 0) or 0),
            Players=[
                TopTeamPlayer.from_dict(player)
                for player in (data.get("Players") or ())
                if isinstance(player, dict)
            ],
        )
