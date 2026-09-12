from __future__ import annotations

from types import MethodType

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox


class RotationThresholdProjectionPolicyControls:
    """Install explicit inputs required to project health thresholds onto fight time.

    Difficulty and raid DPS are caller policy/runtime evidence. Neither is inferred from
    the selected encounter, saved build, parse objective, or historical audit defaults.
    The values are consumed only when the selected encounter has reviewed threshold-based
    demand policy.
    """

    def install(self, page) -> None:
        page.rotation_threshold_difficulty_combo = QComboBox()
        page.rotation_threshold_difficulty_combo.setMinimumWidth(120)
        page.rotation_threshold_difficulty_combo.addItem("Select difficulty", None)
        page.rotation_threshold_difficulty_combo.addItem("Normal", "normal")
        page.rotation_threshold_difficulty_combo.addItem("Veteran", "veteran")
        page.rotation_threshold_difficulty_combo.addItem("Hardmode", "hardmode")
        page.rotation_threshold_difficulty_combo.setToolTip(
            "Explicit encounter difficulty used only when reviewed health-threshold "
            "demand policy must be projected onto fight time."
        )

        page.rotation_threshold_raid_dps_spin = QDoubleSpinBox()
        page.rotation_threshold_raid_dps_spin.setRange(0.0, 100_000_000.0)
        page.rotation_threshold_raid_dps_spin.setDecimals(0)
        page.rotation_threshold_raid_dps_spin.setSingleStep(50_000.0)
        page.rotation_threshold_raid_dps_spin.setSpecialValueText("Not set")
        page.rotation_threshold_raid_dps_spin.setValue(0.0)
        page.rotation_threshold_raid_dps_spin.setSuffix(" DPS")
        page.rotation_threshold_raid_dps_spin.setMinimumWidth(145)
        page.rotation_threshold_raid_dps_spin.setToolTip(
            "Explicit constant raid DPS used to project reviewed boss-health thresholds "
            "onto clock time. No DPS is inferred from the selected build or target parse."
        )

        page.header.add_context_widget(
            page._context_field("DIFFICULTY", page.rotation_threshold_difficulty_combo)
        )
        page.header.add_context_widget(
            page._context_field("RAID DPS", page.rotation_threshold_raid_dps_spin)
        )
        page.canonical_threshold_projection_policy = MethodType(
            lambda bound_page: self.policy(bound_page),
            page,
        )

    @staticmethod
    def policy(page) -> dict[str, object | None]:
        raid_dps = float(page.rotation_threshold_raid_dps_spin.value())
        return {
            "difficulty": page.rotation_threshold_difficulty_combo.currentData(),
            "raid_dps": None if raid_dps <= 0.0 else raid_dps,
        }


def install_rotation_threshold_projection_policy_controls(
    page,
) -> RotationThresholdProjectionPolicyControls:
    support = RotationThresholdProjectionPolicyControls()
    support.install(page)
    return support


__all__ = [
    "RotationThresholdProjectionPolicyControls",
    "install_rotation_threshold_projection_policy_controls",
]
