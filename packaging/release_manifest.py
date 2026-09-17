from __future__ import annotations

"""Authoritative positive allowlist for FoundryDock release payloads.

The source repository is allowed to contain research, tests, retired UI, historical art,
and development evidence. The packaged application is not. PyInstaller and release
audits consume this manifest so only explicitly approved runtime assets are bundled.
"""

# (source path relative to project root, destination path inside the frozen app)
RUNTIME_ASSET_DATAS: tuple[tuple[str, str], ...] = (
    ("assets/AbilityIcons", "assets/AbilityIcons"),
    ("assets/avatar", "assets/avatar"),
    ("assets/icons", "assets/icons"),
    ("assets/logos/BFF_logo.png", "assets/logos"),
    ("assets/raid_plans/trial_banners", "assets/raid_plans/trial_banners"),
    ("assets/themes/bff/foundry.qss", "assets/themes/bff"),
    ("assets/themes/bff/urban_wilderness", "assets/themes/bff/urban_wilderness"),
    ("assets/themes/bff/field_journal/roster", "assets/themes/bff/field_journal/roster"),
    ("bff.ico", "."),
)

# The large startup artwork is intentionally local/optional today because image files
# are ignored by the repository. If present on the release workstation, import only
# this approved splash file from its historical location and place it under the active
# Urban Wilderness runtime path. Do not reopen the retired Grimoire theme tree.
OPTIONAL_RUNTIME_ASSET_DATAS: tuple[tuple[str, str], ...] = (
    (
        "assets/timers/vas2",
        "assets/timers/vas2",
    ),
    (
        "assets/themes/bff/grimoire/assets/fantasy_splash.png",
        "assets/themes/bff/urban_wilderness/startup",
    ),
    (
        "assets/themes/bff/grimoire/assets/fantasy_splash.jpg",
        "assets/themes/bff/urban_wilderness/startup",
    ),
    (
        "assets/themes/bff/grimoire/assets/fantasy_splash.jpeg",
        "assets/themes/bff/urban_wilderness/startup",
    ),
)

SEED_DATAS: tuple[tuple[str, str], ...] = (
    ("data/eso.db", "_seed_data"),
)

# Python namespaces that are explicitly outside the default release runtime. These may
# remain in source for history, tests, migrations, or optional development work.
PYINSTALLER_EXCLUDES: tuple[str, ...] = (
    "old_pages",
    "legacy",
    "deprecated",
    "migration",
    "modules.broadcast",
    "pytest",
)

RUNTIME_EXTERNAL_DATA_FILES: tuple[str, ...] = (
    "antiquities_01.csv",
    "antiquities_02.csv",
    "antiquities_03.csv",
    "antiquities_04.csv",
    "antiquities_05.csv",
    "antiquities_06.csv",
    "antiquities_07.csv",
    "antiquities_08.csv",
    "dungeon_encounter_identity.json",
    "dungeon_encounter_identity_launch_starters.json",
    "dungeon_encounter_identity_launch_starters_fifth.json",
    "dungeon_encounter_identity_launch_starters_sixth.json",
    "gameplay_policy/endgame_pve.json",
    "raid_encounter_identity.json",
    "reference_common_names.json",
    "reference_mitigations.json",
    "reference_mitigations_aetherian_archive.json",
    "reference_mitigations_ascending_tide.json",
    "reference_mitigations_asylum_sanctorium.json",
    "reference_mitigations_black_gem_foundry.json",
    "reference_mitigations_cloudrest.json",
    "reference_mitigations_dragon_bones.json",
    "reference_mitigations_fallen_banners.json",
    "reference_mitigations_flames_of_ambition.json",
    "reference_mitigations_halls_of_fabrication.json",
    "reference_mitigations_harrowstorm.json",
    "reference_mitigations_hel_ra_citadel.json",
    "reference_mitigations_horns_of_the_reach.json",
    "reference_mitigations_imperial_city.json",
    "reference_mitigations_kynes_aegis.json",
    "reference_mitigations_launch_normal_fifth_tranche.json",
    "reference_mitigations_launch_normal_fourth_tranche.json",
    "reference_mitigations_launch_normal_sixth_tranche.json",
    "reference_mitigations_launch_starter_dungeons.json",
    "reference_mitigations_launch_veteran_dungeons.json",
    "reference_mitigations_lost_depths.json",
    "reference_mitigations_lucent_citadel.json",
    "reference_mitigations_maw_of_lorkhaj.json",
    "reference_mitigations_naj_caldeesh.json",
    "reference_mitigations_ossein_cage.json",
    "reference_mitigations_sanctum_ophidia.json",
    "reference_mitigations_sanitys_edge.json",
    "reference_mitigations_scalebreaker.json",
    "reference_mitigations_scions_of_ithelia.json",
    "reference_mitigations_scribes_of_fate.json",
    "reference_mitigations_shadows_of_the_hist.json",
    "reference_mitigations_stonethorn.json",
    "reference_mitigations_update_2_crypt_of_hearts_ii.json",
    "reference_mitigations_update_5_city_of_ash_ii.json",
    "reference_mitigations_waking_flame.json",
    "reference_mitigations_wolfhunter.json",
    "reference_mitigations_wrathstone.json",
    "reference_mitigations_xalvakka_overview.json",
    "reference_version_history.json",
    "reference_version_history_champion_points.json",
    "reference_version_history_healer_skills.json",
    "rotation_dd_periodic_runtime_semantics.json",
    "rotation_dd_periodic_target_health_semantics.json",
    "rotation_runtime_output_conditions.json",
    "rotation_scribed_skill_damage_semantics.json",
    "source_manifest.json",
    "team_compositions.json",
    "team_prescription_templates.json",
)

