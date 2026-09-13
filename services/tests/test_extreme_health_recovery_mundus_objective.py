import pytest

from minmax.mundus_repository import MundusRepository, U50_GAME_UPDATE
from services.extreme_mundus_objective_service import ExtremeMundusObjectiveService


def test_steed_projects_health_recovery_in_extreme_objective_units(tmp_path):
    repository = MundusRepository(tmp_path / "u50.db", game_update=U50_GAME_UPDATE)

    best = ExtremeMundusObjectiveService.best_for_objective(
        repository,
        "health_recovery",
    )

    assert best is not None
    assert best.mundus_name == "The Steed"
    assert best.projected_delta == pytest.approx(238.0)
    assert best.unresolved == ()


def test_health_recovery_mundus_accepts_divines_multiplier(tmp_path):
    repository = MundusRepository(tmp_path / "u50.db", game_update=U50_GAME_UPDATE)

    steed = ExtremeMundusObjectiveService.candidate_for_name(
        repository,
        "The Steed",
        "health_recovery",
        multiplier=1.728,
    )

    assert steed.projected_delta == pytest.approx(238.0 * 1.728)
