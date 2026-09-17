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
    assert '(str(project_root / "assets"), "assets")' not in source


def test_release_version_has_one_python_source_of_truth() -> None:
    version = (ROOT / "app_version.py").read_text(encoding="utf-8")
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")

    assert 'APP_VERSION = "0.1.0"' in version
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
    assert hasattr(manifest, "RUNTIME_EXTERNAL_DATA_FILES")
    assert hasattr(manifest, "CLEAN_FIRST_INSTALL_DATA_FILES")


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
