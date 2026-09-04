from __future__ import annotations


_INSTALLED = False
_ORIGINAL_GENERATE = None


def should_auto_anchor_hybrid_players(
    *,
    source_mode: str,
    saved_player_count: int,
    recruitment_count: int,
    explicit_lock_players: bool,
) -> bool:
    """Return whether a mixed visible Hybrid team should preserve its saved players.

    Hybrid is meant to express "these are the people I have; prescribe the rest."
    When the visible team already contains both saved players and recruitment chairs,
    requiring a second hidden Lock Players step is surprising. Full saved teams still
    obey the explicit Lock Players checkbox so Build Best Team can optimize normally.
    """

    return (
        str(source_mode or "").strip() == "Hybrid: Players + Recruitment"
        and int(saved_player_count) > 0
        and int(recruitment_count) > 0
        and not bool(explicit_lock_players)
    )


def _generate_with_hybrid_visible_players_preserved(self, *args):
    assert _ORIGINAL_GENERATE is not None

    explicit_lock = self.constraint_boxes["Lock Players"].isChecked()
    saved_count, recruitment_count = self._team_counts(self.team_table)
    auto_anchor = should_auto_anchor_hybrid_players(
        source_mode=self._effective_source_mode(),
        saved_player_count=saved_count,
        recruitment_count=recruitment_count,
        explicit_lock_players=explicit_lock,
    )

    if not auto_anchor:
        return _ORIGINAL_GENERATE(self, *args)

    # Temporarily use the existing, tested Lock Players path. The UI checkbox is
    # restored immediately after generation, so this is a mode semantic rather than
    # a hidden permanent setting: visible saved players + visible recruit chairs means
    # "keep these people and prescribe the open chairs."
    self.constraint_boxes["Lock Players"].setChecked(True)
    try:
        result = _ORIGINAL_GENERATE(self, *args)
    finally:
        self.constraint_boxes["Lock Players"].setChecked(False)

    return result


def install() -> None:
    global _INSTALLED, _ORIGINAL_GENERATE
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_GENERATE = OptimizationPage._generate_prescription_preview
    OptimizationPage._generate_prescription_preview = (
        _generate_with_hybrid_visible_players_preserved
    )
    _INSTALLED = True
