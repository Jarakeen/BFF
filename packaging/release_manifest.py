from __future__ import annotations

"""Authoritative positive allowlist for FoundryDock release payloads.

The source repository is allowed to contain research, tests, retired UI, historical art,
and development evidence. The packaged application is not. PyInstaller and release
audits consume this manifest so only explicitly approved runtime assets are bundled.
"""

# (source path relative to project root, destination path inside the frozen app)
RUNTIME_ASSET_DATAS: tuple[tuple[str, str], ...] = (
    # Canonical ESO ability artwork is selected dynamically by runtime identity.
    ("assets/AbilityIcons", "assets/AbilityIcons"),
    # Canonical semantic UI icon library used by FoundryCard/navigation controls.
    ("assets/icons", "assets/icons"),
    # Current approved application branding.
    ("assets/logos/BFF_logo.png", "assets/logos"),
    # Current supported visual skin.
    ("assets/themes/bff/foundry.qss", "assets/themes/bff"),
    ("assets/themes/bff/urban_wilderness", "assets/themes/bff/urban_wilderness"),
    # Urban Wilderness still deliberately uses these pencil/sketch Roster notes.
    ("assets/themes/bff/field_journal/roster", "assets/themes/bff/field_journal/roster"),
    # Windows executable icon.
    ("bff.ico", "."),
)

# Runtime seed data. The live writable database remains external and must never be
# overwritten by an update. This seed is only for first-install/recovery provisioning.
SEED_DATAS: tuple[tuple[str, str], ...] = (
    ("data/eso.db", "_seed_data"),
)

# External runtime reference files copied beside the executable. These are reviewed
# one family at a time; nothing earns a release slot merely because it lives in data/.
RUNTIME_EXTERNAL_DATA_FILES: tuple[str, ...] = (
    # Antiquity reference catalog is consumed by Antiquities and Extreme named-gear logic.
    "antiquities_01.csv",
    "antiquities_02.csv",
    "antiquities_03.csv",
    "antiquities_04.csv",
    "antiquities_05.csv",
    "antiquities_06.csv",
    "antiquities_07.csv",
    "antiquities_08.csv",
    # Reviewed encounter identity used by planning/reference/runtime resolution.
    "dungeon_encounter_identity.json",
    "dungeon_encounter_identity_launch_starters.json",
    "dungeon_encounter_identity_launch_starters_fifth.json",
    "dungeon_encounter_identity_launch_starters_sixth.json",
    "raid_encounter_identity.json",
    # Human-facing reference enrichment used by the current Reference Data surface.
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
    # Executable rotation/runtime semantics. Review-only evidence is excluded below.
    "rotation_dd_periodic_runtime_semantics.json",
    "rotation_dd_periodic_target_health_semantics.json",
    "rotation_runtime_output_conditions.json",
    "rotation_scribed_skill_damage_semantics.json",
    # Provenance and canonical team templates used by current runtime services.
    "source_manifest.json",
    "team_compositions.json",
    "team_prescription_templates.json",
)

# Files created cleanly on first install instead of copied from the developer machine.
CLEAN_FIRST_INSTALL_DATA_FILES: tuple[str, ...] = (
    "builds.json",
)

# Top-level data artifacts that must never ship. Pattern matching is intentional for
# timestamped/one-off recovery copies. These remain useful in source archaeology only.
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

# Exact top-level data files that are intentionally source/development evidence only.
# These are not needed by the supported release runtime.
EXCLUDED_TOP_LEVEL_DATA_FILES: tuple[str, ...] = (
    # Legacy achievement JSON is only referenced by old_pages; current runtime uses
    # canonical database-backed achievement data instead.
    "eso_achievements.json",
    "eso_categories.json",
    "eso_tree.json",
    # Healer refresh/runtime observation fixtures are review/audit evidence.
    "healer_refresh_reviewed.json",
    "healer_runtime_candidates.json",
    "healer_runtime_reviewed.json",
    # Non-executable DD periodic review evidence. Promoted executable semantics live in
    # rotation_dd_periodic_runtime_semantics.json above.
    "rotation_dd_periodic_runtime_semantics_review.json",
)

# These source trees may remain in the repository but are not release payloads.
# Adding one of them to RUNTIME_ASSET_DATAS should fail the release audit.
FORBIDDEN_RELEASE_ASSET_PREFIXES: tuple[str, ...] = (
    "assets/decorative",
    "assets/field_office_placeholders",
    "assets/themes/bff/city_night",
    "assets/themes/bff/decorative",
    "assets/themes/bff/grimoire",
)

# Development/research material is never copied as external package data.
FORBIDDEN_RELEASE_PATH_PARTS: tuple[str, ...] = (
    ".git",
    ".pytest_cache",
    ".runtime-evidence",
    ".venv",
    "__pycache__",
    "tests",
    "research",
)

# User-owned state must not appear in an update archive. Some of these are created as
# clean first-install files, but they are never copied from the developer workstation.
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
    return entries
