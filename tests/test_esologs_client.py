from services.esologs_client import EsoLogsClient


def test_normalize_report_code_accepts_raw_code() -> None:
    assert EsoLogsClient.normalize_report_code("FPy6Tc9BzwQNbfVK") == "FPy6Tc9BzwQNbfVK"


def test_normalize_report_code_accepts_report_url() -> None:
    assert (
        EsoLogsClient.normalize_report_code(
            "https://www.esologs.com/reports/FPy6Tc9BzwQNbfVK"
        )
        == "FPy6Tc9BzwQNbfVK"
    )


def test_normalize_report_code_accepts_trailing_slash() -> None:
    assert (
        EsoLogsClient.normalize_report_code(
            "https://www.esologs.com/reports/FPy6Tc9BzwQNbfVK/"
        )
        == "FPy6Tc9BzwQNbfVK"
    )
