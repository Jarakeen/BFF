from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from importers.import_uesp_rumors import import_rumors, parse_uesp_table


RUMORS_HTML = """
<html><body>
<table id="esologtable">
<thead><tr>
<th></th><th>id</th><th>type</th><th>name</th><th>startHint</th>
<th>backgroundText</th><th>completeText</th><th>numHints</th><th></th>
</tr></thead>
<tbody>
<tr>
<td>View</td><td>1</td><td>1</td><td>The Beriel Heirloom</td>
<td>Find a broadsheet.</td><td>Background.</td><td>Complete.</td><td>2</td><td>View Hints</td>
</tr>
<tr>
<td>View</td><td>7</td><td>1</td><td>Letter-Crossed Lovers</td>
<td>A tale of love.</td><td>Background.</td><td>Complete.</td><td>0</td><td>View Hints</td>
</tr>
</tbody>
</table>
</body></html>
"""

HINTS_HTML = """
<html><body>
<table id="esologtable">
<thead><tr>
<th></th><th>id</th><th>rumorId</th><th>hintIndex</th><th>rumorName</th>
<th>name</th><th>description</th><th>icon</th><th>book</th><th></th>
</tr></thead>
<tbody>
<tr>
<td>View</td><td>1</td><td>1</td><td>1</td><td>The Beriel Heirloom</td>
<td>Burglary in Camlorn!</td><td>An article from a broadsheet.</td>
<td><a href="//esoicons.uesp.net/esoui/art/icons/scroll_001.png"><img src="//esoicons.uesp.net/esoui/art/icons/scroll_001.png"></a></td>
<td>8379</td><td><a href="?action=view&amp;record=book&amp;bookId=8379">View Book</a></td>
</tr>
<tr>
<td>View</td><td>2</td><td>1</td><td>2</td><td>The Beriel Heirloom</td>
<td></td><td></td><td></td><td></td><td>View Rumor</td>
</tr>
</tbody>
</table>
</body></html>
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_parser_reads_uesp_table_and_link_metadata(tmp_path: Path) -> None:
    path = _write(tmp_path / "hints.htm", HINTS_HTML)
    rows = parse_uesp_table(path)

    assert len(rows) == 2
    assert rows[0]["rumorName"].text == "The Beriel Heirloom"
    assert rows[0]["icon"].image_sources == [
        "//esoicons.uesp.net/esoui/art/icons/scroll_001.png"
    ]
    assert "bookId=8379" in rows[0][""].hrefs[0]


def test_import_is_additive_and_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "eso.db"
    rumors_path = _write(tmp_path / "rumors.htm", RUMORS_HTML)
    hints_path = _write(tmp_path / "rumorhints.htm", HINTS_HTML)

    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO unrelated VALUES (1, 'keep me')")
        db.commit()

    assert import_rumors(db_path, rumors_path, hints_path) == (2, 2)
    assert import_rumors(db_path, rumors_path, hints_path) == (2, 2)

    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT value FROM unrelated WHERE id=1").fetchone()[0] == "keep me"
        assert db.execute("SELECT COUNT(*) FROM collectible_rumor").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM collectible_rumor_hint").fetchone()[0] == 2

        rumor = db.execute(
            "SELECT name, declared_hint_count FROM collectible_rumor WHERE id=1"
        ).fetchone()
        assert rumor == ("The Beriel Heirloom", 2)

        hint = db.execute(
            """
            SELECT hint_index, name, icon, book_id
            FROM collectible_rumor_hint
            WHERE id=1
            """
        ).fetchone()
        assert hint == (
            1,
            "Burglary in Camlorn!",
            "https://esoicons.uesp.net/esoui/art/icons/scroll_001.png",
            8379,
        )

        assert db.execute(
            "SELECT 1 FROM schema_migration WHERE migration_key='collectible_rumors_v1'"
        ).fetchone() is not None


def test_import_rolls_back_on_declared_hint_count_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "eso.db"
    rumors_path = _write(
        tmp_path / "rumors.htm",
        RUMORS_HTML.replace("<td>2</td><td>View Hints</td>", "<td>3</td><td>View Hints</td>", 1),
    )
    hints_path = _write(tmp_path / "rumorhints.htm", HINTS_HTML)

    with pytest.raises(ValueError, match="Rumor hint-count mismatch"):
        import_rumors(db_path, rumors_path, hints_path)

    with sqlite3.connect(db_path) as db:
        rumor_table = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='collectible_rumor'"
        ).fetchone()
        if rumor_table is not None:
            assert db.execute("SELECT COUNT(*) FROM collectible_rumor").fetchone()[0] == 0


def test_import_rejects_hint_for_missing_parent(tmp_path: Path) -> None:
    db_path = tmp_path / "eso.db"
    rumors_path = _write(tmp_path / "rumors.htm", RUMORS_HTML)
    hints_path = _write(
        tmp_path / "rumorhints.htm",
        HINTS_HTML.replace("<td>1</td><td>1</td><td>The Beriel Heirloom</td>", "<td>99</td><td>1</td><td>The Beriel Heirloom</td>", 1),
    )

    with pytest.raises(ValueError, match="references missing rumor 99"):
        import_rumors(db_path, rumors_path, hints_path)
