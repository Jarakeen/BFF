from pathlib import Path


def test_raid_plan_overview_uses_editable_persistent_parchment_note() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert "self.plan_notes = QPlainTextEdit()" in source
    assert 'self.plan_notes.setProperty("parchmentEditor", True)' in source
    assert "return replace(plan, plan_note=note or None)" in source
    assert 'self.plan_notes.setPlainText(str(getattr(plan, "plan_note", "") or ""))' in source


def test_raid_plan_domain_and_repository_own_plan_note() -> None:
    model = Path("models/raid_plan.py").read_text(encoding="utf-8")
    repository = Path("services/raid_plan_repository.py").read_text(encoding="utf-8")
    persistence = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "plan_note: str | None = None" in model
    assert 'object.__setattr__(self, "plan_note", _optional(self.plan_note))' in model
    assert 'plan_note=raw.get("plan_note")' in repository
    assert "plan_note=loaded.plan_note" in persistence
