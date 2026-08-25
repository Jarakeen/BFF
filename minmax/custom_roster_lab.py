from __future__ import annotations

from dataclasses import dataclass, field

from .encounter_evaluation import EncounterEvaluation
from .mock_roster_lab import MockRosterLab, MockPlayer
from .role import Role


@dataclass
class CustomRosterPlayer:
    name: str
    role: Role
    capabilities: list[str] = field(default_factory=list)
    uptime: float = 1.0


class CustomRosterLab:
    """Mutable, disposable roster builder for Phase 5B UI testing."""

    def __init__(self, evaluator: MockRosterLab | None = None) -> None:
        self.lab = evaluator or MockRosterLab()
        self.players: list[CustomRosterPlayer] = []

    def add_player(
        self,
        name: str,
        role: Role,
        capabilities: list[str] | None = None,
        uptime: float = 1.0,
    ) -> CustomRosterPlayer:
        player = CustomRosterPlayer(
            name=name.strip() or f"Mock {role.value.title()}",
            role=role,
            capabilities=list(capabilities or []),
            uptime=max(0.0, min(1.0, float(uptime))),
        )
        self.players.append(player)
        return player

    def remove_player(self, index: int) -> None:
        del self.players[index]

    def clear(self) -> None:
        self.players.clear()

    def evaluate(self) -> EncounterEvaluation:
        scenario = self._scenario()
        return self.lab.evaluate(scenario)

    def _scenario(self):
        from .mock_roster_lab import MockRosterScenario

        return MockRosterScenario(
            key="custom",
            name="Custom Roster",
            description="Disposable roster assembled in the Phase 5B Test Lab.",
            players=tuple(
                MockPlayer(
                    player.name,
                    player.role,
                    tuple(player.capabilities),
                    player.uptime,
                )
                for player in self.players
            ),
        )
