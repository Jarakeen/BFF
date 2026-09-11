from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_runtime_mechanics_page_survives_real_mechanics_support_stack():
    """Exercise the runtime page after the same Mechanics wrappers app.py installs.

    Run in a subprocess so global monkey patches from the support installers cannot
    leak into the rest of the UI test process.
    """

    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    script = textwrap.dedent(
        r'''
        from types import SimpleNamespace

        from PySide6.QtWidgets import QApplication

        from services.encounter_runtime_guide_projection_service import (
            EncounterGuideRuntimeProjection,
        )
        from services.expedition_service import ExpeditionService
        from ui.mechanics_boss_map_support import install as install_mechanics_boss_map_support
        from ui.mechanics_search_support import install as install_mechanics_search_support

        app = QApplication.instance() or QApplication([])

        # Match app.py ordering: boss/map support first, search/evidence support second.
        install_mechanics_boss_map_support()
        install_mechanics_search_support()

        # Import the runtime-aware subclass only after the base Mechanics support
        # stack has been installed, matching MainWindow startup.
        from ui.mechanics_runtime_page import RuntimeMechanicsPage


        class GuideService:
            def encounter_summaries(self):
                return (
                    SimpleNamespace(
                        encounter_id="lokkestiiz",
                        content_id="sunspire",
                        content_name="Sunspire",
                        name="Lokkestiiz",
                        location="Sunspire",
                    ),
                )

            def get(self, encounter_id: str):
                assert encounter_id == "lokkestiiz"
                return SimpleNamespace(
                    encounter_id="lokkestiiz",
                    content_id="sunspire",
                    content_name="Sunspire",
                    name="Lokkestiiz",
                    summary="Dragon encounter.",
                    location="Sunspire",
                    health=(("veteran", "1"),),
                    source_revision_id="test",
                    abilities=(),
                    phases=(),
                )


        class RuntimeGuideService:
            def get(self, encounter_id: str):
                assert encounter_id == "lokkestiiz"
                # Deliberately return no runtime evidence. This exercises the
                # clear path that previously dereferenced a deleted QLabel.
                return EncounterGuideRuntimeProjection(
                    encounter_id=encounter_id,
                    notes=(),
                    role_guidance=(),
                    source_labels=(),
                    successful_kills=0,
                    reviewed_windows=0,
                    limitations=(),
                )


        page = RuntimeMechanicsPage(
            expedition=ExpeditionService(),
            guide_service=GuideService(),
            runtime_guide_service=RuntimeGuideService(),
        )

        # Repeat the paths used when navigating to Mechanics and changing boss
        # context. Any libshiboken deleted-widget error will fail this process.
        page.refresh_context()
        page._boss_changed(page.boss_combo.currentIndex())
        page._clear_runtime_strategy()

        assert page.tabs.tabText(2) == "STRATEGY"
        assert page.runtime_notes_table.rowCount() == 0
        assert page.runtime_guidance_table.rowCount() == 0

        page.close()
        app.processEvents()
        '''
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, (
        "Mechanics runtime support-stack subprocess failed.\n"
        f"STDOUT:\n{completed.stdout}\n"
        f"STDERR:\n{completed.stderr}"
    )
