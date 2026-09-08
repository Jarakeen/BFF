from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services import extreme_actual_heal_optimization_service as module
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_actual_heal_reviewed_bar_candidate_service import (
    ExtremeActualHealReviewedBarCandidateService,
)


class _Event:
    def __init__(self, entity_id: str, critical_heal: float):
        self.entity_id = entity_id
        self.critical_heal = critical_heal
        self.normal_heal = critical_heal / 1.5
        self.unresolved = ()
        self.mechanic_complete = True


class _SoulSiphonerHealingEvents:
    def evaluate(self, *, build, context, entity_id):
        _ = context
        siphoning_count = sum(
            name in {"Funnel Health", "Siphoning Attacks"}
            for name in build.FrontBarSkills[:5]
        )
        return _Event(
            entity_id,
            100.0 + float(build.AttributeMagicka or 0) + 10.0 * siphoning_count,
        )


class _ContextFactory:
    def build(self, **kwargs):
        _ = kwargs
        return SimpleNamespace(unresolved_gear_effects=())


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = _ContextFactory()

    @staticmethod
    def objective(key):
        return SimpleNamespace(key=key)

    @staticmethod
    def _candidates(*args, **kwargs):
        _ = args, kwargs
        return ()


def _records():
    return [
        {
            "ability_id": 701,
            "base_ability_id": 700,
            "name": "Combat Prayer",
            "skill_line": "Restoration Staff",
            "class_type": "Weapon",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
        {
            "ability_id": 801,
            "base_ability_id": 800,
            "name": "Funnel Health",
            "skill_line": "Siphoning",
            "class_type": "Nightblade",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
        {
            "ability_id": 901,
            "base_ability_id": 900,
            "name": "Siphoning Attacks",
            "skill_line": "Siphoning",
            "class_type": "Nightblade",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
    ]


def _install_progression_adapter(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            owned_skill_lines=("siphoning",),
            passive_ranks={"Soul Siphoner": 2},
            passive_cp_points={},
        ),
        unresolved=(),
    )

    class _Adapter:
        def __init__(self, catalog):
            _ = catalog

        def resolve(self, build):
            _ = build
            return resolution

    monkeypatch.setattr(module, "MinmaxCharacterProgressionAdapter", _Adapter)


def test_actual_heal_optimizer_can_add_siphoning_carriers_for_soul_siphoner(monkeypatch):
    _install_progression_adapter(monkeypatch)
    reviewed_bar = ExtremeActualHealReviewedBarCandidateService(
        "fake.db",
        skill_loader=lambda _path: _records(),
    )
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_SoulSiphonerHealingEvents(),
        reviewed_bar_candidates=reviewed_bar,
    )
    baseline = PlayerBuild(
        BuildName="Soul Siphoner Search",
        EsoClass="nightblade",
        FrontBarSkills=[
            "Old One",
            "Old Two",
            "Combat Prayer",
            "Old Four",
            "Old Five",
            "Aggressive Horn",
        ],
    )

    result = service.optimize(
        baseline,
        "combat_prayer",
        max_passes=4,
    )

    assert result.optimized_build.AttributeMagicka == 64
    assert result.optimized_build.FrontBarSkills[2] == "Combat Prayer"
    assert "Funnel Health" in result.optimized_build.FrontBarSkills[:5]
    assert "Siphoning Attacks" in result.optimized_build.FrontBarSkills[:5]
    assert result.optimized_build.FrontBarSkills[5] == "Aggressive Horn"
    assert result.optimized_event.critical_heal == 184.0
    assert sum(
        step.after.get("reviewed_passive") == "Soul Siphoner"
        for step in result.steps
        if isinstance(step.after, dict)
    ) >= 2
