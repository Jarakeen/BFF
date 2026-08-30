from __future__ import annotations

from dataclasses import dataclass

from .coverage_requirement import CoverageRequirement
from .encounter_evaluation import EncounterEvaluation, EncounterEvaluator
from .encounter_requirements import EncounterRequirementSet
from .role import Role
from .roster_capability_resolver import RosterCapabilityProvider
from .support_effect import SupportEffect
from .support_effect_category import SupportEffectCategory
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


LAB_EFFECTS = (
    "major_courage",
    "major_force",
    "major_breach",
    "minor_brittle",
    "major_sorcery",
    "major_protection",
)


@dataclass(frozen=True)
class MockPlayer:
    name: str
    role: Role
    capabilities: tuple[str, ...] = ()
    uptime: float = 1.0
    exclusivity_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class MockRosterScenario:
    key: str
    name: str
    description: str
    players: tuple[MockPlayer, ...]


class MockRosterLab:
    """Build disposable roster evidence for Phase 5 testing.

    Nothing in this module reads or writes the production roster/build data.
    The resulting evidence is fed directly into the existing Phase 4
    EncounterEvaluator.
    """

    def __init__(self, evaluator: EncounterEvaluator | None = None) -> None:
        self.evaluator = evaluator or EncounterEvaluator()

    @staticmethod
    def scenario_keys() -> tuple[str, ...]:
        return tuple(s.key for s in _SCENARIOS)

    @staticmethod
    def scenarios() -> tuple[MockRosterScenario, ...]:
        return _SCENARIOS

    @staticmethod
    def scenario(key: str) -> MockRosterScenario:
        for scenario in _SCENARIOS:
            if scenario.key == key:
                return scenario
        raise KeyError(f"Unknown mock roster scenario: {key}")

    @staticmethod
    def requirement_set() -> EncounterRequirementSet:
        return EncounterRequirementSet(
            encounter_id="phase5_mock_encounter",
            encounter_name="Phase 5 Mock Encounter",
            requirements=(
                CoverageRequirement(effect_name="major_courage", minimum_uptime=0.80),
                CoverageRequirement(effect_name="major_force", minimum_uptime=0.80),
                CoverageRequirement(effect_name="major_breach", minimum_uptime=0.80),
                CoverageRequirement(effect_name="minor_brittle", minimum_uptime=0.80),
                CoverageRequirement(effect_name="major_sorcery", minimum_uptime=0.80),
                CoverageRequirement(effect_name="major_protection", minimum_uptime=0.80),
            ),
        )

    def capabilities_for(
        self,
        scenario: MockRosterScenario,
    ) -> dict[str, tuple[RosterCapabilityProvider, ...]]:
        capabilities: dict[str, list[RosterCapabilityProvider]] = {}

        for player in scenario.players:
            for effect_name in player.capabilities:
                exclusivity = (
                    effect_name
                    if effect_name in player.exclusivity_groups
                    else None
                )
                effect = SupportEffect(
                    source="Phase 5 Mock Roster",
                    name=effect_name,
                    category=SupportEffectCategory.BUFF,
                    effect_type=effect_name,
                    target_type=SupportTargetType.GROUP,
                    uptime=player.uptime,
                    stacking=StackingBehavior.UNIQUE,
                    exclusivity_group=exclusivity,
                )
                capabilities.setdefault(effect_name, []).append(
                    RosterCapabilityProvider(
                        character_name=player.name,
                        role=player.role,
                        effect=effect,
                    )
                )

        return {name: tuple(providers) for name, providers in capabilities.items()}

    def evaluate(
        self,
        scenario: MockRosterScenario,
    ) -> EncounterEvaluation:
        return self.evaluator.evaluate(
            self.requirement_set(),
            self.capabilities_for(scenario),
        )


def _players(role: Role, count: int, capabilities: tuple[str, ...]) -> tuple[MockPlayer, ...]:
    return tuple(
        MockPlayer(f"Mock {role.value.title()} {index:02d}", role, capabilities)
        for index in range(1, count + 1)
    )


