import json

import pytest

from tools.audit_phase13_detonating_siphon_controlled_spatial_evidence import load_samples


def test_load_samples_builds_controlled_observations(tmp_path) -> None:
    path = tmp_path / "samples.json"
    path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "label": "caster_only",
                        "caster": [0, 0],
                        "corpse_candidate": [20, 0],
                        "target": [2, 0],
                        "damage_observed": True,
                    },
                    {
                        "label": "interior_no_hit",
                        "caster": [0, 0],
                        "corpse_candidate": [20, 0],
                        "target": [10, 3],
                        "damage_observed": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    samples = load_samples(path)

    assert len(samples) == 2
    assert samples[0].label == "caster_only"
    assert samples[0].caster == (0.0, 0.0)
    assert samples[0].corpse_candidate == (20.0, 0.0)
    assert samples[0].target == (2.0, 0.0)
    assert samples[0].damage_observed is True
    assert samples[1].damage_observed is False


def test_load_samples_requires_samples_array(tmp_path) -> None:
    path = tmp_path / "samples.json"
    path.write_text(json.dumps({"rows": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="samples array"):
        load_samples(path)


def test_load_samples_reports_missing_required_field(tmp_path) -> None:
    path = tmp_path / "samples.json"
    path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "label": "broken",
                        "caster": [0, 0],
                        "corpse_candidate": [20, 0],
                        "damage_observed": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required field 'target'"):
        load_samples(path)
