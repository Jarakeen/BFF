import json
from pathlib import Path

from tools.rebuild_uesp_alchemy_effects_safe import (
    candidate_required_failures,
    promote_candidate,
)


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_candidate_required_failures_reads_v3_validation_contract():
    payload = {"validation": {"missing_non_optional": ["Timidity", "Restore Magicka"]}}
    assert candidate_required_failures(payload) == ("Timidity", "Restore Magicka")


def test_incomplete_candidate_is_not_promoted(tmp_path: Path):
    output = tmp_path / "alchemy_effects.json"
    candidate = tmp_path / "candidate.json"
    _write(output, {"effects": [{"effect_name": "existing"}]})
    _write(
        candidate,
        {
            "effects": [{"effect_name": "partial"}],
            "validation": {"missing_non_optional": ["Restore Stamina"]},
        },
    )

    promoted, failures = promote_candidate(candidate=candidate, output=output)

    assert promoted is False
    assert failures == ("Restore Stamina",)
    assert json.loads(output.read_text(encoding="utf-8"))["effects"][0]["effect_name"] == "existing"
    assert candidate.exists()


def test_valid_candidate_atomically_replaces_authoritative_output(tmp_path: Path):
    output = tmp_path / "alchemy_effects.json"
    candidate = tmp_path / "candidate.json"
    _write(output, {"effects": [{"effect_name": "old"}]})
    _write(
        candidate,
        {
            "effects": [{"effect_name": "Restore Magicka"}, {"effect_name": "Spell Critical"}],
            "validation": {"missing_non_optional": []},
        },
    )

    promoted, failures = promote_candidate(candidate=candidate, output=output)

    assert promoted is True
    assert failures == ()
    assert not candidate.exists()
    names = [item["effect_name"] for item in json.loads(output.read_text(encoding="utf-8"))["effects"]]
    assert names == ["Restore Magicka", "Spell Critical"]
