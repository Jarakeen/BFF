from ui.build_screenshot_import_disable_support import disable_screenshot_import_control


class _Button:
    def __init__(self) -> None:
        self.enabled = True
        self.visible = True
        self.tooltip = ""

    def setEnabled(self, value: bool) -> None:
        self.enabled = bool(value)

    def setVisible(self, value: bool) -> None:
        self.visible = bool(value)

    def setToolTip(self, value: str) -> None:
        self.tooltip = str(value)


class _Page:
    def __init__(self, button=None) -> None:
        if button is not None:
            self.import_screenshots_button = button


def test_screenshot_import_control_is_hidden_and_disabled_when_present() -> None:
    button = _Button()
    page = _Page(button)

    assert disable_screenshot_import_control(page) is True
    assert button.enabled is False
    assert button.visible is False
    assert "temporarily disabled" in button.tooltip.casefold()


def test_screenshot_import_disable_is_safe_when_control_is_absent() -> None:
    assert disable_screenshot_import_control(_Page()) is False
