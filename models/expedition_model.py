# models/exedition_model.py
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class StatusFlags:
    Observe: bool = True
    Document: bool = True
    Learn: bool = False
    ShareTheLesson: bool = True
    InProgress: bool = True
    Complete: bool = False
    UnderReview: bool = False


@dataclass
class ExpeditionModel:
    Expedition: str = ""
    Difficulty: str = ""
    Objective: str = ""
    Weather: str = ""
    Coffee: str = ""
    CoffeeLevel: str = ""
    Engineering: str = ""
    Incidents: str = ""
    Assignment: str = ""
    Observation: str = ""
    Context: str = ""
    NextSteps: str = ""
    Status: StatusFlags = None

    def __post_init__(self) -> None:
        if self.Status is None:
            self.Status = StatusFlags()

    def to_dict(self) -> dict:
        return asdict(self)
