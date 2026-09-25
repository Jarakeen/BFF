from __future__ import annotations

from types import SimpleNamespace

import pytest
from minmax.gear_set_repository import GearSetRepository
from minmax.race_repository import RaceRepository

from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_offensive_stats_service import (
    CRITICAL_DAMAGE_CAP,
    PVE_TARGET_RESISTANCE,
    RaidPlanOffensiveStatsService,
)


class _Trace:
    def __init__(self, value: float, label: str) -> None:
        self.final_value = value
        self.steps = [
            ("base", "set", value, value),
            (label, "add", 0.0, value),
            ("ESO ratio" if value < 2 else "ESO rounding", "retain", value, value),
        ]


class _ContextFactory:
    def __init__(self, by_build_id: dict[str, tuple[float, float, float]]) -> None:
        self.by_build_id = by_build_id

    def build(self, *, build_id: str, **_kwargs):
        crit, physical, spell = self.by_build_id[build_id]
        return SimpleNamespace(
            core_state=SimpleNamespace(
                derived={
                    StatId.CRITICAL_DAMAGE: _Trace(crit, "Personal crit source"),
                    StatId.PHYSICAL_PENETRATION: _Trace(physical, "Physical pen source"),
                    StatId.SPELL_PENETRATION: _Trace(spell, "Spell pen source"),
                }
            ),
            unresolved_gear_effects=(),
        )


class _Progression:
    def resolve(self, build):
        return SimpleNamespace(
            character_id=build.CharacterId or build.BuildId,
            progression=SimpleNamespace(),
            unresolved=(),
        )


class _CapabilityService:
    def audit_build(self, _build):
        return SimpleNamespace(
            resolved_effects=(),
            capability_unresolved=(),
        )


class _Resolver:
    def __init__(self, builds: dict[str, PlayerBuild]) -> None:
        self.builds = builds

    def resolve(self, *, seat_id: str, **_kwargs):
        build = self.builds.get(seat_id)
        if build is None:
            return SimpleNamespace(resolved=False, build=None, unresolved=("missing build",))
        return SimpleNamespace(resolved=True, build=build, unresolved=())


class _BuildService:
    def __init__(self, builds: tuple[PlayerBuild, ...]) -> None:
        self._builds = builds
        self.canonical = SimpleNamespace(catalog_service=SimpleNamespace())

    def load(self):
        return SimpleNamespace(Members=list(self._builds))


def _build(
    *,
    build_id: str,
    name: str,
    eso_class: str,
    set_name: str = "",
) -> PlayerBuild:
    build = PlayerBuild(
        Name=name,
        Gamertag=name,
        BuildName=f"{name} Build",
        EsoClass=eso_class,
        BuildId=build_id,
        CharacterId=f"character-{build_id}",
    )
    if set_name:
        build.Armor["Head"]["Set"] = set_name
        build.Armor["Head"]["Weight"] = "Heavy"
    return build


def _service(builds: tuple[PlayerBuild, ...]) -> RaidPlanOffensiveStatsService:
    by_seat = {
        "tank-1": builds[0],
        "dd-1": builds[1],
    }
    service = RaidPlanOffensiveStatsService(
        build_service=_BuildService(builds),
        context_factory=_ContextFactory(
            {
                builds[0].BuildId: (0.80, 3000.0, 4000.0),
                builds[1].BuildId: (0.80, 3000.0, 4000.0),
            }
        ),
        capability_service=_CapabilityService(),
        resolver=_Resolver(by_seat),
    )
    service.progression = _Progression()
    return service


def test_default_offensive_context_uses_repositories_instead_of_a_path(tmp_path) -> None:
    service = RaidPlanOffensiveStatsService(
        database_path=tmp_path / "eso.db",
        build_service=_BuildService(()),
        capability_service=_CapabilityService(),
    )

    assert isinstance(service.context_factory.race_repository, RaceRepository)
    assert isinstance(service.context_factory.gear_resolver.repository, GearSetRepository)


