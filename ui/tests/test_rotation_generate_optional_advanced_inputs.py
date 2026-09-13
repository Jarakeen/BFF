from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generate_action_support import RotationGenerateActionSupport


class _Status:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class RotationGenerateApplicationContextProvider:
    """Name intentionally matches the production live application provider."""

    def __init__(self) -> None:
        self.calls = 0

    def context_for(self, _page):
        self.calls += 1
        raise AssertionError("advanced provider should not run when opt-in inputs are incomplete")


class _Page:
    def __init__(
        self,
        *,
        role: str = "DD",
        resource=None,
        trigger_fraction=None,
        target_resistance=None,
    ) -> None:
        self.rotation_generate_canonical_context = None
        self.rotation_generate_canonical_context_provider = (
            RotationGenerateApplicationContextProvider()
        )
        self.status = _Status()
        self.build = SimpleNamespace(Role=role)
        self.resource = resource
        self.trigger_fraction = trigger_fraction
        self.target_resistance = target_resistance

    def _selected_build(self):
        return self.build

    def canonical_recovery_policy(self):
        return {
            "resource": self.resource,
            "trigger_fraction": self.trigger_fraction,
        }

    def canonical_dd_evaluation_policy(self):
        return {"target_resistance": self.target_resistance}


def test_generate_uses_baseline_path_when_recovery_policy_is_unset(monkeypatch) -> None:
    support = RotationGenerateActionSupport()
    page = _Page(resource=None, trigger_fraction=None, target_resistance=None)
    plain_calls = []

    monkeypatch.setattr(
        RotationDashboardPage,
        "generate_rotation",
        lambda supplied_page: plain_calls.append(supplied_page),
    )

    support.generate(page)

    assert plain_calls == [page]
    assert page.rotation_generate_canonical_context_provider.calls == 0
    assert page.status.warnings == []


def test_generate_uses_baseline_path_when_dd_target_resistance_is_unset(monkeypatch) -> None:
    support = RotationGenerateActionSupport()
    page = _Page(
        resource=ResourceType.MAGICKA,
        trigger_fraction=0.35,
        target_resistance=None,
    )
    plain_calls = []

    monkeypatch.setattr(
        RotationDashboardPage,
        "generate_rotation",
        lambda supplied_page: plain_calls.append(supplied_page),
    )

    support.generate(page)

    assert plain_calls == [page]
    assert page.rotation_generate_canonical_context_provider.calls == 0
    assert page.status.warnings == []


def test_complete_dd_advanced_policy_opts_into_canonical_provider() -> None:
    page = _Page(
        resource=ResourceType.STAMINA,
        trigger_fraction=0.30,
        target_resistance=18200.0,
    )

    assert RotationGenerateActionSupport._advanced_application_context_ready(
        page,
        page.rotation_generate_canonical_context_provider,
    ) is True


def test_healer_does_not_require_dd_target_resistance_for_advanced_opt_in() -> None:
    page = _Page(
        role="Healer",
        resource=ResourceType.MAGICKA,
        trigger_fraction=0.35,
        target_resistance=None,
    )

    assert RotationGenerateActionSupport._advanced_application_context_ready(
        page,
        page.rotation_generate_canonical_context_provider,
    ) is True
