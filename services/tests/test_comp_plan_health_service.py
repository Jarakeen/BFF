from pathlib import Path
from types import SimpleNamespace
from minmax.gear_set_known_effects import known_effects_for_bonus_row

from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_plan_health_service import CompPlanHealthService
from services.raid_planned_gear_coverage_service import (
    PlannedGearCoverageProvider,
    RaidPlannedGearCoverageService,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


def test_equipped_ozezan_two_piece_minor_vitality_requires_both_pieces(monkeypatch, tmp_path) -> None:
    reviewed = known_effects_for_bonus_row(2000, 687, "Ozezan the Inferno", 2)
    assert any(effect.name == "minor_vitality" for effect in reviewed)
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (SimpleNamespace(
            source_name="Ozezan the Inferno", effect_key="minor_vitality", piece_count=2,
        ),),
    )
    service = RaidPlannedGearCoverageService(tmp_path / "eso.db")
    def provider(count):
        return PlannedGearCoverageProvider(
            seat_id="healer-1", provider_label="Jarakeen",
            gear_sets=("Ozezan the Inferno",), source_kind="saved build",
            equipped_piece_counts=(("Ozezan the Inferno", count),),
        )

    one_piece = service.overlay(service.empty_snapshot(("Minor Vitality",)),
                                (provider(1),), effect_names=("Minor Vitality",))
    two_piece = service.overlay(service.empty_snapshot(("Minor Vitality",)),
                                (provider(2),), effect_names=("Minor Vitality",))
    assert one_piece.conditional_providers["Minor Vitality"] == []
    assert two_piece.status["Minor Vitality"] == "conditional"
    assert two_piece.conditional_providers["Minor Vitality"] == [
        "Jarakeen [saved build: Ozezan the Inferno]"
    ]


def test_planned_gear_overlay_resolves_perfected_set_family_name(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(
                source_name="Roaring Opportunist",
                effect_key="major_slayer",
            ),
        ),
    )

    service = RaidPlannedGearCoverageService(tmp_path / "eso.db")
    snapshot = service.empty_snapshot(("Major Slayer",))
    result = service.overlay(
        snapshot,
        (
            PlannedGearCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                gear_sets=("Perfected Roaring Opportunist",),
            ),
        ),
        effect_names=("Major Slayer",),
    )

    assert result.status["Major Slayer"] == "conditional"
    assert result.providers["Major Slayer"] == []
    assert result.conditional_providers["Major Slayer"] == [
        "Magrat [planned: Perfected Roaring Opportunist]"
    ]


def test_planned_unique_support_set_keeps_provider_identity(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (),
    )

    service = RaidPlannedGearCoverageService(tmp_path / "eso.db")
    snapshot = service.empty_snapshot(("Jorvuld's Guidance",))
    result = service.overlay(
        snapshot,
        (
            PlannedGearCoverageProvider(
                seat_id="healer-1",
                provider_label="Magrat",
                gear_sets=("Jorvuld's Guidance",),
            ),
        ),
        effect_names=("Jorvuld's Guidance",),
    )

    assert result.status["Jorvuld's Guidance"] == "conditional"
    assert result.conditional_providers["Jorvuld's Guidance"] == [
        "Magrat [planned: Jorvuld's Guidance]"
    ]


def test_comp_plan_health_uses_canonical_state_for_open_players_and_gear(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (),
    )

    state = CompPlanState(
        raid_plan_id="swash",
        raid_plan_name="Swash",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(
                seat_id="tank-1",
                player_name="Tank",
                role="Tank",
                planned_gear_sets=("Pearlescent Ward",),
            ),
            CompChairState(
                seat_id="healer-1",
                player_name="Healer",
                role="Healer",
                planned_gear_sets=("Jorvuld's Guidance",),
            ),
            CompChairState(
                seat_id="dd-1",
                player_name="",
                role="Damage",
                planned_gear_sets=("Elemental Catalyst",),
            ),
            CompChairState(
                seat_id="dd-2",
                player_name="Recruit",
                role="Damage",
            ),
        ),
    )

    health = CompPlanHealthService(tmp_path / "eso.db").evaluate(state)

    assert health.open_player_seats == ("dd-1", "dd-2")
    assert health.open_gear_seats == ("dd-2",)
    assert "Pearlescent Ward" in dict(health.coverage_status)
    providers = dict(health.providers_by_effect)
    assert providers["Jorvuld's Guidance"] == (
        "Healer [planned: Jorvuld's Guidance]",
    )


