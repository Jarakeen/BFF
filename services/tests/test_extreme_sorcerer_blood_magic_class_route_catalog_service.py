from pathlib import Path
from types import SimpleNamespace

from minmax.character_build.character_class import CharacterClass
from models.build_model import PlayerBuild
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogService,
)
from services.extreme_sorcerer_blood_magic_trigger_candidate_service import (
    ExtremeSorcererBloodMagicTriggerCandidate,
)


class _BloodMagic:
    def __init__(self) -> None:
        self.optimizer = SimpleNamespace(database_path=Path("fake.db"))
        self.calls = []

    def optimize(
        self,
        build,
        *,
        active_bar="front",
        max_passes=24,
        progression_override=None,
    ):
        self.calls.append((build, active_bar, max_passes, progression_override))
        return SimpleNamespace(
            optimized_event=SimpleNamespace(normal_heal=4321.0, can_crit=False),
            mechanic_complete=True,
            unresolved=(),
        )


class _Triggers:
    def candidates(self):
        return (
            ExtremeSorcererBloodMagicTriggerCandidate(
                name="Dark Exchange",
                ability_id=1,
                skill_rank_id=2,
                rank=4,
                morph=0,
                base_cost=3000.0,
                base_mechanic=0,
                skill_line="Dark Magic",
            ),
        )


class _Routes:
    def __init__(self):
        self.dark = SimpleNamespace(
            base_class=CharacterClass.SORCERER,
            equipped_skill_lines=("dark_magic", "daedric_summoning", "storm_calling"),
        )
        self.no_dark = SimpleNamespace(
            base_class=CharacterClass.SORCERER,
            equipped_skill_lines=("daedric_summoning", "storm_calling", "green_balance"),
        )

    def routes_for_base_class(self, _base_class):
        return (self.no_dark, self.dark)

    @staticmethod
    def materialize_build(build, route):
        result = PlayerBuild.from_dict(build.to_dict())
        result.ClassSkillLines = list(route.equipped_skill_lines)
        return result


class _Normalizer:
    def __init__(self, progression):
        self.progression = progression
        self.calls = []

    def normalize(self, progression, route):
        self.calls.append((progression, route))
        return self.progression


class _Catalog(ExtremeSorcererBloodMagicClassRouteCatalogService):
    def __init__(self, *, baseline_progression, **kwargs):
        self._baseline_progression = baseline_progression
        super().__init__(**kwargs)

    def _progression(self, build):
        return self._baseline_progression


def _build():
    return PlayerBuild(Name="Test", BuildName="Route", EsoClass="sorcerer")


def test_route_catalog_requires_dark_magic_and_preserves_route_progression(tmp_path):
    baseline_progression = object()
    route_progression = object()
    blood_magic = _BloodMagic()
    routes = _Routes()
    normalizer = _Normalizer(route_progression)
    service = _Catalog(
        baseline_progression=baseline_progression,
        database_path=tmp_path / "eso.db",
        blood_magic=blood_magic,
        triggers=_Triggers(),
        routes=routes,
        progression_normalizer=normalizer,
    )

    result = service.rank(_build(), active_bar="back", max_passes=7)

    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.route is routes.dark
    assert entry.trigger.name == "Dark Exchange"
    assert entry.normal_heal == 4321.0
    assert entry.mechanic_complete is True
    assert entry.slotted_index == 0
    assert entry.candidate_build.BackBarSkills[0] == "Dark Exchange"
    assert result.best_scored is entry
    assert result.best_complete is entry
    assert len(blood_magic.calls) == 5
    assert all(call[1:] == ("back", 7, route_progression) for call in blood_magic.calls)
    assert normalizer.calls == [(baseline_progression, routes.dark)]


def test_route_catalog_resolves_blood_magic_noncritical_policy_but_keeps_global_merge_omitted(tmp_path):
    service = _Catalog(
        baseline_progression=object(),
        database_path=tmp_path / "eso.db",
        blood_magic=_BloodMagic(),
        triggers=_Triggers(),
        routes=_Routes(),
        progression_normalizer=_Normalizer(object()),
    )

    result = service.rank(_build())

    assert "Blood Magic critical-heal eligibility" not in result.omitted_scope
    assert "Blood Magic Max-Health passive-proc critical policy: non-critical" in result.search_scope
    assert "global maximum-event comparison against ordinary-heal candidates" in result.omitted_scope
