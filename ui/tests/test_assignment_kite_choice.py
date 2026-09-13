from pathlib import Path


def test_assignments_include_kite_autocomplete_choice() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    assert '("Kite", "mechanic:kite")' in source
    assert 'Qt.MatchFlag.MatchContains' in source
    assert 'QCompleter.CompletionMode.PopupCompletion' in source
