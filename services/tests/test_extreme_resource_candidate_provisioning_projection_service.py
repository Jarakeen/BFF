from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_resource_candidate_provisioning_projection_service import (
    ExtremeResourceCandidateProvisioningProjection,
    ExtremeResourceCandidateProvisioningProjectionService,
)
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjection,
)
from services.extreme_structural_mundus_food_core_stat_record_service import (
    ExtremeBestMundusFoodStructuralStatEvaluator,
)


class _Repository:
    database_path = "fake.db"

    def __init__(self):
        self.values = {
            "Strong Food": 6000.0,
            "Weaker Drink": 5000.0,
        }

    def resolve(self, name):
        value = self.values[str(name)]
        return (
            (
                Effect(
                    stat=StatId.MAX_MAGICKA,
                    operation=EffectOperation.ADD,
                    value=value,
                    source=f"provisioning:{name}",
                ),
            ),
            (),
        )


class _ProjectionService:
    def build(self, objective_key):
        assert objective_key == "max_magicka"
        return ExtremeResourceProvisioningProjection(
            objective_key="max_magicka",
            choices=("Strong Food", "Weaker Drink"),
            foods_reviewed=2,
            food_witness="Strong Food",
            drink_witness="Weaker Drink",
            denominator_proven=True,
            unresolved=(),
        )


class _RuntimeAuditService:
    def __init__(self, conditional=(), *, proven=True, unresolved=()):
        self.conditional = tuple(conditional)
        self.proven = proven
        self.unresolved = tuple(unresolved)

    def build(self, objective_key):
        assert objective_key == "max_magicka"
        return SimpleNamespace(
            denominator_proven=self.proven,
            unresolved=self.unresolved,
            conditional_gear_effects=self.conditional,
        )


def _realization(*, names=(), counts=()):
    return SimpleNamespace(set_names=tuple(names), counts=tuple(counts))


def _service(runtime_audit):
    return ExtremeResourceCandidateProvisioningProjectionService(
        _Repository(),
        provisioning_projection_service=_ProjectionService(),
        runtime_audit_service=runtime_audit,
    )


def test_ordinary_gear_keeps_only_stronger_static_provisioning_witness() -> None:
    result = _service(_RuntimeAuditService()).build(
        "max_magicka",
        _realization(),
    )

    assert result.projection_complete is True
    assert result.global_choices == ("Strong Food", "Weaker Drink")
    assert result.choices == ("Strong Food",)
    assert result.reduced is True
    assert result.active_kind_conditions == ()


def test_drink_dependent_gear_preserves_both_provisioning_kinds() -> None:
    conditional = (
        SimpleNamespace(
            set_name="Bright-Throat's Boast",
            piece_count=5,
            condition="drink_buff_active",
        ),
    )
    result = _service(_RuntimeAuditService(conditional)).build(
        "max_magicka",
        _realization(names=("Bright-Throat's Boast",), counts=(5,)),
    )

    assert result.projection_complete is True
    assert result.choices == ("Strong Food", "Weaker Drink")
    assert result.reduced is False
    assert result.active_kind_conditions == ("drink_buff_active",)


def test_incomplete_runtime_evidence_falls_back_to_global_frontier() -> None:
    result = _service(
        _RuntimeAuditService(proven=False, unresolved=("runtime gap",))
    ).build(
        "max_magicka",
        _realization(),
    )

    assert result.projection_complete is False
    assert result.choices == ("Strong Food", "Weaker Drink")
    assert result.reduced is False
    assert result.unresolved == ("runtime gap",)


class _FoodRepository:
    def __init__(self, database_path):
        self.database_path = database_path

    def list_names(self):
        return ("Strong Food", "Weaker Drink")

    def resolve(self, _name):
        return (), ()


class _MundusEvaluator:
    def __init__(self):
        self.foods = []

    def evaluate_candidate(self, _objective_key, _candidate, **kwargs):
        food = str(kwargs.get("food") or "")
        self.foods.append(food)
        score = {"Strong Food": 10.0, "Weaker Drink": 9.0}[food]
        return score, {"food": food}, ()


def test_food_evaluator_uses_candidate_specific_projection_choices(tmp_path) -> None:
    database_path = tmp_path / "provisioning.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE entity (name TEXT, entity_type TEXT)")
        connection.executemany(
            "INSERT INTO entity (name, entity_type) VALUES (?, ?)",
            (
                ("Strong Food", "food"),
                ("Weaker Drink", "drink"),
            ),
        )

    mundus = _MundusEvaluator()
    projection = ExtremeResourceCandidateProvisioningProjection(
        objective_key="max_magicka",
        global_choices=("Strong Food", "Weaker Drink"),
        choices=("Strong Food",),
        active_kind_conditions=(),
        denominator_proven=True,
        reduced=True,
        unresolved=(),
    )
    evaluator = ExtremeBestMundusFoodStructuralStatEvaluator(
        mundus_evaluator=mundus,
        provisioning_repository=_FoodRepository(database_path),
        candidate_projection_provider=lambda _key: projection,
    )

    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_magicka",
        SimpleNamespace(),
    )

    assert value == 10.0
    assert payload["food"] == "Strong Food"
    assert unresolved == ()
    assert mundus.foods == ["Strong Food"]
