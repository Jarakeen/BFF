from pathlib import Path


def test_owned_rotation_page_preserves_command_center_visual_contract() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert 'FoundryCard("Rotation Context", "rotations")' in source
    assert 'FoundryCard("Rotation Intent", "rotations")' in source
    assert 'FoundryCard("Inputs & Obligations", "field-office")' in source
    assert 'FoundryCard("Generate & Results", "optimization")' not in source
    obligations_start = source.index('def _build_obligations_card')
    obligations_end = source.index('def _obligation_row', obligations_start)
    obligations = source[obligations_start:obligations_end]
    assert 'self.generate_button = QPushButton("Generate Rotation")' in obligations
    assert 'self.clear_button = QPushButton("Clear Results")' in obligations
    assert '"Safe Progression"' in source
    assert '"Balanced"' in source
    assert '"Maximum Output"' in source
    assert 'self.result_tabs.addTab(timeline_host, "Timeline")' in source
    assert 'self.result_tabs.addTab(uptime_host, "Uptime & Resources")' in source
    assert 'self.result_tabs.addTab(explanation_host, "Explanations")' in source
    assert 'self.result_tabs.addTab(compare_host, "Compare")' in source
    assert 'self.result_tabs.addTab(save_host, "Save & Export")' in source


def test_owned_rotation_page_uses_direct_stable_service_boundaries() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert "self.rotation_runtime = Phase14RotationRuntimeService(" in source
    assert "self.rotation_sustain = RotationSustainService" in source
    assert "self.rotation_artifacts = BuildRotationArtifactService(" in source
    assert "self.timeline_projector = RotationTimelineProjectionService()" in source
    assert "self.rotation_pdf_exporter = RotationPdfExportService()" in source
    assert "self.rotation_runtime.generate(" in source
    assert "self.rotation_sustain.evaluate(" in source
    assert "resolve_build_context(" in source


def test_owned_rotation_page_wires_safe_runtime_features_without_legacy_dashboard() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    assert "reserve_fraction=float(self.minimum_reserve_spin.value()) / 100.0" in source
    assert "heavy_behavior=self.heavy_attack_combo.currentText()" in source
    assert "self.timeline_widget.set_projection(projection)" in source
    assert "self.rotation_artifacts.save_rotation(" in source
    assert "self.rotation_pdf_exporter.export(" in source
    assert "self.encounter_demand_registry.entry_for(encounter_id)" in source
    assert "CURRENT GENERATED" in source
    assert "LAST SAVED" in source

    forbidden = (
        "CanonicalRotationDashboardPage",
        "install_rotation_dashboard_layout",
        "install_phase14_rotation_command_center",
        "install_rotation_builder_v2_layout",
        "install_rotation_builder_v2_finish",
        "install_rotation_builder_v2_runtime_repairs",
    )
    for value in forbidden:
        assert value not in source
