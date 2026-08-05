# models/incident_model.py
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ResponsiblePartyFlags:
    MooseGremlin: bool = False
    Lag: bool = False
    UserError: bool = False
    ESO: bool = False
    Unknown: bool = False
    UnderInvestigation: bool = False


@dataclass
class IncidentStatusFlags:
    Filed: bool = False
    PendingReview: bool = False
    RequiresFollowUp: bool = False
    Archived: bool = False


@dataclass
class IncidentModel:
    ReportNumber: str = ""
    Location: str = ""
    Department: str = ""
    Severity: str = ""
    Summary: str = ""
    SuspectedCause: str = ""
    EngineeringAssessment: str = ""
    CoffeeRecommendation: str = ""
    Observations: str = ""
    ActionsTaken: str = ""
    Recommendations: str = ""
    OutstandingQuestions: str = ""
    ResponsibleParty: ResponsiblePartyFlags = None
    Status: IncidentStatusFlags = None

    def __post_init__(self) -> None:
        if self.ResponsibleParty is None:
            self.ResponsibleParty = ResponsiblePartyFlags()
        if self.Status is None:
            self.Status = IncidentStatusFlags()

    def to_dict(self) -> dict:
        return asdict(self)
