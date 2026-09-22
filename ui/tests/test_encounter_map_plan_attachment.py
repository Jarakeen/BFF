from __future__ import annotations

import json
from pathlib import Path


def test_encounter_board_persists_optional_raid_plan_context() -> None:
    source = Path("ui/components/encounter_board.py").read_text(encoding="utf-8")

    assert 'self.raid_plan_id = ""' in source
    assert '"raid_plan_id": str(getattr(self, "raid_plan_id", "") or "").strip()' in source
    assert 'self.raid_plan_id = str(payload.get("raid_plan_id") or "").strip()' in source


def test_encounters_header_has_nullable_raid_plan_selector() -> None:
    source = Path("ui/encounters_page.py").read_text(encoding="utf-8")

    assert 'self.raid_plan_combo.addItem("None", "")' in source
    assert 'self._context_box("RAID PLAN", self.raid_plan_combo)' in source
    assert "self.encounter_board.raid_plan_id" in source


def test_encounter_map_can_attach_directly_to_mechanics_and_live_plan() -> None:
    source = Path("ui/encounters_page.py").read_text(encoding="utf-8")

    assert 'QPushButton("Attach to…")' in source
    assert 'button.text().strip() == "Upload Map"' in source
    assert "self.encounter_board.capture_snapshot()" in source
    assert "self.raid_map_store.import_map(" in source
    assert "self.raid_section_state.set_linked_raid_map_id(" in source
    assert '"Mechanics & Timelines encounter:"' in source