_BALANCED = (
    MockPlayer("Tank 01", Role.TANK, ("major_breach",)),
    MockPlayer("Tank 02", Role.TANK, ("major_protection",)),
    MockPlayer("Healer 01", Role.HEALER, ("major_courage", "major_sorcery")),
    MockPlayer("Healer 02", Role.HEALER, ("minor_brittle",)),
    *_players(Role.DD, 8, ("major_force",)),
)

_HEALERS = tuple(
    MockPlayer(
        f"Healer {index:02d}",
        Role.HEALER,
        LAB_EFFECTS,
    )
    for index in range(1, 13)
)

_DDS = _players(Role.DD, 12, ("major_force",))

_SCENARIOS = (
    MockRosterScenario(
        "balanced12",
        "Balanced 12",
        "A conventional mock trial composition with role-diverse support.",
        _BALANCED,
    ),
    MockRosterScenario(
        "twelve_healers",
        "12 Healers",
        "The deliberately ridiculous Godslayer experiment.",
        _HEALERS,
    ),
    MockRosterScenario(
        "twelve_dds",
        "12 DDs",
        "Maximum damage-shaped chaos with almost no support coverage.",
        _DDS,
    ),
    MockRosterScenario(
        "no_tanks",
        "No Tanks",
        "A balanced roster with the tank providers removed.",
        tuple(p for p in _BALANCED if p.role != Role.TANK),
    ),
    MockRosterScenario(
        "no_healers",
        "No Healers",
        "A balanced roster with healer providers removed.",
        tuple(p for p in _BALANCED if p.role != Role.HEALER),
    ),
    MockRosterScenario(
        "minimal",
        "Minimal Coverage",
        "One provider for each required capability.",
        (
            MockPlayer("Tank 01", Role.TANK, ("major_breach", "major_protection")),
            MockPlayer("Healer 01", Role.HEALER, ("major_courage", "major_sorcery")),
            MockPlayer("Healer 02", Role.HEALER, ("minor_brittle",)),
            MockPlayer("DD 01", Role.DD, ("major_force",)),
        ),
    ),
    MockRosterScenario(
        "overcovered",
        "Overcovered",
        "Several providers cover the same unique effects, exercising redundancy.",
        tuple(
            MockPlayer(f"Healer {index:02d}", Role.HEALER, ("major_courage", "major_sorcery"))
            for index in range(1, 5)
        ),
    ),
    MockRosterScenario(
        "bad_uptime",
        "Bad Uptime",
        "Providers exist, but every provider is below the 80% uptime requirement.",
        tuple(
            MockPlayer(f"Healer {index:02d}", Role.HEALER, ("major_courage",), uptime=0.79)
            for index in range(1, 3)
        ),
    ),
    MockRosterScenario(
        "single_point",
        "Single Point of Failure",
        "One provider carries each capability, making the roster fragile.",
        (
            MockPlayer("Tank 01", Role.TANK, ("major_breach", "major_protection")),
            MockPlayer("Healer 01", Role.HEALER, ("major_courage", "major_sorcery", "minor_brittle")),
            MockPlayer("DD 01", Role.DD, ("major_force",)),
        ),
    ),
    MockRosterScenario(
        "conflict",
        "Conflict Roster",
        "Two satisfying providers deliberately share an exclusivity group.",
        (
            MockPlayer("Healer 01", Role.HEALER, ("major_courage",), exclusivity_groups=("major_courage",)),
            MockPlayer("Healer 02", Role.HEALER, ("major_courage",), exclusivity_groups=("major_courage",)),
        ),
    ),
    MockRosterScenario(
        "conditional",
        "Conditional",
        "Baseline roster used for future phase/condition experiments.",
        _BALANCED,
    ),
    MockRosterScenario(
        "resilience_candidate",
        "Redundancy / Resilience Candidate",
        "Intentionally exposes the current distinction: the evaluator needs explicit resilience evidence; extra unique providers currently classify as REDUNDANT.",
        (
            MockPlayer("Healer 01", Role.HEALER, ("major_courage",)),
            MockPlayer("Healer 02", Role.HEALER, ("major_courage",)),
        ),
    ),
)
