from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]


def _load_manifest():
    path = ROOT / "packaging" / "release_manifest.py"
    spec = importlib.util.spec_from_file_location("foundrydock_release_manifest_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_manifest_is_positive_asset_allowlist() -> None:
    manifest = _load_manifest()
    sources = {source for source, _destination in manifest.RUNTIME_ASSET_DATAS}

    assert "assets/logos/BFF_logo.png" in sources
    assert "assets/themes/bff/urban_wilderness" in sources
    assert "assets/themes/bff/field_journal/roster" in sources
    assert "assets/icons" in sources
    assert "assets/AbilityIcons" in sources
    assert "assets" not in sources

    for forbidden in manifest.FORBIDDEN_RELEASE_ASSET_PREFIXES:
        assert all(
            source != forbidden and not source.startswith(forbidden.rstrip("/") + "/")
            for source in sources
        )


def test_pyinstaller_spec_consumes_release_manifest_instead_of_whole_assets_tree() -> None:
    source = (ROOT / "packaging" / "BFF.spec").read_text(encoding="utf-8")

    assert 'release_manifest.py' in source
    assert 'manifest["pyinstaller_datas"](project_root)' in source
    assert 'release_excludes = list(manifest.get("PYINSTALLER_EXCLUDES", ()))' in source
    assert 'excludes=release_excludes' in source
    assert '(str(project_root / "assets"), "assets")' not in source


def test_release_excludes_archived_legacy_and_optional_python_namespaces() -> None:
    manifest = _load_manifest()
    excluded = set(manifest.PYINSTALLER_EXCLUDES)

    for namespace in (
        "old_pages",
        "legacy",
        "deprecated",
        "migration",
        "modules.broadcast",
        "pytest",
    ):
        assert namespace in excluded


def test_release_runtime_formula_module_does_not_import_pytest() -> None:
    source = (ROOT / "minmax" / "formulas" / "final_calculations.py").read_text(
        encoding="utf-8"
    )

    assert "import pytest" not in source
    assert "from pytest" not in source


def test_release_version_has_one_python_source_of_truth() -> None:
    version = (ROOT / "app_version.py").read_text(encoding="utf-8")
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")

    assert 'APP_VERSION = "0.1.1"' in version
    assert 'from app_version import APP_VERSION; print(APP_VERSION)' in build
    assert 'APP_VERSION' not in (ROOT / "packaging" / "BFF.spec").read_text(encoding="utf-8")


def test_release_build_preserves_user_database_and_uses_fixed_update_asset_name() -> None:
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    updater = (ROOT / "services" / "application_update_service.py").read_text(encoding="utf-8")

    assert 'Copy-Item $SourceDatabase (Join-Path $DataRoot "eso.db") -Force' in build
    assert 'FoundryDock-update.zip' in build
    assert 'FoundryDock-update.zip' in updater
    assert 'Copy-Item (Join-Path $PackageRoot "settings.json")' not in build
    assert 'Copy-Item (Join-Path $DataRoot "eso.db")' not in build
    assert 'Copy-Item (Join-Path $DataRoot "builds.json")' not in build


def test_final_release_build_is_blocked_until_data_classification_is_complete() -> None:
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "audit_release_candidate.py").read_text(encoding="utf-8")
    manifest = _load_manifest()

    assert 'audit_release_candidate.py --strict-data' in build
    assert 'RUNTIME_EXTERNAL_DATA_FILES' in audit
    assert 'EXCLUDED_TOP_LEVEL_DATA_GLOBS' in audit
    assert 'EXCLUDED_TOP_LEVEL_DATA_FILES' in audit
    assert '--list-unclassified' in audit
    assert hasattr(manifest, "RUNTIME_EXTERNAL_DATA_FILES")
    assert hasattr(manifest, "CLEAN_FIRST_INSTALL_DATA_FILES")
    assert hasattr(manifest, "EXCLUDED_TOP_LEVEL_DATA_GLOBS")
    assert hasattr(manifest, "EXCLUDED_TOP_LEVEL_DATA_FILES")


def test_reviewed_runtime_data_and_user_state_are_classified() -> None:
    manifest = _load_manifest()
    runtime = set(manifest.RUNTIME_EXTERNAL_DATA_FILES)
    user_owned = set(manifest.USER_OWNED_DATA_FILES)
    excluded_globs = set(manifest.EXCLUDED_TOP_LEVEL_DATA_GLOBS)
    excluded_exact = set(manifest.EXCLUDED_TOP_LEVEL_DATA_FILES)

    for name in (
        "antiquities_01.csv",
        "antiquities_08.csv",
        "dungeon_encounter_identity.json",
        "dungeon_encounter_identity_launch_starters_sixth.json",
        "raid_encounter_identity.json",
        "reference_common_names.json",
        "reference_mitigations.json",
        "reference_mitigations_xalvakka_overview.json",
        "reference_version_history.json",
        "rotation_dd_periodic_runtime_semantics.json",
        "rotation_dd_periodic_target_health_semantics.json",
        "rotation_runtime_output_conditions.json",
        "rotation_scribed_skill_damage_semantics.json",
        "source_manifest.json",
        "team_compositions.json",
        "team_prescription_templates.json",
    ):
        assert name in runtime

    for name in (
        "encounter_positioning.json",
        "encounter_positioning.png",
        "encounter_positioning_timeline.json",
        "esologs_trending_history.json",
        "performance_dashboard.json",
        "performance_focus.json",
        "TamrielDate.txt",
        "team_composition_user_templates.json",
    ):
        assert name in user_owned

    for name in (
        "eso_achievements.json",
        "eso_categories.json",
        "eso_tree.json",
        "healer_refresh_reviewed.json",
        "healer_runtime_candidates.json",
        "healer_runtime_reviewed.json",
        "rotation_dd_periodic_runtime_semantics_review.json",
    ):
        assert name in excluded_exact

    assert "*.before-*" in excluded_globs
    assert "eso.db.before-*" in excluded_globs


def test_packaged_sidebar_hides_in_progress_routes_but_source_build_keeps_them_available() -> None:
    policy = (ROOT / "services" / "release_feature_policy.py").read_text(encoding="utf-8")
    support = (ROOT / "ui" / "theme_brand_mark_support.py").read_text(encoding="utf-8")

    for route in (
        '"rotations"',
        '"extreme_optimization"',
        '"console:6"',
        '"collectibles"',
        '"stickerbook"',
    ):
        assert route in policy
    assert '"collectibles:"' in policy
    assert 'getattr(sys, "frozen", False)' in policy
    assert 'FOUNDRYDOCK_RELEASE_MODE' in policy
    assert "route_allowed" in support
    assert "_filter_release_sections" in support
    assert "sidebar_module.nav_sections = release_aware_nav_sections" in support


def test_release_status_names_disabled_and_in_progress_boundaries() -> None:
    status = (ROOT / "RELEASE_STATUS.md").read_text(encoding="utf-8")

    assert "## In progress" in status
    assert "Rotation Builder" in status
    assert "Extreme Build Engine" in status
    assert "Collectibles" in status
    assert "## Disabled" in status
    assert "Screenshot/OCR Build Import" in status
    assert "Community News" in status
    assert "Broadcast module" in status
    assert "## Legacy / deprecated / superseded" in status
    assert "Data payload classification: complete" in status
