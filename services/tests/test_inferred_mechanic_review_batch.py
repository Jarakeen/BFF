from __future__ import annotations

import json
from pathlib import Path

from tools.apply_inferred_mechanic_review_batch import apply_review_batch


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_apply_review_batch_changes_only_pending_rows(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    batch = tmp_path / "batch.json"
    _write(
        manifest,
        {
            "decisions": [
                {"encounter_id": "a", "mechanic_name": "one", "status": "pending", "rationale": ""},
                {"encounter_id": "b", "mechanic_name": "two", "status": "accepted", "rationale": "human"},
            ]
        },
    )
    _write(
        batch,
        {
            "decisions": [
                {"encounter_id": "a", "mechanic_name": "one", "status": "rejected", "rationale": "unsupported field"},
                {"encounter_id": "b", "mechanic_name": "two", "status": "rejected", "rationale": "batch must not replace human decision"},
            ]
        },
    )

    assert apply_review_batch(manifest, batch) == (1, 1)
    rows = json.loads(manifest.read_text(encoding="utf-8"))["decisions"]
    assert rows[0]["status"] == "rejected"
    assert rows[0]["rationale"] == "unsupported field"
    assert rows[1]["status"] == "accepted"
    assert rows[1]["rationale"] == "human"


def test_apply_review_batch_rejects_unknown_key(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    batch = tmp_path / "batch.json"
    _write(manifest, {"decisions": []})
    _write(
        batch,
        {"decisions": [{"encounter_id": "x", "mechanic_name": "missing", "status": "accepted", "rationale": "reviewed"}]},
    )

    try:
        apply_review_batch(manifest, batch)
    except ValueError as exc:
        assert "not present in manifest" in str(exc)
    else:
        raise AssertionError("expected ValueError")
