from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from engine.config import ensure_default_database, get_resource_path


def _set_windows_app_id() -> None:
    """
    Set the Windows AppUserModelID so the taskbar icon
    uses the Foundry branding instead of python.exe.
    """

    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "BlackFeatherFoundry.FieldOffice"
        )

    except Exception:
        pass


def _set_native_windows_icon(window, icon_path: Path) -> None:
    """Force the Win32 top-level window icon used by Alt-Tab/taskbar surfaces."""
    if sys.platform != "win32" or not icon_path.is_file():
        return

    try:
        import ctypes

        user32 = ctypes.windll.user32

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        icon_handle = user32.LoadImageW(
            None,
            str(icon_path),
            IMAGE_ICON,
            0,
            0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        if not icon_handle:
            return

        hwnd = int(window.winId())
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_handle)
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon_handle)
    except Exception:
        pass


def _prepare_optional_module_state() -> None:
    from services.optional_modules import broadcast_enabled

    if not broadcast_enabled():
        return

    from services.broadcast_state_migration import migrate_legacy_broadcast_state

    migrate_legacy_broadcast_state()


def _close_pyinstaller_boot_splash() -> None:
    """Close PyInstaller's boot splash only after the Qt splash is visible.

    The module exists only in a splash-enabled frozen build. Keeping the boot
    splash alive until this point prevents a bright/blank handoff gap during
    startup for photosensitive users.
    """
    try:
        import pyi_splash

        if pyi_splash.is_alive():
            pyi_splash.close()
    except (ImportError, RuntimeError):
        pass


def _prepare_packaged_database() -> bool:
    """Provision the frozen database or show a recoverable startup message."""

    try:
        ensure_default_database()
        return True
    except OSError as exc:
        _close_pyinstaller_boot_splash()
        QMessageBox.critical(
            None,
            "FoundryDock data unavailable",
            "FoundryDock could not prepare its ESO database.\n\n"
            "Please extract the complete BFF-Friend.zip into a normal folder "
            "and run FoundryDock.exe from that folder. Administrator access is "
            "not required.\n\n"
            f"Details: {exc}",
        )
        return False


def main() -> int:

    _set_windows_app_id()
    _prepare_optional_module_state()

    app = QApplication(sys.argv)

    app.setApplicationName("Black Feather Foundry Field Office")
    app.setOrganizationName("Black Feather Foundry")

    app_icon = get_resource_path("bff.ico")
    foundry_icon = QIcon(str(app_icon)) if app_icon.exists() else QIcon()
    if not foundry_icon.isNull():
        app.setWindowIcon(foundry_icon)

    if not _prepare_packaged_database():
        return 2

    from ui.startup_splash import create_startup_splash

    splash = create_startup_splash()
    splash.show()
    app.processEvents()
    _close_pyinstaller_boot_splash()

    from ui.theme import ThemeManager
    from ui.components.searchable_build_selectors import install as install_searchable_selectors
    from ui.scribing_support import install as install_scribing_support
    from ui.scribing_editor_compat import install as install_scribing_editor_compat
    from ui.phase5_build_ui_support import install as install_phase5_build_ui_support
    from ui.phase5_racial_filter_fix import install as install_phase5_racial_filter_fix
    from ui.phase5_build_delete_support import install as install_phase5_build_delete_support
    from ui.phase5_operations_progression_support import install as install_phase5_operations_progression_support
    from ui.phase5_racial_context_support import install as install_phase5_racial_context_support
    from ui.phase5_potion_picker_support import install as install_phase5_potion_picker_support
    from ui.build_editor_inline_compat import install as install_inline_build_editor
    from ui.build_workspace_edit_fix import install as install_build_workspace_edit_fix
    from ui.build_workspace_tab_layout_fix import install as install_build_workspace_tab_layout_fix
    from ui.build_editor_performance import install as install_build_editor_performance
    from ui.build_progression_scroll_fix import install as install_build_progression_scroll_fix
    from ui.icon_consistency import install as install_icon_consistency
    from ui.encounter_board_accessibility import install as install_encounter_board_accessibility
    from ui.rylo_theme_support import install as install_rylo_theme_support
    from ui.rylo_surface_icon_fix import install as install_rylo_surface_icon_fix
    from ui.theme_brand_mark_support import install as install_theme_brand_mark_support
    from ui.rylo_raid_map_support import install as install_rylo_raid_map_support
    from ui.mechanics_boss_map_support import install as install_mechanics_boss_map_support
    from ui.independent_timer_note_support import install as install_independent_timer_note_support
    from ui.encounter_research_support import install as install_encounter_research_support
    from ui.collectibles_profile_support import install as install_collectibles_profile_support
    from ui.collectibles_acquisition_support import install as install_collectibles_acquisition_support
    from ui.collectibles_learned_recipe_support import install as install_collectibles_learned_recipe_support
    from ui.collectibles_motif_support import install as install_collectibles_motif_support
    from ui.collectibles_lorebook_support import install as install_collectibles_lorebook_support
    from ui.collectibles_antiquity_support import install as install_collectibles_antiquity_support
    from ui.application_update_support import install as install_application_update_support

    install_searchable_selectors()
    install_scribing_support()
    install_scribing_editor_compat()
    install_phase5_build_ui_support()
    install_phase5_racial_filter_fix()
    install_phase5_build_delete_support()
    install_phase5_operations_progression_support()
    install_phase5_racial_context_support()
    install_phase5_potion_picker_support()
    install_inline_build_editor()
    install_build_workspace_edit_fix()
    install_build_workspace_tab_layout_fix()
    install_build_editor_performance()
    install_build_progression_scroll_fix()
    install_icon_consistency(app)
    install_encounter_board_accessibility()
    install_rylo_theme_support(app)
    # Install last among visual-theme layers so legacy Grimoire leather/raw SVG
    # assignments cannot override Rylo's stone surfaces or silver card icons.
    install_rylo_surface_icon_fix(app)
    install_theme_brand_mark_support()
    # Raid Map owns custom QGraphics painting, so it needs its own theme-aware
    # palette after accessibility and visual-theme support are registered.
    install_rylo_raid_map_support()
    # Mechanics pairs multi-actor encounters and stores per-boss Raid Maps before
    # MainWindow constructs the boss-guide page.
    install_mechanics_boss_map_support()
    # User-facing timers/notepads own separate state and must be patched before
    # MainWindow constructs the affected pages.
    install_independent_timer_note_support()
    # Encounter Research replaces the Data Management builder before SettingsPage
    # is instantiated so intake/review lives beside achievement progress tools.
    install_encounter_research_support()
    install_collectibles_profile_support()
    install_collectibles_acquisition_support()
    install_collectibles_learned_recipe_support()
    install_collectibles_motif_support()
    install_collectibles_lorebook_support()
    install_collectibles_antiquity_support()
    install_application_update_support()

    from ui.main_window import MainWindow

    theme = ThemeManager()
    theme.apply(app)

    window = MainWindow()
    if not foundry_icon.isNull():
        window.setWindowIcon(foundry_icon)
    window.show()
    app.processEvents()

    _set_native_windows_icon(window, app_icon)

    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
