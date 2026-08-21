import pytest

from minmax.formulas.math_utils import fround


def test_fround_uses_single_precision():
    assert fround(0.016) == pytest.approx(0.01600000075995922)
    assert fround(0.168) == pytest.approx(0.1679999977350235)
    assert fround(0.4725) == pytest.approx(0.4724999964237213)


def test_fround_preserves_exact_binary32_values():
    assert fround(0.0) == 0.0
    assert fround(1.0) == 1.0
    assert fround(0.5) == 0.5


def test_fround_handles_negative_values():
    assert fround(-0.168) == pytest.approx(-0.1679999977350235)