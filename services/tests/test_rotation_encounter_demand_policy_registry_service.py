import json

import pytest

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.rotation_encounter_demand_policy_registry_service import (
    RotationEncounterDemandPolicyRegistryService,
)


def _write(tmp_path, payload):
    path = tmp_path / "encounter_demands.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_registry_distinguishes_missing_encounter_from_explicit_empty_policy(tmp_path) -> None:
    service = RotationEncounterDemandPolicyRegistryService(
        _write(
            tmp_path,
            {
                "schema_version": 2,
                "encounters": {
                    "rockgrove_xalvakka": {
                        "clock_policies": [],
                        "threshold_policies": [],
                    },
                },
            },
        )
    )

    assert service.policies_for("rockgrove_xalvakka") == ()
    assert service.threshold_policies_for("rockgrove_xalvakka") == ()
    assert service.review_blockers_for("rockgrove_xalvakka") == ()
    assert service.policies_for("sunspire_lokkestiiz") is None
    assert service.threshold_policies_for("sunspire_lokkestiiz") is None
    assert service.review_blockers_for("sunspire_lokkestiiz") is None
    assert service.configured_encounter_ids() == ("rockgrove_xalvakka",)


def test_registry_builds_exact_explicit_clock_policy_fields(tmp_path) -> None:
    service = RotationEncounterDemandPolicyRegistryService(
        _write(
            tmp_path,
            {
                "schema_version": 2,
                "encounters": {
                    "sunspire_test": {
                        "clock_policies": [
                            {
                                "fact_key": "ice_cage_window",
                                "kind": "healing",
                                "pattern": "burst",
                                "lead_seconds": 1.5,
                                "point_window_seconds": 2.0,
                                "target_count": 2,
                            }
                        ],
                        "threshold_policies": [],
                    }
                },
            },
        )
    )

    policies = service.policies_for("SUNSPIRE_TEST")
    assert policies is not None
    assert len(policies) == 1
    policy = policies[0]
    assert policy.fact_key == "ice_cage_window"
    assert policy.kind is RotationDemandKind.HEALING
    assert policy.pattern is RotationDemandPattern.BURST
    assert policy.lead_seconds == 1.5
    assert policy.point_window_seconds == 2.0
    assert policy.target_count == 2


def test_registry_builds_exact_explicit_threshold_policy_fields(tmp_path) -> None:
    service = RotationEncounterDemandPolicyRegistryService(
        _write(
            tmp_path,
            {
                "schema_version": 2,
                "encounters": {
                    "xalvakka": {
                        "clock_policies": [],
                        "threshold_policies": [
                            {
                                "fact_key": "phase_2",
                                "threshold_fraction": 0.70,
                                "kind": "healing",
                                "pattern": "burst",
                                "lead_seconds": 3.0,
                                "window_seconds": 2.0,
                                "target_count": 12,
                                "name": "Xalvakka Phase 2 healing prep",
                            }
                        ],
                    }
                },
            },
        )
    )

    policies = service.threshold_policies_for("XALVAKKA")
    assert policies is not None
    assert len(policies) == 1
    policy = policies[0]
    assert policy.fact_key == "phase_2"
    assert policy.threshold_fraction == 0.70
    assert policy.kind is RotationDemandKind.HEALING
    assert policy.pattern is RotationDemandPattern.BURST
    assert policy.lead_seconds == 3.0
    assert policy.window_seconds == 2.0
    assert policy.target_count == 12
    assert policy.name == "Xalvakka Phase 2 healing prep"


def test_registry_preserves_structured_review_blockers_without_making_policy(tmp_path) -> None:
    service = RotationEncounterDemandPolicyRegistryService(
        _write(
            tmp_path,
            {
                "schema_version": 2,
                "encounters": {
                    "xalvakka": {
                        "clock_policies": [],
                        "threshold_policies": [],
                        "review_blockers": [
                            {
                                "key": "phase_2_healer_demand_policy",
                                "summary": "Phase 2 anchor is reviewed but healer policy is not.",
                                "needed_evidence": "Approve lead, window, pattern, and target count.",
                                "source_context": "reviewed Xalvakka Phase 2 evidence",
                            }
                        ],
                    }
                },
            },
        )
    )

    assert service.policies_for("xalvakka") == ()
    assert service.threshold_policies_for("xalvakka") == ()
    blockers = service.review_blockers_for("XALVAKKA")
    assert blockers is not None
    assert len(blockers) == 1
    blocker = blockers[0]
    assert blocker.key == "phase_2_healer_demand_policy"
    assert blocker.summary == "Phase 2 anchor is reviewed but healer policy is not."
    assert blocker.needed_evidence == "Approve lead, window, pattern, and target count."
    assert blocker.source_context == "reviewed Xalvakka Phase 2 evidence"


def test_registry_rejects_unknown_clock_policy_fields_instead_of_ignoring_them(tmp_path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 2,
            "encounters": {
                "sunspire_test": {
                    "clock_policies": [
                        {
                            "fact_key": "ice_cage_window",
                            "kind": "healing",
                            "pattern": "burst",
                            "invented_threshold": 9001,
                        }
                    ],
                    "threshold_policies": [],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="unsupported fields.*invented_threshold"):
        RotationEncounterDemandPolicyRegistryService(path)


def test_registry_rejects_duplicate_clock_fact_keys_for_one_encounter(tmp_path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 2,
            "encounters": {
                "sunspire_test": {
                    "clock_policies": [
                        {
                            "fact_key": "ice_cage_window",
                            "kind": "healing",
                            "pattern": "burst",
                        },
                        {
                            "fact_key": "ice_cage_window",
                            "kind": "support",
                            "pattern": "sustained",
                        },
                    ],
                    "threshold_policies": [],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="duplicate.*clock fact_key"):
        RotationEncounterDemandPolicyRegistryService(path)


def test_registry_rejects_duplicate_threshold_identity_for_one_encounter(tmp_path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 2,
            "encounters": {
                "xalvakka": {
                    "clock_policies": [],
                    "threshold_policies": [
                        {
                            "fact_key": "phase_2",
                            "threshold_fraction": 0.70,
                            "kind": "healing",
                            "pattern": "burst",
                        },
                        {
                            "fact_key": "phase_2",
                            "threshold_fraction": 0.70,
                            "kind": "support",
                            "pattern": "sustained",
                        },
                    ],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="duplicate.*threshold policy"):
        RotationEncounterDemandPolicyRegistryService(path)


def test_registry_rejects_duplicate_review_blocker_keys(tmp_path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 2,
            "encounters": {
                "xalvakka": {
                    "clock_policies": [],
                    "threshold_policies": [],
                    "review_blockers": [
                        {
                            "key": "phase_2_policy",
                            "summary": "first",
                            "needed_evidence": "review it",
                        },
                        {
                            "key": "PHASE_2_POLICY",
                            "summary": "second",
                            "needed_evidence": "review it again",
                        },
                    ],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="duplicate.*review blocker"):
        RotationEncounterDemandPolicyRegistryService(path)
