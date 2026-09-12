from __future__ import annotations

from types import MethodType

from PySide6.QtWidgets import QDoubleSpinBox


class RotationDDEvaluationPolicyControls:
    """Install explicit DD target-state inputs used by canonical rotation scoring.

    Target resistance is evaluation evidence. It is deliberately not inferred from
    encounter identity, content type, difficulty, or common trial conventions.
    An unset value therefore remains unknown instead of becoming zero mitigation.
    """

    def install(self, page) -> None:
        page.rotation_dd_target_resistance_spin = QDoubleSpinBox()
        page.rotation_dd_target_resistance_spin.setRange(-1.0, 100_000.0)
        page.rotation_dd_target_resistance_spin.setDecimals(0)
        page.rotation_dd_target_resistance_spin.setSingleStep(500.0)
        page.rotation_dd_target_resistance_spin.setSpecialValueText("Not set")
        page.rotation_dd_target_resistance_spin.setValue(-1.0)
        page.rotation_dd_target_resistance_spin.setSuffix(" armor")
        page.rotation_dd_target_resistance_spin.setMinimumWidth(135)
        page.rotation_dd_target_resistance_spin.setToolTip(
            "Explicit target resistance used by canonical DD rotation damage. "
            "No resistance is inferred from encounter or content type."
        )

        page.header.add_context_widget(
            page._context_field("TARGET RESIST", page.rotation_dd_target_resistance_spin)
        )
        page.canonical_dd_evaluation_policy = MethodType(
            lambda bound_page: self.policy(bound_page),
            page,
        )

    @staticmethod
    def policy(page) -> dict[str, object | None]:
        resistance = float(page.rotation_dd_target_resistance_spin.value())
        return {
            "target_resistance": None if resistance < 0.0 else resistance,
        }


def install_rotation_dd_evaluation_policy_controls(
    page,
) -> RotationDDEvaluationPolicyControls:
    support = RotationDDEvaluationPolicyControls()
    support.install(page)
    return support


__all__ = [
    "RotationDDEvaluationPolicyControls",
    "install_rotation_dd_evaluation_policy_controls",
]
