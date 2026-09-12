from minmax.resource_costs import ResourceType
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _Combo:
    def __init__(self, value) -> None:
        self.value = value

    def currentData(self):
        return self.value


class _Spin:
    def __init__(self, value: float) -> None:
        self._value = value

    def value(self) -> float:
        return self._value


class _Page:
    def __init__(self, *, resource, trigger_percent: float) -> None:
        self.rotation_recovery_resource_combo = _Combo(resource)
        self.rotation_recovery_trigger_spin = _Spin(trigger_percent)


def test_unset_recovery_controls_remain_explicitly_unresolved() -> None:
    page = _Page(resource=None, trigger_percent=-1.0)

    policy = CanonicalRotationDashboardPage.canonical_recovery_policy(page)

    assert policy == {
        "resource": None,
        "trigger_fraction": None,
    }


def test_recovery_controls_return_exact_selected_resource_and_fraction() -> None:
    page = _Page(resource=ResourceType.MAGICKA, trigger_percent=35.0)

    policy = CanonicalRotationDashboardPage.canonical_recovery_policy(page)

    assert policy == {
        "resource": ResourceType.MAGICKA,
        "trigger_fraction": 0.35,
    }