# Reviewed runtime directories required by the packaged application. Keep these
# separate from file entries so the release script can copy them recursively while
# preserving the exact data-relative path. These are canonical app inputs, not
# research/workbench folders.
RUNTIME_EXTERNAL_DATA_DIRECTORIES: tuple[str, ...] = (
    "eso_info/bosses",
    "encounter_evidence",
)

CLEAN_FIRST_INSTALL_DATA_FILES: tuple[str, ...] = (
    "builds.json",
    "characters.json",
)

EXCLUDED_TOP_LEVEL_DATA_GLOBS: tuple[str, ...] = (
    "*.before-*",
    "*.backup*",
    "*.bak",
    "*.old",
    "*.orig",
    "*.pre-*",
    "*.pre_*",
    "eso.db.before-*",
    "eso.db.pre-*",
    "eso.db.*backup*",
)

EXCLUDED_TOP_LEVEL_DATA_FILES: tuple[str, ...] = (
    "eso_achievements.json",
    "eso_categories.json",
    "eso_tree.json",
    "healer_refresh_reviewed.json",
    "healer_runtime_candidates.json",
    "healer_runtime_reviewed.json",
    "rotation_dd_periodic_runtime_semantics_review.json",
)

FORBIDDEN_RELEASE_ASSET_PREFIXES: tuple[str, ...] = (
    "assets/decorative",
    "assets/field_office_placeholders",
    "assets/themes/bff/city_night",
    "assets/themes/bff/decorative",
    "assets/themes/bff/grimoire",
)

FORBIDDEN_RELEASE_PATH_PARTS: tuple[str, ...] = (
    ".git",
    ".pytest_cache",
    ".runtime-evidence",
    ".venv",
    "__pycache__",
    "tests",
    "research",
)

USER_OWNED_DATA_FILES: tuple[str, ...] = (
    "achievement_progress.json",
    "antiquity_progress.json",
    "builds.json",
    "capabilities.json",
    "characters.json",
    "current_achievement_run.json",
    "CurrentAchievementRun.json",
    "CurrentBroadcast.json",
    "CurrentExpedition.json",
    "CurrentIncident.json",
    "encounter_positioning.json",
    "encounter_positioning.png",
    "encounter_positioning_timeline.json",
    "esologs_trending_history.json",
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt",
    "MarkerLog.md",
    "performance_dashboard.json",
    "performance_focus.json",
    "StreamEvents.json",
    "StreamSession.json",
    "TamrielDate.txt",
    "team_composition_user_templates.json",
    "team_prescription_observed_templates.json",
)


def pyinstaller_datas(project_root):
    """Return validated PyInstaller ``datas`` entries from the positive allowlist."""
    entries: list[tuple[str, str]] = []
    for source, destination in (*RUNTIME_ASSET_DATAS, *SEED_DATAS):
        path = project_root / source
        if not path.exists():
            raise FileNotFoundError(f"Required release asset is missing: {source}")
        entries.append((str(path), destination))

    for source, destination in OPTIONAL_RUNTIME_ASSET_DATAS:
        path = project_root / source
        if path.exists():
            entries.append((str(path), destination))

    return entries
