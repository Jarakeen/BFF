from pathlib import Path

from ui import rotation_builder_v2_polish_support
from ui import rotation_dashboard_layout_support


def test_mockup_composition_installs_before_compact_context_and_final_polish() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert "install_rotation_builder_v2_mockup_bridge(page)" in source
    assert "install_rotation_builder_v2_compact_context(page)" in source
    assert "install_rotation_builder_v2_polish(page)" in source
    assert source.index("install_rotation_builder_v2_mockup_bridge(page)") < source.index(
        "install_rotation_builder_v2_compact_context(page)"
    ) < source.index("install_rotation_builder_v2_polish(page)")


def test_polish_surfaces_live_heavy_attack_requirements_from_resolved_build() -> None:
    source = Path(rotation_builder_v2_polish_support.__file__).read_text(encoding="utf-8")

    assert "discover_healer_heavy_attack_build_incentives(build)" in source
    assert "rotation_effective_build" in source
    assert "HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT" in source
    assert "maintains" in source
    assert "verified recovery option" in source


def test_unfinished_rotation_modes_remain_visibly_disabled_after_mockup_pass() -> None:
    source = Path(rotation_builder_v2_polish_support.__file__).read_text(encoding="utf-8")

    assert 'supported = title == "Semi-static"' in source
    assert "button.setEnabled(supported)" in source
    assert "button.setChecked(True)" in source


def test_mockup_polish_compacts_live_controls_without_cloning_engine_inputs() -> None:
    source = Path(rotation_builder_v2_polish_support.__file__).read_text(encoding="utf-8")

    assert "control.setMinimumHeight(30)" in source
    assert "control.setMaximumHeight(30)" in source
    assert '"Rotation Rules & Requirements"' in source
    assert '"Pressure Windows"' in source
