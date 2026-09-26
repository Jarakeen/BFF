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
    assert "assets/avatar" in sources
    assert "assets" not in sources

    for forbidden in manifest.FORBIDDEN_RELEASE_ASSET_PREFIXES:
        assert all(
            source != forbidden and not source.startswith(forbidden.rstrip("/") + "/")
            for source in sources
        )


def test_release_imports_only_approved_optional_splash_from_legacy_location() -> None:
    manifest = _load_manifest()
    optional = dict(manifest.OPTIONAL_RUNTIME_ASSET_DATAS)

    assert optional[
        "assets/themes/bff/grimoire/assets/fantasy_splash.png"
    ] == "assets/themes/bff/urban_wilderness/startup"
    splash_optional = {
        source: destination
        for source, destination in optional.items()
        if "fantasy_splash" in source
    }
    assert all("grimoire" in source for source in splash_optional)
    assert all(
        destination == "assets/themes/bff/urban_wilderness/startup"
        for destination in splash_optional.values()
    )
    assert optional["assets/timers/vas2"] == "assets/timers/vas2"

    splash = (ROOT / "ui" / "startup_splash.py").read_text(encoding="utf-8")
    assert '("assets", "themes", "bff", "urban_wilderness", "startup")' in splash
    assert "fantasy_splash.png" in splash


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

    import re

    match = re.search(r'^APP_VERSION\\s*=\\s*["\\'](\\d+\\.\\d+\\.\\d+)["\\']', version, re.MULTILINE)
    assert match is not None
    assert match.group(1)
    assert 'from app_version import APP_VERSION; print(APP_VERSION)' in build
    assert 'APP_VERSION' not in (ROOT / "packaging" / "BFF.spec").read_text(encoding="utf-8")


def test_release_build_preserves_user_database_and_uses_fixed_update_asset_name() -> None:
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    updater = (ROOT / "services" / "application_update_service.py").read_text(encoding="utf-8")

    assert 'build_release_database_seed.py' in build
    assert 'Copy-Item $ReleaseSeedDatabase (Join-Path $DataRoot "eso.db") -Force' in build
    assert 'Copy-Item $SourceDatabase (Join-Path $DataRoot "eso.db") -Force' not in build
    assert 'FoundryDock-update.zip' in build
    assert 'FoundryDock-update.zip' in updater
    assert 'Copy-Item (Join-Path $PackageRoot "settings.json")' not in build
    assert 'Copy-Item (Join-Path $DataRoot "eso.db")' not in build
    assert 'Copy-Item (Join-Path $DataRoot "builds.json")' not in build


def test_release_builds_support_explicit_first_run_user_database_seed() -> None:
    manifest = _load_manifest()
    release = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    friend = (ROOT / "packaging" / "build_friend.ps1").read_text(encoding="utf-8")

    assert ("build/release_seed/foundrydock.db", "_seed_user_data") in set(
        manifest.OPTIONAL_SEED_DATAS
    )
    assert '[string]$UserDatabaseSeed = ""' in release
    assert '[string]$UserDatabaseSeed = ""' in friend
    assert "[switch]$UseCurrentRaidSetup" in friend
    assert '[string]$RaidPlanId = ""' in friend
    assert "build_custom_user_database_seed.py" in friend
    assert "build_custom_raid_plan_catalog_seed.py" not in friend
    assert "--plan-id $RaidPlanId" in friend
    assert "data\\builds.json or data\\characters.json" in friend
    assert 'Join-Path $ReleaseSeedRoot "foundrydock.db"' in release
    assert 'Join-Path $ReleaseSeedRoot "foundrydock.db"' in friend


def test_release_build_supports_nested_runtime_reference_data() -> None:
    manifest = _load_manifest()
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")

    assert "gameplay_policy/endgame_pve.json" in manifest.RUNTIME_EXTERNAL_DATA_FILES
    assert "$DestinationParent = Split-Path $Destination -Parent" in build
    assert "$UpdateDestinationParent = Split-Path $UpdateDestination -Parent" in build
    assert "New-Item -ItemType Directory -Force -Path $DestinationParent" in build
    assert "New-Item -ItemType Directory -Force -Path $UpdateDestinationParent" in build


def test_release_includes_canonical_encounter_runtime_directories() -> None:
    manifest = _load_manifest()
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "audit_release_candidate.py").read_text(encoding="utf-8")

    runtime_directories = set(manifest.RUNTIME_EXTERNAL_DATA_DIRECTORIES)
    assert runtime_directories == {
        "eso_info/bosses",
        "encounter_evidence",
        "rotation_policy",
    }
    assert "RUNTIME_EXTERNAL_DATA_DIRECTORIES" in build
    assert "Copy-Item $Source $Destination -Recurse -Force" in build
    assert "RUNTIME_EXTERNAL_DATA_DIRECTORIES" in audit
    assert "runtime_external_directories" in audit


