from pathlib import Path


def test_owned_rotation_page_preserves_command_center_visual_contract() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Rotation Context", "rotations")' in source
    assert 'FoundryCard("Rotation Intent", "rotations")' in source
    assert 'FoundryCard("Inputs & Obligations", "field-office")' in source
    assert 'FoundryCard("Generate & Results", "optimization")' in source
    assert '"Safe Progression"' in source
    assert '"Balanced"' in source
    assert '"Maximum Output"' in source
    assert 'self.result_tabs.addTab(timeline_host, "Timeline")' in source
    assert 'self.result_tabs.addTab(uptime_host, "Uptime & Resources")' in source
    assert 'self.result_tabs.addTab(explanation_host, "Explanations")' in source
    assert 'self.result_tabs.addTab(compare_host, "Compare")' in source
    assert 'self.result_tabs.addTab(save_host, "Save & Export")' in source


def test_owned_rotation_page_calls_existing_engine_services_directly() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert "self.rotation_generation = RotationGenerationSupport()" in source
    assert "self.rotation_sustain = RotationSustainService" in source
    assert "self.rotation_generation.generate_with_evidence(" in source
    assert "self.rotation_sustain.evaluate(" in source
    assert "resolve_build_context(" in source
