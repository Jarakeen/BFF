from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.expedition_model import ExpeditionModel, StatusFlags


class JsonService:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load(self) -> ExpeditionModel:
        if not self.file_path.exists():
            return ExpeditionModel()

        raw_text = self.file_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)

        status_payload = payload.get("Status", {})
        status = StatusFlags(
            Observe=status_payload.get("Observe", True),
            Document=status_payload.get("Document", True),
            Learn=status_payload.get("Learn", False),
            ShareTheLesson=status_payload.get("ShareTheLesson", True),
            InProgress=status_payload.get("InProgress", True),
            Complete=status_payload.get("Complete", False),
            UnderReview=status_payload.get("UnderReview", False),
        )

        return ExpeditionModel(
            Expedition=payload.get("Expedition", ""),
            Difficulty=payload.get("Difficulty", ""),
            Objective=payload.get("Objective", ""),
            Weather=payload.get("Weather", ""),
            Coffee=payload.get("Coffee", ""),
            CoffeeLevel=payload.get("CoffeeLevel", ""),
            Engineering=payload.get("Engineering", ""),
            Incidents=payload.get("Incidents", ""),
            Assignment=payload.get("Assignment", ""),
            Observation=payload.get("Observation", ""),
            Context=payload.get("Context", ""),
            NextSteps=payload.get("NextSteps", ""),
            Status=status,
        )

    def save(self, model: ExpeditionModel) -> None:
        payload = model.to_dict()
        serialized = json.dumps(payload, ensure_ascii=False, indent=4)
        self.file_path.write_text(serialized, encoding="utf-8")
