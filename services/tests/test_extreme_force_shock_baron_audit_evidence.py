from tools.audit_extreme_health_recovery_force_shock_baron_witness import (
    _contains,
    _normalize_eso_text,
)


def test_normalize_eso_color_markup_preserves_numeric_percent_evidence():
    assert _normalize_eso_text("Increases chance by |cffffff100|r%") == "increases chance by 100%"


def test_elemental_force_markup_is_searchable_after_normalization():
    row = {
        "name": "Elemental Force",
        "description": (
            "Increases your chance of applying Status Effects by |cffffff100|r% "
            "while you have a Destruction Staff equipped."
        ),
        "raw_tooltip": "",
        "raw_coef": "",
        "coef_types": "",
    }

    assert _contains(row, "status effects", "100%") is True


def test_nonmatching_rank_value_remains_rejected():
    row = {
        "name": "Elemental Force",
        "description": "Increases your chance of applying Status Effects by |cffffff50|r%.",
        "raw_tooltip": "",
        "raw_coef": "",
        "coef_types": "",
    }

    assert _contains(row, "status effects", "100%") is False
