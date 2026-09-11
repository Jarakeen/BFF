from pathlib import Path
from types import SimpleNamespace
import json

from services.esologs_event_interpreter import SemanticEventKind
from tools.discover_phase13_healer_refresh_evidence_windows import (
    RefreshEvidenceWindow,
    _candidate_casters,
    _corpus_fights,
)


def test_corpus_fights_enumerates_reports_and_fights(tmp_path: Path):
    path = tmp_path / "corpus.json"
    path.write_text(
        json.dumps(
            {
                "reports": {
                    "B": {"fights": {"9": {}, "2": {}}},
                    "A": {"fights": {"5": {}}},
                }
            }
        ),
        encoding="utf-8",
    )

    assert _corpus_fights(path) == (("A", 5), ("B", 2), ("B", 9))


def test_candidate_casters_uses_semantic_cast_kind_and_aliases():
    events = (
        SimpleNamespace(
            source_id=7,
            source_is_friendly=True,
            ability_game_id=100,
            event_kind=SemanticEventKind.CAST,
        ),
        SimpleNamespace(
            source_id=8,
            source_is_friendly=True,
            ability_game_id=101,
            event_kind=SemanticEventKind.CAST,
        ),
        SimpleNamespace(
            source_id=9,
            source_is_friendly=False,
            ability_game_id=100,
            event_kind=SemanticEventKind.CAST,
        ),
        SimpleNamespace(
            source_id=10,
            source_is_friendly=True,
            ability_game_id=100,
            event_kind=SemanticEventKind.HEAL,
        ),
    )

    assert _candidate_casters(events, (100, 101)) == (7, 8)


def test_discovery_ranking_prefers_restart_shape_then_phase_separation():
    restart_wide = RefreshEvidenceWindow(
        source_name="Budding Seeds",
        coefficient_number=2,
        report_code="A",
        fight_id=1,
        caster_id=7,
        recipient_id=20,
        cast_gap_seconds=4.0,
        recast_time_seconds=10.0,
        phase_separation_seconds=0.40,
        shape="reapplied-restart-shaped",
        restart_delta_seconds=0.01,
        old_delta_seconds=0.35,
        post_tick_offsets_seconds=(0.06, 1.06),
    )
    restart_narrow = RefreshEvidenceWindow(
        source_name="Budding Seeds",
        coefficient_number=2,
        report_code="A",
        fight_id=2,
        caster_id=7,
        recipient_id=21,
        cast_gap_seconds=4.0,
        recast_time_seconds=20.0,
        phase_separation_seconds=0.20,
        shape="reapplied-restart-shaped",
        restart_delta_seconds=0.01,
        old_delta_seconds=0.18,
        post_tick_offsets_seconds=(0.06, 1.06),
    )
    ambiguous = RefreshEvidenceWindow(
        source_name="Budding Seeds",
        coefficient_number=2,
        report_code="A",
        fight_id=3,
        caster_id=7,
        recipient_id=22,
        cast_gap_seconds=4.0,
        recast_time_seconds=30.0,
        phase_separation_seconds=0.49,
        shape="phase-ambiguous",
        restart_delta_seconds=0.01,
        old_delta_seconds=0.02,
        post_tick_offsets_seconds=(0.06, 1.06),
    )

    ordered = sorted((ambiguous, restart_narrow, restart_wide), key=lambda row: row.score)
    assert ordered == [restart_wide, restart_narrow, ambiguous]
