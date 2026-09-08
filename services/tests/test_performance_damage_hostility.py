from services.performance_dashboard_service import ROLE_OUTPUT


def test_dps_damage_queries_friendly_sources() -> None:
    assert ROLE_OUTPUT["DPS"] == ("DamageDone", "Friendlies", "Damage", "DPS")


def test_tank_damage_queries_friendly_sources() -> None:
    assert ROLE_OUTPUT["Tank"] == ("DamageDone", "Friendlies", "Damage", "DPS")


def test_healer_output_remains_friendly_healing() -> None:
    assert ROLE_OUTPUT["Healer"] == ("Healing", "Friendlies", "Healing", "HPS")
