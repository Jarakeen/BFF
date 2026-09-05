from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_novelty_evidence import CompBuilderNoveltyEvidenceService
from services.team_prescription_observed_templates import (
    OBSERVED_TEMPLATE_SCHEMA_VERSION,
    ObservedTeamTemplate,
    ObservedTeamTemplateSnapshot,
    ObservedTeamTemplateStore,
)


def _candidate(candidate_id: str, *, eso_class: str, gear_sets=()) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name=candidate_id,
        source_kind="reference_template",
        source_name="test",
        source_url="",
        eso_class=eso_class,
        role="Healer",
        gear_sets=tuple(gear_sets),
        skills=(),
        mundus="",
        complete_build=True,
        unresolved=(),
        score=100.0,
        score_reasons=(),
    )


def _observed(index: int, *, trial: str, eso_class: str, gear_sets=()):
    return ObservedTeamTemplate(
        template_id=f"obs-{index}",
        name=f"Observed {index}",
        source_name="ESO Logs",
        source_url=f"https://www.esologs.com/reports/report{index}",
        retrieved_at="2026-09-05T12:00:00+00:00",
        game_update="U51",
        trial_name=trial,
        encounter_name="Boss",
        report_code=f"report{index}",
        fight_id=index,
        observed_player_name=f"Player {index}",
        role="Healer",
        eso_class=eso_class,
        gear_sets=tuple(gear_sets),
        skills=(),
        mundus="",
        unknown_fields=(),
        source_score=100.0,
    )


def _save(tmp_path, rows) -> None:
    ObservedTeamTemplateStore(
        tmp_path / "team_prescription_observed_templates.json"
    ).save(
        ObservedTeamTemplateSnapshot(
            schema_version=OBSERVED_TEMPLATE_SCHEMA_VERSION,
            templates=tuple(rows),
        )
    )


def test_novelty_prefers_rare_class_and_gear_within_trial(tmp_path) -> None:
    rows = [
        _observed(i, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure",))
        for i in range(1, 5)
    ]
    rows.append(
        _observed(
            5,
            trial="Sunspire",
            eso_class="Necromancer",
            gear_sets=("Serpent's Disdain",),
        )
    )
    _save(tmp_path, rows)

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (
            _candidate("common", eso_class="Warden", gear_sets=("Spell Power Cure",)),
            _candidate("rare", eso_class="Necromancer", gear_sets=("Serpent's Disdain",)),
        ),
        role="Healer",
        trial_name="Sunspire",
    )

    scores = result.novelty_by_candidate
    assert scores["rare"] > scores["common"]
    assert result.sample_size == 5
    assert result.scope == "Sunspire healer observations"
    assert "Necromancer healer pairing observed 1/5 times" in result.evidence[1].reasons


def test_novelty_is_zero_when_observed_sample_is_too_small(tmp_path) -> None:
    _save(
        tmp_path,
        (
            _observed(1, trial="Sunspire", eso_class="Warden"),
            _observed(2, trial="Sunspire", eso_class="Necromancer"),
        ),
    )

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (_candidate("candidate", eso_class="Warden"),),
        role="Healer",
        trial_name="Sunspire",
    )

    assert result.novelty_by_candidate == {"candidate": 0.0}
    assert "insufficient observed sample" in result.evidence[0].reasons[0]


def test_novelty_falls_back_to_role_wide_corpus_when_trial_sample_is_small(tmp_path) -> None:
    _save(
        tmp_path,
        (
            _observed(1, trial="Sunspire", eso_class="Warden"),
            _observed(2, trial="Dreadsail Reef", eso_class="Warden"),
            _observed(3, trial="Rockgrove", eso_class="Necromancer"),
        ),
    )

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (_candidate("candidate", eso_class="Necromancer"),),
        role="Healer",
        trial_name="Sunspire",
    )

    assert result.sample_size == 3
    assert result.scope == "all observed healer setups"
    assert result.novelty_by_candidate["candidate"] > 0.0


def test_novelty_normalizes_perfected_and_standard_set_names(tmp_path) -> None:
    _save(
        tmp_path,
        (
            _observed(1, trial="Sunspire", eso_class="Warden", gear_sets=("Perfected Pillager's Profit",)),
            _observed(2, trial="Sunspire", eso_class="Warden", gear_sets=("Perfected Pillager's Profit",)),
            _observed(3, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure",)),
        ),
    )

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (_candidate("pillager", eso_class="Warden", gear_sets=("Pillager's Profit",)),),
        role="Healer",
        trial_name="Sunspire",
    )

    reasons = " | ".join(result.evidence[0].reasons)
    assert "observed 2/3 geared setups" in reasons


def test_novelty_rewards_uncommon_gear_pair_even_when_individual_sets_are_common(tmp_path) -> None:
    rows = (
        _observed(1, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
        _observed(2, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
        _observed(3, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
        _observed(4, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Serpent's Disdain")),
        _observed(5, trial="Sunspire", eso_class="Warden", gear_sets=("Pillager's Profit", "Serpent's Disdain")),
    )
    _save(tmp_path, rows)

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (
            _candidate(
                "common-pair",
                eso_class="Warden",
                gear_sets=("Spell Power Cure", "Pillager's Profit"),
            ),
            _candidate(
                "rare-pair",
                eso_class="Warden",
                gear_sets=("Spell Power Cure", "Serpent's Disdain"),
            ),
        ),
        role="Healer",
        trial_name="Sunspire",
    )

    assert result.novelty_by_candidate["rare-pair"] > result.novelty_by_candidate["common-pair"]
    rare_reasons = " | ".join(result.evidence[1].reasons)
    assert "gear pairing observed 1/5 multi-set setups" in rare_reasons


def test_provider_redistribution_novelty_is_explicitly_unavailable_without_canonical_evidence(tmp_path) -> None:
    _save(
        tmp_path,
        (
            _observed(1, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
            _observed(2, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
            _observed(3, trial="Sunspire", eso_class="Warden", gear_sets=("Spell Power Cure", "Pillager's Profit")),
        ),
    )

    result = CompBuilderNoveltyEvidenceService(tmp_path).evaluate_candidates(
        (
            _candidate(
                "candidate",
                eso_class="Warden",
                gear_sets=("Spell Power Cure", "Pillager's Profit"),
            ),
        ),
        role="Healer",
        trial_name="Sunspire",
    )

    reasons = " | ".join(result.evidence[0].reasons)
    assert "provider redistribution rarity unavailable" in reasons
    assert "canonical provider evidence" in reasons
