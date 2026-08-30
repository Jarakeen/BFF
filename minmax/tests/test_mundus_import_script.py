from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data" / "import_mundus_u50.py"


def test_mundus_import_script_runs_outside_repository_root(tmp_path):
    database = tmp_path / "eso.db"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(database)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Imported 13 Update 50 Mundus Stones" in completed.stdout
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM mundus_stone WHERE game_update = 50"
        ).fetchone()[0] == 13
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM mundus_effect me
            JOIN mundus_stone ms ON ms.id = me.mundus_id
            WHERE ms.game_update = 50
            """
        ).fetchone()[0] == 17
