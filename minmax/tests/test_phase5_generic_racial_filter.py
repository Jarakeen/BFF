from __future__ import annotations

from types import SimpleNamespace

from ui.phase5_racial_filter_fix import _filtered_passive_rows_by_line


class _Reference:
    def list_skills(self):
        return [
            {
                "name": "Gift of Magnus",
                "skill_line": "Racial",
                "class_type": "",
                "is_player": 1,
                "is_passive": 1,
                "rank": 3,
            },
            {
                "name": "Resourceful",
                "skill_line": "Argonian Skills",
                "class_type": "",
                "is_player": 1,
                "is_passive": 1,
                "rank": 3,
            },
            {
                "name": "Rugged",
                "skill_line": "Racial Passives",
                "class_type": "",
                "is_player": 1,
                "is_passive": 1,
                "rank": 3,
            },
            {
                "name": "Mystery Heritage",
                "skill_line": "Racial",
                "class_type": "",
                "is_player": 1,
                "is_passive": 1,
                "rank": 1,
            },
            {
                "name": "Flourish",
                "skill_line": "Animal Companions",
                "class_type": "Warden",
                "is_player": 1,
                "is_passive": 1,
                "rank": 2,
            },
        ]


def test_racial_passive_identity_keeps_only_selected_character_race():
    dialog = SimpleNamespace(
        reference=_Reference(),
        race="Breton",
        eso_class="Warden",
        _race_skill_lines={"breton", "argonian", "nord"},
    )

    grouped = _filtered_passive_rows_by_line(dialog)

    assert [row["name"] for row in grouped["Breton Skills"]] == ["Gift of Magnus"]
    assert [row["name"] for row in grouped["Animal Companions"]] == ["Flourish"]
    assert all(
        row["name"] not in {"Resourceful", "Rugged", "Mystery Heritage"}
        for rows in grouped.values()
        for row in rows
    )
