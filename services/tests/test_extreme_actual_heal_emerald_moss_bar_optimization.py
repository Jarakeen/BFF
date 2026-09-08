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


class _EmeraldMossHealingEvents:
    def evaluate(self, *, build, context, entity_id):
        _ = context
        green_balance_count = sum(
            name in {"Budding Seeds", "Fungal Growth"}
            for name in build.FrontBarSkills[:5]
        )
        return _Event(
            entity_id,
            100.0 + float(build.AttributeMagicka or 0) + 10.0 * green_balance_count,
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
            "ability_id": 501,
            "base_ability_id": 500,
            "name": "Budding Seeds",
            "skill_line": "Green Balance",
            "class_type": "Warden",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 1,
        },
        {
            "ability_id": 601,
            "base_ability_id": 600,
            "name": "Fungal Growth",
            "skill_line": "Green Balance",
            "class_type": "Warden",
            "is_player": 1,
            "is_passive": 0,
            "base_mechanic": 0,
            "morph": 0,
        },
    ]


def _install_progression_adapter(monkeypatch):
    resolution = SimpleNamespace(
        resolved=True,
        character_id="char-1",
        progression=CharacterProgression(
            attributes=AttributeAllocation(),
            owned_skill_lines=("green_balance",),
            passive_ranks={"Emerald Moss": 2},
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


def test_actual_heal_optimizer_can_add_green_balance_carrier_for_emerald_moss(monkeypatch):
    _install_progression_adapter(monkeypatch)
    reviewed_bar = ExtremeActualHealReviewedBarCandidateService(
        "fake.db",
        skill_loader=lambda _path: _records(),
    )
    service = ExtremeActualHealOptimizationService(
        optimizer=_Optimizer(),
        healing_events=_EmeraldMossHealingEvents(),
        reviewed_bar_candidates=reviewed_bar,
    )
    baseline = PlayerBuild(
        BuildName="Emerald Moss Search",
        FrontBarSkills=[
            "Old One",
            "Old Two",
            "Budding Seeds",
            "Old Four",
            "Old Five",
            "Aggressive Horn",
        ],
    )

    result = service.optimize(
        baseline,
        "budding_seeds",
        max_passes=4,
    )

    assert result.optimized_build.AttributeMagicka == 64
    assert result.optimized_build.FrontBarSkills[2] == "Budding Seeds"
    assert "Fungal Growth" in result.optimized_build.FrontBarSkills[:5]
    assert result.optimized_build.FrontBarSkills[5] == "Aggressive Horn"
    assert result.optimized_event.critical_heal == 184.0
    assert any(
        step.after.get("reviewed_passive") == "Emerald Moss"
        for step in result.steps
        if isinstance(step.after, dict)
    )
