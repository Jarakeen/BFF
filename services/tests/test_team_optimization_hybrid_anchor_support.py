from ui.team_optimization_hybrid_anchor_support import (
    should_auto_anchor_hybrid_players,
)


def test_partial_hybrid_team_auto_anchors_visible_saved_players() -> None:
    assert should_auto_anchor_hybrid_players(
        source_mode="Hybrid: Players + Recruitment",
        saved_player_count=2,
        recruitment_count=10,
        explicit_lock_players=False,
    )


def test_full_saved_hybrid_team_does_not_implicitly_lock_players() -> None:
    assert not should_auto_anchor_hybrid_players(
        source_mode="Hybrid: Players + Recruitment",
        saved_player_count=12,
        recruitment_count=0,
        explicit_lock_players=False,
    )


def test_recruitment_only_team_does_not_need_saved_player_anchor() -> None:
    assert not should_auto_anchor_hybrid_players(
        source_mode="Recruitment Plan Only",
        saved_player_count=0,
        recruitment_count=12,
        explicit_lock_players=False,
    )


def test_explicit_lock_remains_authoritative() -> None:
    assert not should_auto_anchor_hybrid_players(
        source_mode="Hybrid: Players + Recruitment",
        saved_player_count=2,
        recruitment_count=10,
        explicit_lock_players=True,
    )