def test_final_release_build_is_blocked_until_data_classification_is_complete() -> None:
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "audit_release_candidate.py").read_text(encoding="utf-8")
    manifest = _load_manifest()

    assert 'audit_release_candidate.py --strict-data' in build
    assert 'RUNTIME_EXTERNAL_DATA_FILES' in audit
    assert 'RUNTIME_EXTERNAL_DATA_DIRECTORIES' in audit
    assert 'EXCLUDED_TOP_LEVEL_DATA_GLOBS' in audit
    assert 'EXCLUDED_TOP_LEVEL_DATA_FILES' in audit
    assert '--list-unclassified' in audit
    assert hasattr(manifest, "RUNTIME_EXTERNAL_DATA_FILES")
    assert hasattr(manifest, "RUNTIME_EXTERNAL_DATA_DIRECTORIES")
    assert hasattr(manifest, "CLEAN_FIRST_INSTALL_DATA_FILES")
    assert hasattr(manifest, "EXCLUDED_TOP_LEVEL_DATA_GLOBS")
    assert hasattr(manifest, "EXCLUDED_TOP_LEVEL_DATA_FILES")


def test_reviewed_runtime_data_and_user_state_are_classified() -> None:
    manifest = _load_manifest()
    runtime = set(manifest.RUNTIME_EXTERNAL_DATA_FILES)
    runtime_directories = set(manifest.RUNTIME_EXTERNAL_DATA_DIRECTORIES)
    user_owned = set(manifest.USER_OWNED_DATA_FILES)
    excluded_globs = set(manifest.EXCLUDED_TOP_LEVEL_DATA_GLOBS)
    excluded_exact = set(manifest.EXCLUDED_TOP_LEVEL_DATA_FILES)

    for name in (
        "antiquities_01.csv",
        "antiquities_08.csv",
        "dungeon_encounter_identity.json",
        "dungeon_encounter_identity_launch_starters_sixth.json",
        "gameplay_policy/endgame_pve.json",
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

    assert "eso_info/bosses" in runtime_directories
    assert "encounter_evidence" in runtime_directories
    assert "rotation_policy" in runtime_directories
    assert (ROOT / "data" / "rotation_policy" / "encounter_demands.json").is_file()

    for name in (
        "build_profiles.json",
        "finch_shared_provenance.json",
        "discord_registrations.json",
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


def test_packaged_sidebar_hides_only_unreleased_routes_and_keeps_collectibles_visible() -> None:
    policy = (ROOT / "services" / "release_feature_policy.py").read_text(encoding="utf-8")
    support = (ROOT / "ui" / "theme_brand_mark_support.py").read_text(encoding="utf-8")

    assert '"rotations"' not in policy
    for route in (
        '"extreme_optimization"',
        '"console:6"',
    ):
        assert route in policy
    assert '"collectibles"' not in policy
    assert '"stickerbook"' not in policy
    assert '"collectibles:"' not in policy
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
    assert "Collectibles / Stickerbook core workflows" in status
    assert "Collectibles presentation polish" not in status
    assert "## Disabled" in status
    assert "Screenshot/OCR Build Import" in status
    assert "Community News" in status
    assert "Broadcast module" in status
    assert "## Legacy / deprecated / superseded" in status
    assert "Data payload classification: complete" in status


def test_rotation_command_center_preserves_legacy_shell_without_delete_later() -> None:
    command_center = (ROOT / "ui" / "phase14_rotation_command_center_support.py").read_text(
        encoding="utf-8"
    )

    assert "page._phase14_preserved_legacy_builder = old_builder" in command_center
    assert "old_builder.deleteLater()" not in command_center
    assert not (ROOT / "ui" / "phase14_rotation_visual_target_support.py").exists()


def test_first_install_keeps_build_and_character_state_out_of_data_directory() -> None:
    manifest = _load_manifest()
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    friend = (ROOT / "packaging" / "build_friend.ps1").read_text(encoding="utf-8")

    assert manifest.CLEAN_FIRST_INSTALL_DATA_FILES == ()
    assert '[System.IO.File]::WriteAllText(\n        (Join-Path $DataRoot "characters.json")' not in build
    assert '(Join-Path $DataRoot "builds.json")' not in build
    assert '$CharacterCatalogPath = Join-Path $DataRoot "characters.json"' not in friend
    assert '$CleanBuildsPath = Join-Path $DataRoot "builds.json"' not in friend


def test_release_includes_rotation_encounter_policy_required_at_startup() -> None:
    manifest = _load_manifest()
    registry = (
        ROOT / "services" / "rotation_encounter_demand_policy_registry_service.py"
    ).read_text(encoding="utf-8")

    assert "rotation_policy" in set(manifest.RUNTIME_EXTERNAL_DATA_DIRECTORIES)
    assert 'get_data_dir() / "rotation_policy" / "encounter_demands.json"' in registry
    assert (ROOT / "data" / "rotation_policy" / "encounter_demands.json").is_file()


def test_release_embeds_sanitized_database_seed_instead_of_live_database() -> None:
    manifest = _load_manifest()
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")

    assert manifest.SEED_DATAS == (("build/release_seed/eso.db", "_seed_data"),)
    assert '$ReleaseSeedDatabase = Join-Path $ReleaseSeedRoot "eso.db"' in build
    assert 'python tools\\build_release_database_seed.py --source $SourceDatabase --destination $ReleaseSeedDatabase' in build


def test_private_updater_package_uses_production_gateway_without_committing_secret() -> None:
    service = (ROOT / "services" / "application_update_service.py").read_text(encoding="utf-8")
    release = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8")
    friend = (ROOT / "packaging" / "build_friend.ps1").read_text(encoding="utf-8")

    expected_domain = "https://bff-production-30c2.up.railway.app"
    assert expected_domain in service
    assert expected_domain in release
    assert expected_domain in friend
    assert "FOUNDRYDOCK_UPDATE_ACCESS_KEY" in release
    assert "FOUNDRYDOCK_UPDATE_ACCESS_KEY" in friend
    assert 'update_access.json' in release
    assert 'update_access.json' in friend
    assert "GITHUB_TOKEN" not in service
    assert "GITHUB_TOKEN" not in release
    assert "GITHUB_TOKEN" not in friend


def test_friend_build_creates_sanitized_release_seed_before_pyinstaller() -> None:
    friend = (ROOT / "packaging" / "build_friend.ps1").read_text(encoding="utf-8")

    seed_command = (
        'python tools\\build_release_database_seed.py --source $SourceDatabase '
        '--destination $ReleaseSeedDatabase'
    )
    pyinstaller_command = 'python -m PyInstaller --clean $SpecPath'

    assert '$ReleaseSeedDatabase = Join-Path $ReleaseSeedRoot "eso.db"' in friend
    assert seed_command in friend
    assert 'Copy-Item $ReleaseSeedDatabase $TargetDatabase -Force' in friend
    assert 'Copy-Item $SourceDatabase $TargetDatabase -Force' not in friend
    assert friend.index(seed_command) < friend.index(pyinstaller_command)


def test_friend_build_uses_release_manifest_runtime_data_allowlists() -> None:
    friend = (ROOT / "packaging" / "build_friend.ps1").read_text(encoding="utf-8")
    manifest = (ROOT / "packaging" / "release_manifest.py").read_text(encoding="utf-8")

    assert "RUNTIME_EXTERNAL_DATA_FILES" in friend
    assert "RUNTIME_EXTERNAL_DATA_DIRECTORIES" in friend
    assert "gameplay_policy/endgame_pve.json" in manifest
    assert 'Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Force' in friend
    assert 'Copy-Item (Join-Path $DataRoot $Name) $UpdateDestination -Recurse -Force' in friend
