from models.build_model import PlayerBuild
from tools.audit_phase5_resolution_matrix import _is_template_build


def test_obvious_template_build_is_excluded_from_authoritative_roster():
    assert _is_template_build(
        PlayerBuild(Name="YOUR TANK BUILD", BuildName="YOUR TANK BUILD")
    )


def test_normal_saved_build_is_authoritative():
    assert not _is_template_build(
        PlayerBuild(Name="Magrat", BuildName="DF Healer")
    )


def test_explicit_template_label_is_excluded():
    assert _is_template_build(
        PlayerBuild(Name="Test Character", BuildName="Tank Template")
    )
