from __future__ import annotations

"""Add portable application-update controls to Settings → About & Credits."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

from app_version import APP_VERSION
from services.application_update_service import ApplicationUpdateService
from ui.components.foundry_card import FoundryCard

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import settings_page

    original_about_page = settings_page.SettingsPage._about_page

    def about_page_with_updates(self):
        page = original_about_page(self)
        layout = page.layout()

        self.application_update_service = ApplicationUpdateService(APP_VERSION)
        self.application_update_info = None

        card = FoundryCard("APPLICATION UPDATES")
        version = QLabel(f"Current version: {APP_VERSION}")
        version.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card.addWidget(version)

        self.application_update_status = QLabel(
            "Updates are checked only when you press the button. Personal data, settings, builds, and eso.db are not replaced by portable updates."
        )
        self.application_update_status.setWordWrap(True)
        self.application_update_status.setProperty("muted", True)
        card.addWidget(self.application_update_status)

        self.check_application_update_button = QPushButton("Check for Updates")
        self.install_application_update_button = QPushButton("Download & Install Update")
        self.install_application_update_button.setProperty("primary", True)
        self.install_application_update_button.setEnabled(False)
        card.addWidget(self.check_application_update_button)
        card.addWidget(self.install_application_update_button)
        layout.addWidget(card)

        def check_for_update() -> None:
            self.check_application_update_button.setEnabled(False)
            self.application_update_status.setText("Checking GitHub Releases…")
            QApplication.processEvents()
            try:
                info = self.application_update_service.check()
            except Exception as exc:
                self.application_update_status.setText(f"Update check failed: {exc}")
                self.check_application_update_button.setEnabled(True)
                return

            self.application_update_info = info
            if info is None:
                self.application_update_status.setText(
                    "No published FoundryDock release is available yet."
                )
                self.install_application_update_button.setEnabled(False)
            elif not info.is_newer:
                self.application_update_status.setText(
                    f"FoundryDock {APP_VERSION} is current. Latest release: {info.tag or info.version}."
                )
                self.install_application_update_button.setEnabled(False)
            elif not info.asset_url:
                self.application_update_status.setText(
                    f"{info.tag or info.version} is newer, but that release does not contain FoundryDock-update.zip."
                )
                self.install_application_update_button.setEnabled(False)
            else:
                summary = (info.notes or "").strip().splitlines()
                note = summary[0].strip() if summary else ""
                message = f"Update available: {info.tag or info.version}."
                if note:
                    message += f" {note}"
                self.application_update_status.setText(message)
                self.install_application_update_button.setEnabled(True)
            self.check_application_update_button.setEnabled(True)

        def install_update() -> None:
            info = self.application_update_info
            if info is None or not info.is_newer or not info.asset_url:
                return

            answer = QMessageBox.question(
                self,
                "Install FoundryDock Update",
                f"Download and install {info.tag or info.version}?\n\n"
                "FoundryDock will close and restart. Personal data and eso.db will be left in place.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

            self.install_application_update_button.setEnabled(False)
            self.application_update_status.setText("Downloading update…")
            QApplication.processEvents()
            try:
                archive, digest = self.application_update_service.download(info)
                self.application_update_status.setText(
                    f"Downloaded. SHA-256 {digest[:12]}… Staging update…"
                )
                QApplication.processEvents()
                staged = self.application_update_service.stage(archive)
                log = self.application_update_service.launch_staged_install(staged)
            except Exception as exc:
                self.application_update_status.setText(f"Update installation failed: {exc}")
                self.install_application_update_button.setEnabled(True)
                return

            QMessageBox.information(
                self,
                "FoundryDock Updating",
                "The update is staged. FoundryDock will now close, apply the update, and restart.\n\n"
                f"Updater log: {log}",
            )
            QApplication.quit()

        self.check_application_update_button.clicked.connect(check_for_update)
        self.install_application_update_button.clicked.connect(install_update)
        return page

    settings_page.SettingsPage._about_page = about_page_with_updates
    _INSTALLED = True
