from tools.audit_phase6_other_richer_semantics import detail_category
from tools.audit_phase6_richer_semantics_taxonomy import RicherSemanticsTaxonomyRow


def _row(fragment: str, *, effect_kind: str | None = "damage", signals=()):
    return RicherSemanticsTaxonomyRow(
        skill_rank_id=1,
        coefficient_number=1,
        ability_id=10,
        ability_name="Example",
        category="other_richer_semantics",
        effect_kind=effect_kind,
        signals=tuple(signals),
        fragment=fragment,
    )


def test_periodic_damage_precedes_generic_duration_bucket():
    row = _row("Deal $1 Shock Damage every 2 seconds for 20 seconds.")
    assert detail_category(row) == "periodic_damage_classification_gap"


def test_damage_scaling_wording_is_preserved_as_candidate():
    row = _row("Deal $1 Magic Damage, increasing based on your missing Health.")
    assert detail_category(row) == "damage_scaling_or_modifier_candidate"


def test_plain_direct_damage_is_classification_gap():
    row = _row("Strike the enemy, dealing $1 Physical Damage.")
    assert detail_category(row) == "direct_damage_classification_gap"


def test_secondary_wording_without_known_damage_kind_stays_candidate():
    row = _row("You also gain an additional benefit.", effect_kind=None)
    assert detail_category(row) == "secondary_wording_candidate"


def test_status_wording_is_case_insensitive():
    row = _row("Apply the Chilled status effect.", effect_kind=None)
    assert detail_category(row) == "named_or_status_effect_wording"


def test_signal_only_row_remains_visible():
    row = _row("Special unresolved behavior.", effect_kind=None, signals=("healing_candidate",))
    assert detail_category(row) == "signal_only_candidate"
