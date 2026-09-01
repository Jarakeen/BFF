from __future__ import annotations

from models.build_model import PlayerBuild
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.static_build_inputs import StaticBuildInputResolver


def test_selected_potion_remains_outside_static_active_state():
    build = PlayerBuild(Potion="spell power")

    result = StaticBuildInputResolver().apply(GearCalculationInputs(), build)

    assert result.unresolved == (
        "Potion selected; activation/uptime is not part of static build state: spell power",
    )


def test_empty_potion_does_not_add_unresolved_noise():
    result = StaticBuildInputResolver().apply(GearCalculationInputs(), PlayerBuild())

    assert result.unresolved == ()
