from __future__ import annotations

"""Project explicitly reviewed encounter evidence into healer demand criteria.

Reconciled encounter evidence is source-backed, but reconciliation alone is not
promotion to canonical encounter truth. This adapter therefore requires the caller
to supply the exact reviewed fact ids that are approved for hard-gate use.
Unreviewed facts remain non-authoritative and are never silently promoted.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from services.encounter_projection import EncounterEvidenceFact
from services.rotation_healer_demand_criteria_service import (
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
)


_HEALER_CRITERION_FACT_TYPE = "healer_demand_criterion"


class RotationHealerEncounterFactProvider(Protocol):
    def evidence_facts(
        self,
        encounter_id: str,
        fact_type: str | None = None,
    ) -> tuple[EncounterEvidenceFact, ...]: ...


@dataclass(frozen=True)
class RotationHealerEncounterCriteriaProjection:
    encounter_id: str
    criteria: tuple[RotationHealerDemandCriterion, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerEncounterCriteriaProvider:
    """Read reviewed structured encounter facts as healer hard-gate criteria.

    Expected fact value schema::

        {
            "demand_name": "execute burn",
            "minimum_modeled_healing_per_demand_second": 1250.0
        }

    The numeric unit intentionally matches the existing healer role-output model:
    canonical pre-recipient, pre-overheal modeled healing per demand-second. This
    adapter owns no healing math and does not infer a threshold from boss damage,
    health, prose, or target count.

    A reconciled fact becomes ``VERIFIED_ENCOUNTER_EVIDENCE`` only when its exact
    ``fact_id`` is present in ``reviewed_fact_ids``. This preserves the encounter
    evidence architecture's explicit review/promotion boundary.
    """

    def __init__(self, encounter_fact_provider: RotationHealerEncounterFactProvider) -> None:
        self.encounter_fact_provider = encounter_fact_provider

    def criteria_for_encounter(
        self,
        *,
        encounter_id: str,
        reviewed_fact_ids: tuple[str, ...] = (),
    ) -> RotationHealerEncounterCriteriaProjection:
        encounter_id = str(encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("healer encounter criteria require encounter_id")

        reviewed = {
            str(item).strip().casefold()
            for item in reviewed_fact_ids
            if str(item).strip()
        }
        facts = tuple(
            self.encounter_fact_provider.evidence_facts(
                encounter_id,
                _HEALER_CRITERION_FACT_TYPE,
            )
        )

        criteria: list[RotationHealerDemandCriterion] = []
        unresolved: list[str] = []
        seen_demands: set[str] = set()

        for fact in facts:
            if fact.fact_type != _HEALER_CRITERION_FACT_TYPE:
                raise ValueError(
                    "healer encounter criteria provider returned unexpected fact type: "
                    f"{fact.fact_type!r}"
                )

            value = fact.value
            if not isinstance(value, dict):
                unresolved.append(
                    f"{fact.fact_id}: healer demand criterion value must be an object"
                )
                continue

            demand_name = str(value.get("demand_name") or "").strip()
            raw_minimum = value.get("minimum_modeled_healing_per_demand_second")
            if not demand_name:
                unresolved.append(f"{fact.fact_id}: healer demand criterion missing demand_name")
                continue
            if (
                not isinstance(raw_minimum, (int, float))
                or isinstance(raw_minimum, bool)
                or not isfinite(float(raw_minimum))
                or float(raw_minimum) < 0.0
            ):
                unresolved.append(
                    f"{fact.fact_id}: healer demand criterion has invalid minimum modeled output"
                )
                continue

            demand_key = demand_name.casefold()
            if demand_key in seen_demands:
                unresolved.append(
                    f"{fact.fact_id}: duplicate healer demand criterion for {demand_name!r}"
                )
                continue
            seen_demands.add(demand_key)

            if fact.status == "conflicting" or fact.value_json is None:
                unresolved.append(
                    f"{fact.fact_id}: conflicting healer demand criterion evidence"
                )
                continue

            is_reviewed = fact.fact_id.casefold() in reviewed
            source_kind = (
                RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
                if is_reviewed
                else RotationHealerDemandCriterionSourceKind.CALLER_ASSUMPTION
            )
            provenance = [
                f"encounter_fact={fact.fact_id}",
                f"reconciliation_status={fact.status}",
                f"distinct_sources={fact.distinct_sources}",
            ]
            provenance.extend(
                f"source={source.page_title or source.url}"
                for source in fact.evidence
                if source.page_title or source.url
            )
            if not is_reviewed:
                provenance.append("review_status=not_promoted")
            else:
                provenance.append("review_status=approved_for_hard_gate")

            criteria.append(
                RotationHealerDemandCriterion(
                    demand_name=demand_name,
                    minimum_modeled_healing_per_demand_second=float(raw_minimum),
                    source_kind=source_kind,
                    provenance=tuple(provenance),
                )
            )

        return RotationHealerEncounterCriteriaProjection(
            encounter_id=encounter_id,
            criteria=tuple(criteria),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationHealerEncounterCriteriaProjection",
    "RotationHealerEncounterCriteriaProvider",
    "RotationHealerEncounterFactProvider",
]
