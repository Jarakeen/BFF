from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
    _SimulationTemporalSkillProvider,
)
from services.minmax_character_progression_adapter import (
    SavedBuildProgressionResolution,
)
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationWeaponAttackBuildEvaluationResolution,
)
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
)


class _StaticContextService:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return self.resolution


class _WeaponEvaluationService:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve(self, *, player_build, static_context):
        self.calls.append((player_build, static_context))
        return self.resolution


def _progression(*, unresolved=()):
    return SavedBuildProgressionResolution(
        character_id="character-1",
        progression=CharacterProgression(
            passive_ranks={},
            passive_cp_points={},
        ),
        unresolved=tuple(unresolved),
    )


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=10.0,
        actions=(),
    )


def test_saved_build_dd_provider_rejects_non_dd_role_before_context_resolution() -> None:
    static = _StaticContextService(
        RotationStaticBuildContextResolution(
            progression=_progression(),
            contexts=(SimpleNamespace(active_bar="front"),),
        )
    )
    service = CombatSimulationSavedBuildDDProviderService(
        database_path="unused.db",
        static_context_service=static,
        weapon_evaluation_service=_WeaponEvaluationService(
            RotationWeaponAttackBuildEvaluationResolution(build=None)
        ),
    )

    result = service.resolve(
        player_build=PlayerBuild(
            Name="Healer",
            BuildName="Heal",
            Role="Healer",
        ),
        plan=_plan(),
        target_resistance=18200.0,
    )

    assert result.provider is None
    assert "damage-dealer build" in result.unresolved[0]
    assert static.calls == []


def test_saved_build_dd_provider_fails_closed_on_relevant_static_context_gap() -> None:
    static = _StaticContextService(
        RotationStaticBuildContextResolution(
            progression=_progression(),
            contexts=(SimpleNamespace(active_bar="front"),),
            unresolved=("front static context: offensive mechanic unresolved",),
        )
    )
    service = CombatSimulationSavedBuildDDProviderService(
        database_path="unused.db",
        static_context_service=static,
        weapon_evaluation_service=_WeaponEvaluationService(
            RotationWeaponAttackBuildEvaluationResolution(build=None)
        ),
    )

    result = service.resolve(
        player_build=PlayerBuild(
            Name="Damage Tester",
            BuildName="DD Build",
            Role="DD",
        ),
        plan=_plan(),
        target_resistance=18200.0,
    )

    assert result.provider is None
    assert result.unresolved == (
        "front static context: offensive mechanic unresolved",
    )


def test_saved_build_dd_provider_allows_reviewed_ambient_static_context_gap() -> None:
    static_resolution = RotationStaticBuildContextResolution(
        progression=_progression(),
        contexts=(SimpleNamespace(active_bar="front"),),
        unresolved=("front static context: movement_speed unresolved",),
    )
    weapon = _WeaponEvaluationService(
        RotationWeaponAttackBuildEvaluationResolution(
            build=None,
            unresolved=("weapon evidence unavailable in fixture",),
        )
    )
    service = CombatSimulationSavedBuildDDProviderService(
        database_path="unused.db",
        static_context_service=_StaticContextService(static_resolution),
        weapon_evaluation_service=weapon,
    )

    result = service.resolve(
        player_build=PlayerBuild(
            Name="Damage Tester",
            BuildName="DD Build",
            Role="DD",
        ),
        plan=_plan(),
        target_resistance=18200.0,
    )

    assert result.provider is not None
    assert result.unresolved == ()
    assert result.static_context is not None
    assert result.static_context.unresolved == ()
    assert len(weapon.calls) == 1



class _PeriodicTimingService:
    def __init__(self, entries):
        self.entries = tuple(entries)

    def inspect_action(self, action):
        return SimpleNamespace(entries=self.entries)


class _SkillDamageDelegate:
    def __init__(self):
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        return __import__(
            "services.rotation_candidate_dd_role_output_service",
            fromlist=["RotationActionDamageEvidence"],
        ).RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=12345.0,
        )


def test_simulation_temporal_skill_provider_blocks_periodic_whole_plan_totals() -> None:
    action = __import__(
        "minmax.rotation_plan",
        fromlist=["RotationAction", "RotationActionKind"],
    ).RotationAction(
        time_seconds=1.0,
        sequence=0,
        kind=__import__(
            "minmax.rotation_plan",
            fromlist=["RotationActionKind"],
        ).RotationActionKind.SKILL,
        name="Damage Over Time",
        bar="front",
    )
    delegate = _SkillDamageDelegate()
    provider = _SimulationTemporalSkillProvider(
        delegate=delegate,
        timing_service=_PeriodicTimingService((object(),)),
    )
    candidate = __import__(
        "services.rotation_candidate_generation_service",
        fromlist=["GeneratedRotationCandidate"],
    ).GeneratedRotationCandidate(
        candidate_id="periodic",
        plan=__import__(
            "minmax.rotation_plan",
            fromlist=["RotationPlan"],
        ).RotationPlan(
            character_name="Damage Tester",
            build_name="DD Build",
            duration_seconds=5.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )

    result = provider.evaluate_action(candidate=candidate, action=action)

    assert result.damage_value is None
    assert "occurrence-level tick damage" in result.unresolved[0]
    assert delegate.calls == []


def test_simulation_temporal_skill_provider_allows_nonperiodic_damage() -> None:
    action = __import__(
        "minmax.rotation_plan",
        fromlist=["RotationAction", "RotationActionKind"],
    ).RotationAction(
        time_seconds=1.0,
        sequence=0,
        kind=__import__(
            "minmax.rotation_plan",
            fromlist=["RotationActionKind"],
        ).RotationActionKind.SKILL,
        name="Direct Hit",
        bar="front",
    )
    delegate = _SkillDamageDelegate()
    provider = _SimulationTemporalSkillProvider(
        delegate=delegate,
        timing_service=_PeriodicTimingService(()),
    )
    candidate = __import__(
        "services.rotation_candidate_generation_service",
        fromlist=["GeneratedRotationCandidate"],
    ).GeneratedRotationCandidate(
        candidate_id="direct",
        plan=__import__(
            "minmax.rotation_plan",
            fromlist=["RotationPlan"],
        ).RotationPlan(
            character_name="Damage Tester",
            build_name="DD Build",
            duration_seconds=5.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )

    result = provider.evaluate_action(candidate=candidate, action=action)

    assert result.damage_value == 12345.0
    assert result.unresolved == ()
    assert len(delegate.calls) == 1
