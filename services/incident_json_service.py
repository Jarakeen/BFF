# services/incident_json_service.py
from __future__ import annotations

import json
from pathlib import Path

from models.incident_model import IncidentModel, ResponsiblePartyFlags, IncidentStatusFlags


class IncidentJsonService:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load(self) -> IncidentModel:
        if not self.file_path.exists():
            return IncidentModel()

        raw_text = self.file_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)

        party_payload = payload.get("ResponsibleParty", {})
        party = ResponsiblePartyFlags(
            MooseGremlin=party_payload.get("MooseGremlin", False),
            Lag=party_payload.get("Lag", False),
            UserError=party_payload.get("UserError", False),
            ESO=party_payload.get("ESO", False),
            Unknown=party_payload.get("Unknown", False),
            UnderInvestigation=party_payload.get("UnderInvestigation", False),
        )

        status_payload = payload.get("Status", {})
        status = IncidentStatusFlags(
            Filed=status_payload.get("Filed", False),
            PendingReview=status_payload.get("PendingReview", False),
            RequiresFollowUp=status_payload.get("RequiresFollowUp", False),
            Archived=status_payload.get("Archived", False),
        )

        return IncidentModel(
            ReportNumber=payload.get("ReportNumber", ""),
            Location=payload.get("Location", ""),
            Department=payload.get("Department", ""),
            Severity=payload.get("Severity", ""),
            Summary=payload.get("Summary", ""),
            SuspectedCause=payload.get("SuspectedCause", ""),
            EngineeringAssessment=payload.get("EngineeringAssessment", ""),
            CoffeeRecommendation=payload.get("CoffeeRecommendation", ""),
            Observations=payload.get("Observations", ""),
            ActionsTaken=payload.get("ActionsTaken", ""),
            Recommendations=payload.get("Recommendations", ""),
            OutstandingQuestions=payload.get("OutstandingQuestions", ""),
            ResponsibleParty=party,
            Status=status,
        )

    def save(self, model: IncidentModel) -> None:
        payload = model.to_dict()
        serialized = json.dumps(payload, ensure_ascii=False, indent=4)
        self.file_path.write_text(serialized, encoding="utf-8")