def test_comp_plan_health_detects_duplicate_effect_sources(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(source_name="Spell Power Cure", effect_key="major_courage"),
            SimpleNamespace(source_name="Vestment of Olorime", effect_key="major_courage"),
        ),
    )

    state = CompPlanState(
        raid_plan_id="dup",
        raid_plan_name="Duplicate Test",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="H1",
                planned_gear_sets=("Spell Power Cure",),
            ),
            CompChairState(
                seat_id="healer-2",
                player_name="H2",
                planned_gear_sets=("Vestment of Olorime",),
            ),
        ),
    )

    health = CompPlanHealthService(tmp_path / "eso.db").evaluate(state)

    assert "Major Courage" in health.duplicate_effects
    assert "Major Courage" in health.conditional_required


def test_comp_assignment_review_distinguishes_planned_source_from_unproven_assignment(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(
                source_name="Roaring Opportunist",
                effect_key="major_slayer",
            ),
        ),
    )

    supported = CompPlanState(
        raid_plan_id="supported",
        raid_plan_name="Supported",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="H1",
                planned_gear_sets=("Perfected Roaring Opportunist",),
                primary_assignment="Major Slayer",
            ),
        ),
    )
    supported_health = CompPlanHealthService(tmp_path / "eso.db").evaluate(supported)
    supported_review = next(
        row for row in supported_health.assignment_reviews
        if row.effect_name == "Major Slayer"
    )
    assert supported_review.state == "assigned_conditional"
    assert "Major Slayer" in supported_health.planned_required
    assert "Major Slayer" not in supported_health.missing_required
    assert supported_review.supported_primary == ("healer-1",)
    assert supported_review.unsupported_primary == ()

    unproven = CompPlanState(
        raid_plan_id="unproven",
        raid_plan_name="Unproven",
        trial_id="Dreadsail Reef",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="H1",
                planned_gear_sets=("Spell Power Cure",),
                primary_assignment="Major Slayer",
            ),
        ),
    )
    unproven_health = CompPlanHealthService(tmp_path / "eso.db").evaluate(unproven)
    unproven_review = next(
        row for row in unproven_health.assignment_reviews
        if row.effect_name == "Major Slayer"
    )
    assert unproven_review.state == "assigned_unproven"
    assert unproven_review.label == "Covered • Planned"
    assert "Major Slayer" in unproven_health.planned_required
    assert "Major Slayer" not in unproven_health.missing_required
    assert unproven_review.unsupported_primary == ("healer-1",)


def test_comp_assignment_review_detects_duplicate_primary_ownership(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "services.raid_planned_gear_coverage_service."
        "NonAbilityEffectProviderReferenceService.gear",
        lambda self: (
            SimpleNamespace(
                source_name="Spell Power Cure",
                effect_key="major_courage",
            ),
        ),
    )

    state = CompPlanState(
        raid_plan_id="dupe-assignment",
        raid_plan_name="Dupe Assignment",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="H1",
                planned_gear_sets=("Spell Power Cure",),
                primary_assignment="Major Courage",
            ),
            CompChairState(
                seat_id="healer-2",
                player_name="H2",
                planned_gear_sets=("Spell Power Cure",),
                primary_assignment="Major Courage",
            ),
        ),
    )

    health = CompPlanHealthService(tmp_path / "eso.db").evaluate(state)
    review = next(
        row for row in health.assignment_reviews
        if row.effect_name == "Major Courage"
    )

    assert review.duplicate_primary is True
    assert review.primary_seats == ("healer-1", "healer-2")
    assert "Duplicate primary" in review.label
