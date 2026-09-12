from __future__ import annotations

from types import SimpleNamespace

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjectionService,
)
from services.extreme_twice_born_mundus_structural_stat_evaluator import (
    ExtremeTwiceBornMundusStructuralStatEvaluator,
)


def _repository(tmp_path):
    path = tmp_path / "mundus.db"
    return MundusRepository(
        path,
        game_update=U50_GAME_UPDATE,
        initialize=True,
    )


def test_u50_max_magicka_reduces_to_the_mage(tmp_path):
    result = ExtremeResourceMundusProjectionService(_repository(tmp_path)).build(
        "max_magicka"
    )

    assert result.stones_reviewed == 13
    assert result.witness == "The Mage"
    assert result.denominator_proven is True
    assert result.projection_complete is True
    assert result.unresolved == ()


def test_u50_max_stamina_reduces_to_the_tower(tmp_path):
    result = ExtremeResourceMundusProjectionService(_repository(tmp_path)).build(
        "max_stamina"
    )

    assert result.stones_reviewed == 13
    assert result.witness == "The Tower"
    assert result.denominator_proven is True
    assert result.projection_complete is True
    assert result.unresolved == ()


def test_missing_record_evidence_fails_closed_to_no_projection():
    repository = SimpleNamespace(list_names=lambda: ("The Mage", "The Tower"))

    result = ExtremeResourceMundusProjectionService(repository).build("max_magicka")

    assert result.witness is None
    assert result.denominator_proven is False
    assert result.projection_complete is False
    assert result.unresolved


class _Evaluator:
    def evaluate_candidate(self, objective_key, candidate, **kwargs):
        primary = str(kwargs.get("mundus") or "")
        secondary = str(kwargs.get("second_mundus") or "")
        score = 100.0 if primary == "The Mage" else 0.0
        return score, {"mundus": primary, "second_mundus": secondary}, ()


def test_twice_born_max_magicka_uses_same_single_exact_witness(tmp_path):
    evaluator = ExtremeTwiceBornMundusStructuralStatEvaluator(
        evaluator=_Evaluator(),
        mundus_repository=_repository(tmp_path),
    )

    states = evaluator.mundus_states("max_magicka")
    value, payload, unresolved = evaluator.evaluate_candidate(
        "max_magicka",
        SimpleNamespace(),
    )

    assert states == (("The Mage", ""),)
    assert value == 100.0
    assert payload["mundus"] == "The Mage"
    assert payload["second_mundus"] == ""
    assert payload["twice_born_mundus_states_scored"] == 1
    assert unresolved == ()
