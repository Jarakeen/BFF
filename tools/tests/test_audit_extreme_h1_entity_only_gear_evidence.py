from __future__ import annotations

from tools.audit_extreme_h1_entity_only_gear_evidence import build_review


def test_entity_only_gear_evidence_review_tracks_pairs_and_non_arena_rows() -> None:
    rows = [
        {
            "name": "Grand Rejuvenation",
            "type": "Arena",
            "location": "Dragonstar Arena",
            "bonuses": ["(2 items) Restore resources."],
            "modified_skills": ["Grand Healing"],
            "unresolved": [],
        },
        {
            "name": "Perfected Grand Rejuvenation",
            "type": "Arena",
            "location": "Dragonstar Arena",
            "bonuses": [
                "(2 items) Adds Maximum Magicka.",
                "(2 items) Restore resources.",
            ],
            "modified_skills": ["Grand Healing"],
            "unresolved": [],
        },
        {
            "name": "Odd Set",
            "type": "Mythic",
            "location": "",
            "bonuses": ["(1 item) Something."],
            "modified_skills": [],
            "unresolved": [],
        },
    ]

    review = build_review(rows)

    assert review["row_count"] == 3
    assert review["type_counts"] == {"Arena": 2, "Mythic": 1}
    assert review["perfected_pair_count"] == 1
    assert review["unpaired"] == [("Odd Set", ("Odd Set",))]
    assert review["non_arena"][0][0] == "Odd Set"
    assert review["no_modified_skills"] == ["Odd Set"]
