from types import SimpleNamespace

from ui.components.rotation_cadence_progression_card import (
    RotationCadenceProgressionCard,
)


def test_card_text_surfaces_latest_accepted_rationale_and_reasons() -> None:
    report = SimpleNamespace(
        advanced_steps=2,
        iterations=3,
        stop_summary="No eligible local cadence candidate improved the accepted rotation.",
        unresolved=(),
        steps=(
            SimpleNamespace(
                accepted=True,
                promoted_rationale="full coverage cadence",
                promoted_reasons=("eligible",),
            ),
            SimpleNamespace(
                accepted=True,
                promoted_rationale="target-floor cadence preserves sustain",
                promoted_reasons=("uptime obligation satisfied", "sustain improved"),
            ),
            SimpleNamespace(
                accepted=False,
                promoted_rationale="repeated schedule",
                promoted_reasons=("eligible",),
            ),
        ),
    )

    summary, detail = RotationCadenceProgressionCard.text_for_report(report)

    assert summary == (
        "2 accepted changes across 3 iterations. "
        "No eligible local cadence candidate improved the accepted rotation."
    )
    assert "Latest accepted change: target-floor cadence preserves sustain" in detail
    assert "Why it won: uptime obligation satisfied; sustain improved" in detail
    assert "repeated schedule" not in detail


def test_card_text_reports_no_change_and_unresolved_mechanics_without_inference() -> None:
    report = SimpleNamespace(
        advanced_steps=0,
        iterations=1,
        stop_summary="No eligible local cadence candidate improved the accepted rotation.",
        unresolved=("major_brittle duration unresolved", "target state unresolved"),
        steps=(
            SimpleNamespace(
                accepted=False,
                promoted_rationale=None,
                promoted_reasons=(),
            ),
        ),
    )

    summary, detail = RotationCadenceProgressionCard.text_for_report(report)

    assert summary.startswith("0 accepted changes across 1 iteration.")
    assert detail == "Unresolved mechanics: 2 item(s)."
