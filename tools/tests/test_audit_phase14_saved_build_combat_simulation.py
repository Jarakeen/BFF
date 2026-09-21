from __future__ import annotations

import json

from tools import audit_phase14_saved_build_combat_simulation as audit


def test_saved_dd_builds_lists_only_damage_roles(tmp_path) -> None:
    path = tmp_path / "builds.json"
    path.write_text(
        json.dumps(
            {
                "Members": [
                    {
                        "Name": "Rylonia",
                        "BuildName": "Corpsebuster DD",
                        "Role": "DD",
                    },
                    {
                        "Name": "Magrat",
                        "BuildName": "DF Healer",
                        "Role": "Healer",
                    },
                    {
                        "Name": "Other",
                        "BuildName": "Damage Build",
                        "Role": "damage dealer",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    builds = audit._saved_dd_builds(path)

    assert [
        (audit._character_name(build), build.BuildName, build.Role)
        for build in builds
    ] == [
        ("Other", "Damage Build", "damage dealer"),
        ("Rylonia", "Corpsebuster DD", "DD"),
    ]


def test_print_saved_dd_builds_returns_nonzero_when_none_exist(
    tmp_path,
    capsys,
) -> None:
    path = tmp_path / "builds.json"
    path.write_text(json.dumps({"Members": []}), encoding="utf-8")

    code = audit._print_saved_dd_builds(path)
    output = capsys.readouterr().out

    assert code == 1
    assert "none" in output
