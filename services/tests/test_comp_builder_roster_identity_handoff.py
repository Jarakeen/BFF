from __future__ import annotations

from pathlib import Path

from models.comp_plan_state import CompChairState, CompPlanState


def test_roster_intake_carries_canonical_identity_into_comp_state() -> None:
    source = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")

    assert 'getattr(member, "CanonicalPlayerId", "")' in source
    assert 'getattr(member, "CanonicalCharacterId", "")' in source
    assert 'changes["roster_member_id"] = member_id' in source
    assert 'changes["player_id"] = canonical_player_id' in source
    assert 'changes["character_id"] = canonical_character_id' in source


def test_comp_chair_accepts_stable_roster_identity() -> None:
    chair = CompChairState(
        seat_id="DD1",
        player_name="Rylo",
        roster_member_id=7,
        player_id="player-rylo",
        character_id="character-rylo",
        character_name="Rylo Character",
        role="DD",
        eso_class="Arcanist",
    )
    state = CompPlanState(
        raid_plan_id=None,
        raid_plan_name="Performance Mode",
        trial_id="Rockgrove",
        chairs=(chair,),
        dirty=True,
    )

    restored = state.chair("DD1")
    assert restored is not None
    assert restored.roster_member_id == 7
    assert restored.player_id == "player-rylo"
    assert restored.character_id == "character-rylo"
