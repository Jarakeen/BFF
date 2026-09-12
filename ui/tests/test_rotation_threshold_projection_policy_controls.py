from ui.rotation_threshold_projection_policy_controls import (
    RotationThresholdProjectionPolicyControls,
)


class _Combo:
    def __init__(self, value) -> None:
        self.value = value

    def currentData(self):
        return self.value


class _Spin:
    def __init__(self, value) -> None:
        self._value = value

    def value(self):
        return self._value


class _Page:
    def __init__(self, *, difficulty=None, raid_dps=0.0) -> None:
        self.rotation_threshold_difficulty_combo = _Combo(difficulty)
        self.rotation_threshold_raid_dps_spin = _Spin(raid_dps)


def test_threshold_projection_policy_preserves_unset_values() -> None:
    assert RotationThresholdProjectionPolicyControls.policy(_Page()) == {
        "difficulty": None,
        "raid_dps": None,
    }


def test_threshold_projection_policy_returns_only_explicit_ui_values() -> None:
    assert RotationThresholdProjectionPolicyControls.policy(
        _Page(difficulty="hardmode", raid_dps=2_000_000.0)
    ) == {
        "difficulty": "hardmode",
        "raid_dps": 2_000_000.0,
    }
