from types import SimpleNamespace

import pytest

from minmax.optimization_mode import OptimizationMode
from ui.optimization_page import OptimizationPage


HYBRID_SOURCE = "Hybrid: Players + Recruitment"


class _FakeTeamSourceCombo:
    def __init__(self, text: str = HYBRID_SOURCE):
        self._text = text
        self.enabled = None

    def currentText(self) -> str:
        return self._text

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


@pytest.mark.parametrize("mode", tuple(OptimizationMode))
def test_team_source_selector_remains_enabled_for_every_mode(mode):
    source_combo = _FakeTeamSourceCombo()
    page = SimpleNamespace(
        team_source_combo=source_combo,
        _current_mode=lambda: mode,
    )

    OptimizationPage._optimization_mode_changed(page, 0)

    assert source_combo.enabled is True


@pytest.mark.parametrize("mode", tuple(OptimizationMode))
def test_hybrid_team_source_is_honored_for_every_mode(mode):
    source_combo = _FakeTeamSourceCombo(HYBRID_SOURCE)
    page = SimpleNamespace(
        team_source_combo=source_combo,
        _current_mode=lambda: mode,
    )

    assert OptimizationPage._effective_source_mode(page) == HYBRID_SOURCE
