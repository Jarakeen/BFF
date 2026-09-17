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
    # Urban Wilderness still deliberately uses these two pencil/sketch Roster notes.
    ("assets/themes/bff/field_journal/roster", "assets/themes/bff/field_journal/roster"),
    # Windows executable icon.
    ("bff.ico", "."),
)

# Runtime seed data. The live writable database remains external and must never be
# overwritten by an update. This seed is only for first-install/recovery provisioning.
SEED_DATAS: tuple[tuple[str, str], ...] = (
    ("data/eso.db", "_seed_data"),
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
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt",
    "MarkerLog.md",
    "StreamEvents.json",
    "StreamSession.json",
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