def test_raid_plan_crit_and_pen_layers_group_effects_without_double_owning_them() -> None:
    lucent = _build(
        build_id="lucent",
        name="Lucent Tank",
        eso_class="Dragonknight",
        set_name="Lucent Echoes",
    )
    dd = _build(
        build_id="dd",
        name="DD",
        eso_class="Arcanist",
    )
    plan = RaidPlan(
        plan_id="plan",
        trial_id="sunspire",
        name="Performance Mode GS",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Lucent Tank",
                role="Tank",
                eso_class="Dragonknight",
                selected_build_id="lucent",
                selected_build_name="Lucent Tank Build",
                planned_skills=("Aggressive Horn",),
                primary_assignment="Minor Brittle",
                secondary_assignment="Major Breach",
                utility_assignments=("Minor Breach",),
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="DD",
                role="DD",
                eso_class="Arcanist",
                selected_build_id="dd",
                selected_build_name="DD Build",
            ),
        ),
    )

    result = _service((lucent, dd)).calculate(plan)

    assert result.target_resistance == PVE_TARGET_RESISTANCE
    assert result.raid_armor_reduction == pytest.approx(5948 + 2974)

    tank = next(row for row in result.rows if row.seat_id == "tank-1")
    damage = next(row for row in result.rows if row.seat_id == "dd-1")

    # Both receive Major Force and target Minor Brittle; Lucent excludes its wearer.
    assert tank.personal_critical_damage == pytest.approx(0.80)
    assert tank.raid_critical_damage == pytest.approx(1.10)
    assert damage.personal_critical_damage == pytest.approx(0.80)
    assert damage.raid_critical_damage == pytest.approx(1.21)

    assert damage.physical_penetration == pytest.approx(3000)
    assert damage.spell_penetration == pytest.approx(4000)
    assert damage.effective_physical_penetration == pytest.approx(11922)
    assert damage.effective_spell_penetration == pytest.approx(12922)
    assert damage.physical_overpenetration == pytest.approx(-6278)
    assert damage.spell_overpenetration == pytest.approx(-5278)

    labels = {row.label for row in damage.contributions}
    assert "Lucent Echoes (group member)" in labels
    assert "Major Force" in labels
    assert "Minor Brittle" in labels


def test_raid_plan_crit_damage_caps_at_125_percent() -> None:
    lucent = _build(
        build_id="lucent",
        name="Lucent Tank",
        eso_class="Dragonknight",
        set_name="Lucent Echoes",
    )
    dd = _build(build_id="dd", name="DD", eso_class="Arcanist")
    service = _service((lucent, dd))
    service.context_factory = _ContextFactory(
        {
            "lucent": (1.10, 0.0, 0.0),
            "dd": (1.10, 0.0, 0.0),
        }
    )
    plan = RaidPlan(
        plan_id="plan",
        trial_id="sunspire",
        name="Cap Test",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Lucent Tank",
                selected_build_id="lucent",
                selected_build_name="Lucent Tank Build",
                planned_skills=("Aggressive Horn",),
                primary_assignment="Minor Brittle",
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="DD",
                selected_build_id="dd",
                selected_build_name="DD Build",
            ),
        ),
    )

    result = service.calculate(plan)
    row = next(item for item in result.rows if item.seat_id == "dd-1")

    assert row.raid_critical_damage == pytest.approx(CRITICAL_DAMAGE_CAP)
    assert row.critical_capped is True


def test_unresolved_seat_stays_visible_instead_of_inventing_zero_stats() -> None:
    lucent = _build(build_id="lucent", name="Lucent Tank", eso_class="Dragonknight")
    dd = _build(build_id="dd", name="DD", eso_class="Arcanist")
    service = _service((lucent, dd))
    plan = RaidPlan(
        plan_id="plan",
        trial_id="sunspire",
        name="Missing Build",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Recruitment Needed",
                role="Healer",
            ),
        ),
    )

    result = service.calculate(plan)
    row = result.rows[0]

    assert row.resolved is False
    assert row.personal_critical_damage is None
    assert row.physical_penetration is None
    assert row.unresolved
